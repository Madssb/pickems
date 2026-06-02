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
const submissionDeadline = new Date('2026-06-06T13:00:00Z');

type LoginRequest = {
  email: string;
  display_name: string;
};

type CurrentUser = {
  id: number,
  display_name: string
}

type SubmissionPayload = {
  team_rankings: string[];
  [key: string]: string[] | string | null;
};

type SubmissionResponse = {
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


/* hit POST: /auth/request-link when button is clicked */
function setupLoginForm() {
  const showLoginButton = document.querySelector<HTMLButtonElement>('#show-login-button');
  const closeLoginButton = document.querySelector<HTMLButtonElement>('#close-login-button');
  const loginOverlay = document.querySelector<HTMLDivElement>('#login-overlay');
  const loginForm = document.querySelector<HTMLFormElement>('#login-form');
  const emailInput = document.querySelector<HTMLInputElement>('#email');
  const displayNameInput = document.querySelector<HTMLInputElement>('#display-name');
  const loginButton = document.querySelector<HTMLButtonElement>('#login-button');
  const loginStatus = document.querySelector<HTMLParagraphElement>('#login-status');
  
  if (!showLoginButton || !closeLoginButton || !loginOverlay || !loginForm || !emailInput || !displayNameInput || !loginButton || !loginStatus) {
    throw new Error('Login form markup is missing required elements');
  }

  showLoginButton.addEventListener('click', () => {
    loginOverlay.hidden = false;
    displayNameInput.focus();
  });

  closeLoginButton.addEventListener('click', () => {
    loginOverlay.hidden = true;
    loginStatus.textContent = '';
  });
  
  loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
  
    const payload: LoginRequest = {
      email: emailInput.value,
      display_name: displayNameInput.value,
    };
  
    loginButton.disabled = true;
    loginStatus.textContent = 'Requesting login link...';
  
    try {
      const response = await fetch(`${apiBaseUrl}/auth/request-link`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
  
      if (!response.ok) {
        throw await explainFailedResponse(response);
      }
  
      loginStatus.textContent = 'Login link requested. Check your email.';
    } catch (error) {
      console.error(error);
      loginStatus.textContent = 'Could not request a login link.';
    } finally {
      loginButton.disabled = false;
    }
  });
}

/* hit GET: /auth/me on page load */
async function checkCurrentUser(): Promise<CurrentUser | null> {
  try {
    const response = await fetch(`${apiBaseUrl}/auth/me`, {
      credentials: 'include',
    });
    if (!response.ok) {
      throw await explainFailedResponse(response);
    }
    const user: CurrentUser = await response.json();

    console.log(user.id);
    console.log(user.display_name);
    return user;
  } catch (error) {
    console.log(error);
    return null;
  }
}

function setupLoggedInBanner(user: CurrentUser | null) {
  const showLoginButton = document.querySelector<HTMLButtonElement>('#show-login-button');
  const loginOverlay = document.querySelector<HTMLDivElement>('#login-overlay');
  const loggedInPanel = document.querySelector<HTMLDivElement>('#logged-in-panel');
  const banner = document.querySelector<HTMLDivElement>('#logged-in-banner');

  if (!showLoginButton || !loginOverlay || !loggedInPanel || !banner) {
    throw new Error('Auth panel markup is missing required elements');
  }

  if (user) {
    showLoginButton.hidden = true;
    loginOverlay.hidden = true;
    loggedInPanel.hidden = false;
    banner.textContent = `Logged in as ${user.display_name}`;
  } else {
    showLoginButton.hidden = false;
    loginOverlay.hidden = true;
    loggedInPanel.hidden = true;
    banner.textContent = '';
  }
}

function setupLogoutButton() {
  const logoutButton = document.querySelector<HTMLButtonElement>('#logout-button');
  const loginStatus = document.querySelector<HTMLParagraphElement>('#login-status');

  if (!logoutButton || !loginStatus) {
    throw new Error('Logout markup is missing required elements');
  }

  logoutButton.addEventListener('click', async () => {
    logoutButton.disabled = true;
    loginStatus.textContent = 'Logging out...';

    try {
      const response = await fetch(`${apiBaseUrl}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });

      if (!response.ok) {
        throw await explainFailedResponse(response);
      }

      setupLoggedInBanner(null);
      loginStatus.textContent = '';
    } catch (error) {
      console.error(error);
      loginStatus.textContent = 'Could not log out.';
    } finally {
      logoutButton.disabled = false;
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
  select.dataset.submissionField = questionKey;

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

function SetupSubmissionCountdown() {
  const countdown = document.querySelector<HTMLElement>('#submission-countdown');

  if (!countdown) {
    throw new Error('Submission countdown is missing');
  }
  const countdownElement = countdown;

  function renderCountdown() {
    const millisecondsRemaining = submissionDeadline.getTime() - Date.now();

    if (millisecondsRemaining <= 0) {
      countdownElement.textContent = 'Submissions are closed.';
      return;
    }

    countdownElement.textContent = `Submissions close in ${formatCountdown(millisecondsRemaining)}`;
  }

  renderCountdown();
  window.setInterval(renderCountdown, 1000);
}

function collectSubmission(): SubmissionPayload {
  const rankingSelects = document.querySelectorAll<HTMLSelectElement>('.ranking-select');
  const questionSelects = document.querySelectorAll<HTMLSelectElement>('[data-submission-field]');
  const payload: SubmissionPayload = {
    team_rankings: Array.from(rankingSelects).map((select) => select.value),
  };

  questionSelects.forEach((select) => {
    const fieldName = select.dataset.submissionField;

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

async function saveSubmission() {
  setSaveStatus('Saving...');

  try {
    const response = await fetch(`${apiBaseUrl}/submit-predictions`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(collectSubmission()),
    });

    if (response.status === 401) {
      setSaveStatus('Log in to save predictions.');
      return;
    }

    if (!response.ok) {
      throw await explainFailedResponse(response);
    }

    const result: SubmissionResponse = await response.json();
    const savedAt = new Date(result.updated_at);
    setSaveStatus(`Saved ${savedAt.toLocaleTimeString()}`);
  } catch (error) {
    console.error(error);
    setSaveStatus('Could not save predictions.');
  }
}

function setupSubmissionAutosave() {
  const rankingPanel = document.querySelector<HTMLElement>('#ranking-panel');
  const questionsPanel = document.querySelector<HTMLElement>('#questions-panel');

  if (!rankingPanel || !questionsPanel) {
    throw new Error('Submission controls are missing');
  }

  let saveTimeout: number | undefined;

  function scheduleSave() {
    setSaveStatus('Unsaved changes...');

    if (saveTimeout !== undefined) {
      window.clearTimeout(saveTimeout);
    }

    saveTimeout = window.setTimeout(saveSubmission, 400);
  }

  rankingPanel.addEventListener('change', scheduleSave);
  questionsPanel.addEventListener('change', scheduleSave);
}

async function hydrateSubmission(rankingControls: RankingControls) {
  try {
    const response = await fetch(`${apiBaseUrl}/get-predictions`, {
      credentials: 'include',
    });

    if (response.status === 401) {
      setSaveStatus('Log in to save predictions.');
      return;
    }

    if (!response.ok) {
      throw await explainFailedResponse(response);
    }

    const submission: SubmissionPayload = await response.json();
    rankingControls.hydrate(submission.team_rankings ?? []);

    const questionSelects = document.querySelectorAll<HTMLSelectElement>('[data-submission-field]');
    questionSelects.forEach((select) => {
      const fieldName = select.dataset.submissionField;
      const value = fieldName ? submission[fieldName] : null;

      if (typeof value === 'string') {
        select.value = value;
      }
    });

    setSaveStatus('');
  } catch (error) {
    console.error(error);
    setSaveStatus('Could not load saved predictions.');
  }
}





setupLoginForm();
setupLogoutButton();
SetupSubmissionCountdown();
const rankingControls = SetupRankings();
SetupQuestions();
setupSubmissionAutosave();
const user = await checkCurrentUser();
setupLoggedInBanner(user);
if (user) {
  await hydrateSubmission(rankingControls);
}
