const chartCanvas = document.getElementById('price-chart');
const ctx = chartCanvas.getContext('2d');
const tradeForm = document.getElementById('trade-form');
const recentTradesEl = document.getElementById('recent-trades');
const accountSelect = document.getElementById('account-select');
const balanceValue = document.getElementById('balance-value');

const state = {
  marketData: [480, 482, 481, 486, 489, 485, 488, 494, 492, 487, 490, 487.42],
  currentMode: 'matches',
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

  for (let i = 0; i <= 5; i++) {
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
  document.getElementById('last-price').textContent = last.toFixed(2);
  document.getElementById('open-price').textContent = state.marketData[0].toFixed(2);
  document.getElementById('high-price').textContent = Math.max(...state.marketData).toFixed(2);
  document.getElementById('low-price').textContent = Math.min(...state.marketData).toFixed(2);
}

function renderRecentTrades(trades) {
  recentTradesEl.innerHTML = ''; 
  trades.forEach((trade) => {
    const row = document.createElement('div');
    row.className = 'trade-row';
    row.innerHTML = `
      <span>${trade.mode.toUpperCase()} / ${trade.digit}</span>
      <strong class="${trade.won ? 'gain' : 'loss'}">${trade.won ? 'Win' : 'Loss'}</strong>
    `;
    recentTradesEl.appendChild(row);
  });
}

function getDemoTradeData() {
  return [
    { mode: 'matches', digit: 5, won: true },
    { mode: 'even_odd', digit: 4, won: false },
    { mode: 'threshold', digit: 7, won: true },
  ];
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

function updateBalanceFromAccount() {
  const selected = accountSelect.value;
  const balances = {
    demo: 5000,
    live: 0,
  };
  balanceValue.textContent = `$${balances[selected].toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

tradeForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const payload = {
    mode: state.currentMode,
    digit: Number(document.getElementById('digit-input').value),
    amount: Number(document.getElementById('amount-input').value),
    prediction: document.getElementById('prediction-select').value,
    account: accountSelect.value,
  };

  try {
    const response = await fetch('/api/demo-trade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || 'Trade failed.');
    }

    const trade = result.trade;
    const balance = result.account.balance;
    balanceValue.textContent = `$${balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const fallbackTrades = getDemoTradeData();
    fallbackTrades.unshift({
      mode: trade.mode,
      digit: trade.digit,
      won: trade.won,
    });
    renderRecentTrades(fallbackTrades.slice(0, 4));
    alert(`Trade placed: ${trade.won ? 'win' : 'loss'} on digit ${trade.result_digit}. Demo mode only.`);
  } catch (error) {
    alert(error.message);
  }
});

document.querySelectorAll('.mode-btn').forEach((button) => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.mode-btn').forEach((btn) => btn.classList.remove('active'));
    button.classList.add('active');
    state.currentMode = button.dataset.mode;
  });
});

accountSelect.addEventListener('change', updateBalanceFromAccount);

renderChart(state.marketData);
updateMarketNumbers();
updateBalanceFromAccount();
renderRecentTrades(getDemoTradeData());
fetchMarket();
