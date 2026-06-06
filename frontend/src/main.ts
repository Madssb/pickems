import './style.css';
import teams_ from '../../data/teams.json'
import questions_ from '../../data/questions.json'


type Team = {
  prefix: string
  members: string[]
};
type Teams = Record<string, Team>;

type AnswerCategory = 'player' | 'team';
type Question = {
  question: string;
  answerCategory: AnswerCategory;
};
type QuestionGroup = Record<string, Question>;
type Questions = Record<string, QuestionGroup>;


const teams = teams_ as Teams;
const questions = questions_ as Questions;
const teamNames = Object.keys(teams);
const predictionDeadline = new Date('2026-06-06T12:00:00Z');

type LoginLinkResponse = {
  login_url: string;
};

type Participant = {
  id: number,
  display_name: string
}

type PredictionsPayload = {
  team_rankings: string[];
  [key: string]: string[] | string | null;
};

type PredictionsResponse = {
  message: string;
  updated_at: string;
};

function getApiBaseUrl(): string {
  const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL;
  if (!rawApiBaseUrl) {
    throw new Error('VITE_API_BASE_URL is not set');
  }

  try {
    const url = new URL(rawApiBaseUrl);
    if (!['http:', 'https:'].includes(url.protocol)) {
      throw new Error('unsupported protocol');
    }

    return url.toString().replace(/\/$/, '');
  } catch {
    throw new Error('VITE_API_BASE_URL must be an absolute http(s) URL, for example https://pickems-api.ladlorchart.com');
  }
}

async function explainFailedResponse(response: Response): Promise<Error> {
  const responseText = await response.text();
  let responseDetail = responseText.trim();

  if (responseDetail) {
    try {
      const parsed = JSON.parse(responseDetail) as unknown;
      if (typeof parsed === 'object' && parsed !== null && 'detail' in parsed) {
        responseDetail = String(parsed.detail);
      }
    } catch {
      responseDetail = responseDetail.slice(0, 160);
    }
  }

  const message = responseDetail
    ? `Request to ${response.url} failed with status ${response.status}: ${responseDetail}`
    : `Request to ${response.url} failed with status ${response.status}`;

  return new Error(message);
}

const apiBaseUrl = getApiBaseUrl();
const privacyNoticeStorageKey = 'pickems-privacy-notice-dismissed';

function predictionsAreClosed(): boolean {
  return Date.now() >= predictionDeadline.getTime();
}

function setupPrivacyNotice() {
  const privacyNotice = document.querySelector<HTMLElement>('#privacy-notice');
  const dismissButton = document.querySelector<HTMLButtonElement>('#privacy-notice-dismiss');

  if (!privacyNotice || !dismissButton) {
    throw new Error('Privacy notice markup is missing required elements');
  }

  if (localStorage.getItem(privacyNoticeStorageKey) === 'true') {
    privacyNotice.hidden = true;
    return;
  }

  privacyNotice.hidden = false;
  dismissButton.addEventListener('click', () => {
    localStorage.setItem(privacyNoticeStorageKey, 'true');
    privacyNotice.hidden = true;
  });
}


function setupLoginLinkPanel() {
  const showLoginLinkButton = document.querySelector<HTMLButtonElement>('#show-login-link-button');
  const closeLoginLinkButton = document.querySelector<HTMLButtonElement>('#close-login-link-button');
  const loginLinkPanel = document.querySelector<HTMLElement>('#login-link-panel');
  const copyLoginLinkButton = document.querySelector<HTMLButtonElement>('#copy-login-link-button');
  const loginLinkStatus = document.querySelector<HTMLParagraphElement>('#login-link-status');
  
  if (!showLoginLinkButton || !closeLoginLinkButton || !loginLinkPanel || !copyLoginLinkButton || !loginLinkStatus) {
    throw new Error('Login-link panel markup is missing required elements');
  }

  async function createOrRotateLoginLink(): Promise<LoginLinkResponse> {
    const response = await fetch(`${apiBaseUrl}/login-links`, {
      method: 'POST',
      credentials: 'include',
    });

    if (!response.ok) {
      throw await explainFailedResponse(response);
    }
    return await response.json() as LoginLinkResponse;
  }

  showLoginLinkButton.addEventListener('click', () => {
    loginLinkPanel.hidden = false;
  });

  closeLoginLinkButton.addEventListener('click', () => {
    loginLinkPanel.hidden = true;
    loginLinkStatus.textContent = '';
  });

  copyLoginLinkButton.addEventListener('click', async () => {
    copyLoginLinkButton.disabled = true;
    loginLinkStatus.textContent = 'Creating new login link...';

    try {
      const result = await createOrRotateLoginLink();
      await navigator.clipboard.writeText(result.login_url);
      loginLinkStatus.textContent = 'New login link copied. The previous link is now invalid.';
    } catch (error) {
      console.error(error);
      loginLinkStatus.textContent = 'Could not copy a login link.';
    } finally {
      copyLoginLinkButton.disabled = false;
    }
  });

}

/* Return the existing browser session, or create a guest session. */
async function getOrCreateParticipant(): Promise<Participant | null> {
  try {
    let response = await fetch(`${apiBaseUrl}/session`, {
      credentials: 'include',
    });

    if (response.status === 401) {
      response = await fetch(`${apiBaseUrl}/session`, {
        method: 'POST',
        credentials: 'include',
      });
    }

    if (!response.ok) {
      throw await explainFailedResponse(response);
    }
    return await response.json() as Participant;
  } catch (error) {
    console.log(error);
    return null;
  }
}

function setupSessionPanel(participant: Participant | null) {
  const showLoginLinkButton = document.querySelector<HTMLButtonElement>('#show-login-link-button');
  const loginLinkPanel = document.querySelector<HTMLElement>('#login-link-panel');
  const banner = document.querySelector<HTMLParagraphElement>('#session-banner');
  const displayNameInput = document.querySelector<HTMLInputElement>('#display-name');

  if (!showLoginLinkButton || !loginLinkPanel || !banner || !displayNameInput) {
    throw new Error('Session panel markup is missing required elements');
  }

  if (participant) {
    showLoginLinkButton.hidden = false;
    loginLinkPanel.hidden = true;
    banner.textContent = `Picks saved as ${participant.display_name}`;
    displayNameInput.value = participant.display_name;
  } else {
    showLoginLinkButton.hidden = false;
    loginLinkPanel.hidden = true;
    banner.textContent = '';
  }
}

function setupDisplayNameForm() {
  const displayNameForm = document.querySelector<HTMLFormElement>('#display-name-form');
  const displayNameInput = document.querySelector<HTMLInputElement>('#display-name');
  const saveDisplayNameButton = document.querySelector<HTMLButtonElement>('#save-display-name-button');
  const loginLinkStatus = document.querySelector<HTMLParagraphElement>('#login-link-status');

  if (!displayNameForm || !displayNameInput || !saveDisplayNameButton || !loginLinkStatus) {
    throw new Error('Display-name form markup is missing required elements');
  }

  displayNameForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    saveDisplayNameButton.disabled = true;
    loginLinkStatus.textContent = 'Saving display name...';

    try {
      const response = await fetch(`${apiBaseUrl}/display-name`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ display_name: displayNameInput.value }),
      });

      if (!response.ok) {
        throw await explainFailedResponse(response);
      }

      const participant = await response.json() as Participant;
      setupSessionPanel(participant);
      loginLinkStatus.textContent = 'Display name saved.';
    } catch (error) {
      console.error(error);
      loginLinkStatus.textContent = 'Could not save display name.';
    } finally {
      saveDisplayNameButton.disabled = false;
    }
  });
}

function getPlayerOptions(): string[] {
  return Object.values(teams).flatMap((team) =>
    team.members.map((member) => `${team.prefix} ${member}`)
  );
}

function renderQuestion(
  questionKey: string,
  question: Question,
  players: string[],
  teamNames: string[],
): HTMLElement {
  const questionRow = document.createElement('div');
  questionRow.className = 'question-row';

  const label = document.createElement('label');
  label.textContent = question.question;

  const select = document.createElement('select');
  select.name = questionKey;
  select.dataset.predictionField = questionKey;

  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = 'None selected';
  placeholder.disabled = true;
  placeholder.selected = true;
  select.appendChild(placeholder);

  const options = question.answerCategory === 'player' ? players : teamNames;
  for (const option of options) {
    const optionElement = document.createElement('option');
    optionElement.value = option;
    optionElement.textContent = option;
    select.appendChild(optionElement);
  }

  questionRow.append(label, select);
  return questionRow;
}

function SetupQuestions() {
  const questionsPanel = document.querySelector<HTMLElement>('#questions-panel');

  if (!questionsPanel) {
    throw new Error('Questions panel is missing');
  }

  const players = getPlayerOptions();

  for (const [category, questionGroup] of Object.entries(questions)) {
    const categorySection = document.createElement('section');
    categorySection.className = 'question-category';

    const categoryTitle = document.createElement('h2');
    categoryTitle.textContent = category;

    const categoryGrid = document.createElement('div');
    categoryGrid.className = 'question-grid';

    for (const [questionKey, question] of Object.entries(questionGroup)) {
      categoryGrid.appendChild(renderQuestion(questionKey, question, players, teamNames));
    }

    categorySection.append(categoryTitle, categoryGrid);
    questionsPanel.appendChild(categorySection);
  }
}

type RankingControls = {
  hydrate: (teamRankings: string[]) => void;
};

function ordinal(rank: number): string {
  const suffixes = ['th', 'st', 'nd', 'rd'];
  const lastTwoDigits = rank % 100;
  const suffix = suffixes[(lastTwoDigits - 20) % 10] ?? suffixes[lastTwoDigits] ?? suffixes[0];
  return `${rank}${suffix}`;
}

function SetupRankings(): RankingControls {
  const rankingPanel = document.querySelector<HTMLElement>('#ranking-panel');

  if (!rankingPanel) {
    throw new Error('Ranking panel is missing');
  }

  const selections = Array<string>(teamNames.length).fill('');
  const selects: HTMLSelectElement[] = [];

  const title = document.createElement('h2');
  title.textContent = 'Team rankings';

  const rankingRows = document.createElement('div');
  rankingRows.className = 'ranking-rows';

  function renderRankingOptions() {
    const selectedTeams = new Set(selections.filter(Boolean));

    selects.forEach((select, index) => {
      const currentValue = selections[index];
      select.replaceChildren();

      const placeholder = document.createElement('option');
      placeholder.value = '';
      placeholder.textContent = 'None selected';
      select.appendChild(placeholder);

      for (const teamName of teamNames) {
        if (selectedTeams.has(teamName) && teamName !== currentValue) {
          continue;
        }

        const option = document.createElement('option');
        option.value = teamName;
        option.textContent = teamName;
        select.appendChild(option);
      }

      select.value = currentValue;
    });
  }

  teamNames.forEach((_, index) => {
    const row = document.createElement('div');
    row.className = 'ranking-row';

    const label = document.createElement('label');
    label.textContent = ordinal(index + 1);

    const select = document.createElement('select');
    select.name = `ranking-${index + 1}`;
    select.className = 'ranking-select';
    select.addEventListener('change', () => {
      selections[index] = select.value;
      renderRankingOptions();
    });

    selects.push(select);
    row.append(label, select);
    rankingRows.appendChild(row);
  });

  rankingPanel.append(title, rankingRows);
  renderRankingOptions();

  return {
    hydrate: (teamRankings: string[]) => {
      teamRankings.forEach((teamName, index) => {
        if (index < selections.length) {
          selections[index] = teamName;
        }
      });
      renderRankingOptions();
    },
  };
}

function formatCountdown(milliseconds: number): string {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const days = Math.floor(totalSeconds / 86_400);
  const hours = Math.floor((totalSeconds % 86_400) / 3_600);
  const minutes = Math.floor((totalSeconds % 3_600) / 60);
  const seconds = totalSeconds % 60;

  return `${days}d ${hours}h ${minutes}m ${seconds}s`;
}

function setupPredictionCountdown() {
  const countdown = document.querySelector<HTMLElement>('#prediction-countdown');

  if (!countdown) {
    throw new Error('Prediction countdown is missing');
  }
  const countdownElement = countdown;

  function renderCountdown() {
    const millisecondsRemaining = predictionDeadline.getTime() - Date.now();

    if (millisecondsRemaining <= 0) {
      countdownElement.textContent = 'Predictions are closed.';
      setPredictionControlsDisabled(true);
      return;
    }

    countdownElement.textContent = `Predictions close in ${formatCountdown(millisecondsRemaining)}`;
  }

  renderCountdown();
  window.setInterval(renderCountdown, 1000);
}

function setPredictionControlsDisabled(disabled: boolean) {
  const predictionControls = document.querySelectorAll<HTMLSelectElement>(
    '.ranking-select, [data-prediction-field]',
  );

  predictionControls.forEach((control) => {
    control.disabled = disabled;
  });
}

function collectPredictions(): PredictionsPayload {
  const rankingSelects = document.querySelectorAll<HTMLSelectElement>('.ranking-select');
  const questionSelects = document.querySelectorAll<HTMLSelectElement>('[data-prediction-field]');
  const payload: PredictionsPayload = {
    team_rankings: Array.from(rankingSelects).map((select) => select.value),
  };

  questionSelects.forEach((select) => {
    const fieldName = select.dataset.predictionField;

    if (!fieldName) {
      return;
    }

    payload[fieldName] = select.value || null;
  });

  return payload;
}

function setSaveStatus(message: string) {
  const saveStatus = document.querySelector<HTMLParagraphElement>('#save-status');

  if (!saveStatus) {
    throw new Error('Save status element is missing');
  }

  saveStatus.textContent = message;
}

async function savePredictions() {
  if (predictionsAreClosed()) {
    setPredictionControlsDisabled(true);
    setSaveStatus('Predictions are closed. Showing saved picks.');
    return;
  }

  setSaveStatus('Saving...');

  try {
    const response = await fetch(`${apiBaseUrl}/predictions`, {
      method: 'PUT',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(collectPredictions()),
    });

    if (response.status === 401) {
      setSaveStatus('Could not find this browser session.');
      return;
    }

    if (!response.ok) {
      throw await explainFailedResponse(response);
    }

    const result: PredictionsResponse = await response.json();
    const savedAt = new Date(result.updated_at);
    setSaveStatus(`Saved ${savedAt.toLocaleTimeString()}`);
  } catch (error) {
    console.error(error);
    setSaveStatus('Could not save predictions.');
  }
}

function setupPredictionAutosave() {
  const rankingPanel = document.querySelector<HTMLElement>('#ranking-panel');
  const questionsPanel = document.querySelector<HTMLElement>('#questions-panel');

  if (!rankingPanel || !questionsPanel) {
    throw new Error('Prediction controls are missing');
  }

  let saveTimeout: number | undefined;

  function scheduleSave() {
    if (predictionsAreClosed()) {
      setPredictionControlsDisabled(true);
      setSaveStatus('Predictions are closed. Showing saved picks.');
      return;
    }

    setSaveStatus('Unsaved changes...');

    if (saveTimeout !== undefined) {
      window.clearTimeout(saveTimeout);
    }

    saveTimeout = window.setTimeout(savePredictions, 400);
  }

  rankingPanel.addEventListener('change', scheduleSave);
  questionsPanel.addEventListener('change', scheduleSave);
}

function hasSavedPredictions(predictions: PredictionsPayload): boolean {
  if (predictions.team_rankings.some((teamName) => teamName.trim() !== '')) {
    return true;
  }

  return Object.entries(predictions).some(([fieldName, value]) => (
    fieldName !== 'team_rankings' && typeof value === 'string' && value.trim() !== ''
  ));
}

async function hydratePredictions(rankingControls: RankingControls): Promise<boolean> {
  try {
    const response = await fetch(`${apiBaseUrl}/predictions`, {
      credentials: 'include',
    });

    if (response.status === 401) {
      setSaveStatus('Could not find this browser session.');
      return false;
    }

    if (!response.ok) {
      throw await explainFailedResponse(response);
    }

    const predictions: PredictionsPayload = await response.json();
    rankingControls.hydrate(predictions.team_rankings ?? []);

    const questionSelects = document.querySelectorAll<HTMLSelectElement>('[data-prediction-field]');
    questionSelects.forEach((select) => {
      const fieldName = select.dataset.predictionField;
      const value = fieldName ? predictions[fieldName] : null;

      if (typeof value === 'string') {
        select.value = value;
      }
    });

    setSaveStatus('');
    return hasSavedPredictions(predictions);
  } catch (error) {
    console.error(error);
    setSaveStatus('Could not load saved predictions.');
    return false;
  }
}


setupPrivacyNotice();
setupLoginLinkPanel();
setupDisplayNameForm();
setupPredictionCountdown();
const rankingControls = SetupRankings();
SetupQuestions();
const participant = await getOrCreateParticipant();
setupSessionPanel(participant);
if (participant) {
  const hasSavedPicks = await hydratePredictions(rankingControls);

  if (predictionsAreClosed()) {
    setSaveStatus(
      hasSavedPicks
        ? 'Predictions are closed. Showing saved picks.'
        : 'Predictions are closed. No saved picks for this browser.',
    );
  } else {
    setupPredictionAutosave();
  }
}

if (predictionsAreClosed()) {
  setPredictionControlsDisabled(true);
}
