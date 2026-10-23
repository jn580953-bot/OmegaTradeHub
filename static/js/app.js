const chartCanvas = document.getElementById('price-chart');
const ctx = chartCanvas.getContext('2d');
const tradeForm = document.getElementById('trade-form');
const recentTradesEl = document.getElementById('recent-trades-list');
const accountSelect = document.getElementById('account-select');
const balanceValue = document.getElementById('balance-value');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const authTabs = document.querySelectorAll('.auth-tab');
const userSession = document.getElementById('user-session');
const sessionUsername = document.getElementById('session-username');
const logoutBtn = document.getElementById('logout-btn');
const predictionSelect = document.getElementById('prediction-select');
const thresholdInput = document.getElementById('threshold-input');
const modeButtons = document.querySelectorAll('.mode-btn');

const state = {
  marketData: [480, 482, 481, 486, 489, 485, 488, 494, 492, 487, 490, 487.42],
  currentMode: 'matches',
  authenticated: false,
  user: null,
};

function renderChart(data) {
  const width = chartCanvas.width;
  const height = chartCanvas.height;
  const padding = 20;
  const min = Math.min(...data) - 5;
  const max = Math.max(...data) + 5;
  const stepX = (width - padding * 2) / (data.length - 1);

  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = 'rgba(255,255,255,0.08)';
  ctx.lineWidth = 1;

  for (let i = 0; i <= 5; i += 1) {
    const y = padding + (height - padding * 2) * (i / 5);
    ctx.beginPath();
    ctx.moveTo(padding, y);
    ctx.lineTo(width - padding, y);
    ctx.stroke();
  }

  ctx.beginPath();
  data.forEach((value, index) => {
    const x = padding + index * stepX;
    const y = height - padding - ((value - min) / (max - min || 1)) * (height - padding * 2);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });

  ctx.strokeStyle = '#2ed67a';
  ctx.lineWidth = 2.5;
  ctx.stroke();

  const lastValue = data[data.length - 1];
  const lastX = width - padding;
  const lastY = height - padding - ((lastValue - min) / (max - min || 1)) * (height - padding * 2);

  ctx.fillStyle = '#2ed67a';
  ctx.beginPath();
  ctx.arc(lastX, lastY, 4, 0, Math.PI * 2);
  ctx.fill();
}

function updateMarketNumbers() {
  const last = state.marketData[state.marketData.length - 1];
  document.getElementById('last-price').textContent = Number(last).toFixed(2);
  document.getElementById('open-price').textContent = Number(state.marketData[0]).toFixed(2);
  document.getElementById('high-price').textContent = Number(Math.max(...state.marketData)).toFixed(2);
  document.getElementById('low-price').textContent = Number(Math.min(...state.marketData)).toFixed(2);
}

function renderRecentTrades(trades) {
  recentTradesEl.innerHTML = '';
  if (!trades || !trades.length) {
    recentTradesEl.innerHTML = '<div class="trade-row"><span>No trades yet</span><strong class="muted">--</strong></div>';
    return;
  }

  trades.forEach((trade) => {
    const row = document.createElement('div');
    row.className = 'trade-row';
    row.innerHTML = `
      <span>${trade.mode ? trade.mode.toUpperCase() : 'TRADE'} / ${trade.digit ?? '--'}</span>
      <strong class="${trade.won ? 'gain' : 'loss'}">${trade.won ? 'Win' : 'Loss'}</strong>
    `;
    recentTradesEl.appendChild(row);
  });
}

function updateBalanceFromAccount() {
  const selected = accountSelect.value;
  if (!state.user) {
    const defaultBalance = selected === 'live' ? 0 : 5000;
    balanceValue.textContent = `$${defaultBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    return;
  }

  const balance = selected === 'live' ? state.user.live_balance : state.user.demo_balance;
  balanceValue.textContent = `$${Number(balance).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function syncPredictionOptions() {
  const mode = state.currentMode;
  const options = {
    matches: [
      { value: 'match', label: 'Match' },
      { value: 'differ', label: 'Differ' },
    ],
    even_odd: [
      { value: 'even', label: 'Even' },
      { value: 'odd', label: 'Odd' },
    ],
    over_under: [
      { value: 'above', label: 'Above' },
      { value: 'below', label: 'Below' },
    ],
  };

  predictionSelect.innerHTML = options[mode].map((option) => `<option value="${option.value}">${option.label}</option>`).join('');

  if (mode === 'over_under') {
    thresholdInput.disabled = false;
    thresholdInput.parentElement.classList.remove('hidden');
  } else {
    thresholdInput.disabled = true;
    thresholdInput.parentElement.classList.add('hidden');
  }
}

async function fetchMarket() {
  try {
    const response = await fetch('/api/market');
    const data = await response.json();
    if (data.history && data.history.length) {
      state.marketData = data.history;
      renderChart(state.marketData);
      updateMarketNumbers();
    }
  } catch (error) {
    console.warn('Falling back to demo chart data.', error);
    renderChart(state.marketData);
    updateMarketNumbers();
  }
}

async function fetchSession() {
  try {
    const response = await fetch('/api/session');
    const data = await response.json();
    if (data.authenticated && data.user) {
      state.authenticated = true;
      state.user = data.user;
      userSession.classList.remove('hidden');
      sessionUsername.textContent = data.user.username;
      loginForm.classList.add('hidden');
      registerForm.classList.add('hidden');
      document.querySelectorAll('.auth-tab').forEach((tab) => tab.classList.remove('active'));
    } else {
      state.authenticated = false;
      state.user = null;
      userSession.classList.add('hidden');
      loginForm.classList.remove('hidden');
      registerForm.classList.add('hidden');
    }
    updateBalanceFromAccount();
    await fetchTrades();
  } catch (error) {
    console.warn('Session fetch failed.', error);
  }
}

async function fetchTrades() {
  try {
    const response = await fetch('/api/trades');
    const data = await response.json();
    renderRecentTrades(data.trades || []);
  } catch (error) {
    console.warn('Trade fetch failed.', error);
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;

  const response = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  const result = await response.json();
  if (!response.ok) {
    alert(result.error || 'Login failed.');
    return;
  }

  loginForm.reset();
  await fetchSession();
  alert(`Welcome back, ${result.user.username}!`);
}

async function handleRegister(event) {
  event.preventDefault();
  const username = document.getElementById('register-username').value.trim();
  const email = document.getElementById('register-email').value.trim();
  const password = document.getElementById('register-password').value;

  const response = await fetch('/api/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  });

  const result = await response.json();
  if (!response.ok) {
    alert(result.error || 'Registration failed.');
    return;
  }

  registerForm.reset();
  await fetchSession();
  alert(`Account created for ${result.user.username}. Demo balance loaded.`);
}

async function handleLogout() {
  const response = await fetch('/api/logout', { method: 'POST' });
  if (response.ok) {
    await fetchSession();
  }
}

tradeForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  if (!state.authenticated) {
    alert('Please log in or create an account first.');
    return;
  }

  const payload = {
    mode: state.currentMode,
    digit: Number(document.getElementById('digit-input').value),
    amount: Number(document.getElementById('amount-input').value),
    prediction: predictionSelect.value,
    threshold: Number(document.getElementById('threshold-input').value),
    account: accountSelect.value,
  };

  try {
    const response = await fetch('/api/trade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || 'Trade failed.');
    }

    state.user = result.account;
    updateBalanceFromAccount();
    await fetchTrades();
    await fetchMarket();
    alert(`${result.message} Result digit: ${result.trade.result_digit}. ${result.trade.won ? 'You won.' : 'You lost.'}`);
  } catch (error) {
    alert(error.message);
  }
});

modeButtons.forEach((button) => {
  button.addEventListener('click', () => {
    modeButtons.forEach((btn) => btn.classList.remove('active'));
    button.classList.add('active');
    state.currentMode = button.dataset.mode;
    syncPredictionOptions();
  });
});

authTabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    authTabs.forEach((btn) => btn.classList.remove('active'));
    tab.classList.add('active');
    const mode = tab.dataset.auth;
    loginForm.classList.toggle('hidden', mode !== 'login');
    registerForm.classList.toggle('hidden', mode !== 'register');
  });
});

loginForm.addEventListener('submit', handleLogin);
registerForm.addEventListener('submit', handleRegister);
logoutBtn.addEventListener('click', handleLogout);
accountSelect.addEventListener('change', updateBalanceFromAccount);

renderChart(state.marketData);
updateMarketNumbers();
syncPredictionOptions();
updateBalanceFromAccount();
fetchMarket();
fetchSession();
