import './style.css';

type LoginRequest = {
  email: string;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

if (!apiBaseUrl) {
  throw new Error('VITE_API_BASE_URL is not set');
}

const loginForm = document.querySelector<HTMLFormElement>('#login-form');
const emailInput = document.querySelector<HTMLInputElement>('#email');
const loginButton = document.querySelector<HTMLButtonElement>('#login-button');
const loginStatus = document.querySelector<HTMLParagraphElement>('#login-status');

if (!loginForm || !emailInput || !loginButton || !loginStatus) {
  throw new Error('Login form markup is missing required elements');
}

loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const payload: LoginRequest = {
    email: emailInput.value,
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
      throw new Error(`Request failed with status ${response.status}`);
    }

    loginStatus.textContent = 'Login link requested. Check your email.';
  } catch (error) {
    console.error(error);
    loginStatus.textContent = 'Could not request a login link.';
  } finally {
    loginButton.disabled = false;
  }
});
