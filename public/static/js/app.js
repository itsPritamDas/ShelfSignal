const state = { overview: null, products: [], stores: [], inventory: [], forecast: null };
const $ = (selector) => document.querySelector(selector);
const number = (value) => Number(value || 0).toLocaleString('en-IN');
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

async function api(url, options = {}) {
  const response = await fetch(url, {cache: 'no-store', ...options});
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
  return payload;
}

function toast(message, isError = false) {
  const element = $('#toast');
  element.textContent = message;
  element.style.background = isError ? '#9d3544' : '#192742';
  element.classList.add('show');
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => element.classList.remove('show'), 3000);
}

function activateSection(section) {
  document.querySelectorAll('.page-section').forEach((element) => element.classList.toggle('active', element.id === `section-${section}`));
  document.querySelectorAll('.nav-link').forEach((element) => element.classList.toggle('active', element.dataset.section === section));
  const labels = {dashboard:'Overview',forecast:'Demand forecast',inventory:'Inventory planner',model:'Data & model'};
  $('#breadcrumbCurrent').textContent = labels[section] || 'Overview';
  $('#sidebar').classList.remove('open');
  if (section === 'inventory' && !state.inventory.length) loadInventory();
}

document.querySelectorAll('.nav-link').forEach((button) => button.addEventListener('click', () => activateSection(button.dataset.section)));
document.querySelectorAll('[data-go]').forEach((button) => button.addEventListener('click', () => activateSection(button.dataset.go)));
$('#mobileMenu').addEventListener('click', () => $('#sidebar').classList.toggle('open'));


// Shared, stock-style hover tooltip for custom SVG charts.
function showChartTooltips(root = document) {
  let tip = document.getElementById('chartHoverTooltip');
  if (!tip) {
    tip = document.createElement('div');
    tip.id = 'chartHoverTooltip';
    tip.className = 'chart-hover-tooltip';
    tip.setAttribute('role', 'status');
    document.body.appendChild(tip);
  }
  root.querySelectorAll('[data-chart-tip]').forEach((point) => {
    if (point.dataset.tipBound) return;
    point.dataset.tipBound = '1';
    const move = (event) => {
      tip.innerHTML = point.dataset.chartTip;
      tip.classList.add('visible');
      const x = Math.min(event.clientX + 14, window.innerWidth - tip.offsetWidth - 12);
      const y = Math.max(12, event.clientY - tip.offsetHeight - 14);
      tip.style.left = `${Math.max(12, x)}px`;
      tip.style.top = `${y}px`;
    };
    point.addEventListener('pointerenter', move);
    point.addEventListener('pointermove', move);
    point.addEventListener('pointerleave', () => tip.classList.remove('visible'));
    point.addEventListener('focus', (event) => move({clientX: event.target.getBoundingClientRect().left, clientY: event.target.getBoundingClientRect().top}));
    point.addEventListener('blur', () => tip.classList.remove('visible'));
  });
}

function renderSalesChart(items) {
  const container = $('#salesChart');
  if (!items || !items.length) { container.innerHTML = '<div class="empty-state">No sales history available.</div>'; return; }
  const width = 720, height = 220, left = 42, right = 12, top = 13, bottom = 27;
  const values = items.map((item) => item.units);
  const max = Math.max(10, ...values) * 1.12;
  const x = (index) => left + index * ((width - left - right) / Math.max(1, items.length - 1));
  const y = (value) => height - bottom - (value / max) * (height - top - bottom);
  const points = items.map((item, index) => [x(index), y(item.units)]);
  const line = points.map((point, index) => `${index ? 'L' : 'M'}${point[0].toFixed(1)},${point[1].toFixed(1)}`).join(' ');
  const area = `${line} L${points[points.length - 1][0]},${height-bottom} L${points[0][0]},${height-bottom} Z`;
  const grid = [0, .33, .66, 1].map((fraction) => {
    const gy = height - bottom - fraction * (height - top - bottom);
    return `<line class="chart-gridline" x1="${left}" y1="${gy}" x2="${width-right}" y2="${gy}"/><text class="chart-label" x="${left-8}" y="${gy+3}" text-anchor="end">${Math.round(max*fraction)}</text>`;
  }).join('');
  const labelIndexes = [0, Math.floor((items.length-1)/3), Math.floor(2*(items.length-1)/3), items.length-1];
  const labels = [...new Set(labelIndexes)].map((index) => `<text class="chart-label" x="${x(index)}" y="${height-7}" text-anchor="middle">${new Date(`${items[index].date}T00:00:00`).toLocaleDateString('en-IN',{day:'numeric',month:'short'})}</text>`).join('');
  const last = points[points.length - 1];
  const hoverPoints = points.map((point, index) => `<circle class="chart-hover-point" cx="${point[0]}" cy="${point[1]}" r="8" tabindex="0" data-chart-tip="<strong>${escapeHtml(new Date(`${items[index].date}T00:00:00`).toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short',year:'numeric'}))}</strong><span>Sales: <b>${number(items[index].units)} units</b></span>"/>`).join('');
  container.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Daily sales trend"><defs><linearGradient id="salesGradient" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#4b73ef" stop-opacity=".20"/><stop offset="100%" stop-color="#4b73ef" stop-opacity="0"/></linearGradient></defs>${grid}<path class="chart-area" d="${area}"/><path class="chart-line" d="${line}"/><circle class="chart-point" cx="${last[0]}" cy="${last[1]}" r="4"/>${hoverPoints}${labels}</svg>`;
  showChartTooltips(container);
  $('#salesTotal').textContent = `${number(values.reduce((sum, value) => sum + value, 0))} units`;
}

function renderCategoryMix(items) {
  const container = $('#categoryChart');
  if (!items || !items.length) { container.innerHTML = '<div class="empty-state">No category data available.</div>'; return; }
  const colors = ['#4d73ee','#8a70e7','#29a993','#e9a342','#58a7d8','#de7f93','#86a65d'];
  const total = items.reduce((sum, item) => sum + item.units, 0);
  let offset = 0;
  const segments = items.map((item, index) => {
    const fraction = total ? item.units / total : 0;
    const segment = `<circle class="donut-segment" cx="60" cy="60" r="48" fill="none" stroke="${colors[index % colors.length]}" stroke-width="13" stroke-dasharray="${fraction*301.6} ${301.6-fraction*301.6}" stroke-dashoffset="${-offset*301.6}" tabindex="0" data-chart-tip="<strong>${escapeHtml(item.category)}</strong><span>Sales: <b>${number(item.units)} units</b></span><span>Share: <b>${(fraction*100).toFixed(1)}%</b></span>"/>`;
    offset += fraction;
    return segment;
  }).join('');
  const legend = items.slice(0, 6).map((item, index) => {
    const percent = total ? item.units / total * 100 : 0;
    return `<div><div class="category-item"><i style="background:${colors[index % colors.length]}"></i><span>${escapeHtml(item.category)}</span><strong>${percent.toFixed(0)}%</strong></div><div class="category-bar"><span style="width:${percent}%;background:${colors[index % colors.length]}"></span></div></div>`;
  }).join('');
  container.innerHTML = `<div class="donut-row"><div class="donut"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="48" fill="none" stroke="#f0f2f7" stroke-width="13"/>${segments}</svg><div class="donut-center"><strong>${number(total)}</strong><small>UNITS SOLD</small></div></div><div class="category-legend">${legend}</div></div>`;
  showChartTooltips(container);
}

function renderTopProducts(items) {
  const max = Math.max(1, ...items.map((item) => item.units));
  $('#topProducts').innerHTML = items.length ? items.map((item) => `<tr><td><span class="product-name-cell">${escapeHtml(item.product_name)}</span><span class="product-id">${escapeHtml(item.product_id)}</span></td><td>${escapeHtml(item.category || '—')}</td><td><strong>${number(item.units)}</strong></td><td><div class="mini-bar"><span style="width:${(item.units/max*100).toFixed(1)}%"></span></div></td></tr>`).join('') : '<tr><td colspan="4" class="empty-cell">No product sales found.</td></tr>';
}

function renderMetrics(metrics) {
  $('#modelMetrics').innerHTML = metrics.map((item) => `<tr><td><strong>${escapeHtml(item.model)}</strong></td><td>${Number(item.mae).toFixed(2)}</td><td>${Number(item.rmse).toFixed(2)}</td><td><strong>${Number(item.wape).toFixed(1)}%</strong></td><td>${Number(item.r2).toFixed(3)}</td></tr>`).join('');
}

function renderFeatureImportance(items) {
  const container = $('#featureImportance');
  if (!items || !items.length) {
    container.innerHTML = '<div class="empty-state">Feature-level importance is unavailable for the selected estimator. Compare the benchmark metrics and review the feature engineering notes.</div>';
    return;
  }
  const max = Math.max(...items.map((item) => item.importance), 0.0001);
  container.innerHTML = items.map((item) => `<div class="feature-row"><label>${escapeHtml(item.feature)}</label><strong>${(item.importance*100).toFixed(1)}%</strong><div class="feature-track"><span style="width:${item.importance/max*100}%"></span></div></div>`).join('');
}

async function loadOverview() {
  try {
    const data = await api('/api/overview');
    state.overview = data;
    $('#kpiUnits').textContent = number(data.kpis.units_30d);
    $('#kpiProducts').textContent = number(data.kpis.active_products);
    $('#kpiStores').textContent = number(data.kpis.stores);
    $('#kpiRisk').textContent = number(data.kpis.at_risk_items);
    const change = data.kpis.sales_change_pct;
    const changeEl = $('#kpiChange');
    changeEl.textContent = `${change > 0 ? '+' : ''}${change.toFixed(1)}%`;
    changeEl.className = `trend ${change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral'}`;
    $('#lastDataDate').textContent = data.last_data_date;
    $('#modelMetrics').innerHTML = '';
    $('#forecastModelName').textContent = data.model.name;
    $('#backtestNote').textContent = `Trained ${new Date(data.model.trained_at).toLocaleString()} · ${data.model.training_rows.toLocaleString()} feature rows. ${data.model.backtest_note}`;
    renderSalesChart(data.daily_sales);
    renderCategoryMix(data.category_mix);
    renderTopProducts(data.top_products);
    renderMetrics(data.model.metrics);
    renderFeatureImportance(data.model.feature_importance);
    $('#forecastModel').textContent = data.model.name;
    $('#forecastModel').title = 'Selected using validation WAPE; test metrics shown separately';
  } catch (error) {
    toast(error.message, true);
    $('#salesChart').innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}

async function loadProducts() {
  try {
    const data = await api('/api/products');
    state.products = data.products;
    state.stores = data.stores;
    const productSelect = $('#forecastProduct');
    productSelect.innerHTML = data.products.map((item) => `<option value="${escapeHtml(item.product_id)}">${escapeHtml(item.product_name)} (${escapeHtml(item.product_id)})</option>`).join('');
    $('#forecastStore').innerHTML = data.stores.map((store) => `<option value="${escapeHtml(store)}">${escapeHtml(store.replace('_',' '))}</option>`).join('');
  } catch (error) { toast(error.message, true); }
}

function renderForecastChart(data) {
  const container = $('#forecastChart');
  const history = data.history || [], forecast = data.forecast || [];
  const combined = [...history.map((item) => ({date:item.date,value:item.actual,type:'actual'})), ...forecast.map((item) => ({date:item.date,value:item.forecast,type:'forecast'}))];
  if (!combined.length) { container.innerHTML = '<div class="empty-state">No forecast data to display.</div>'; return; }
  const width=850,height=280,left=45,right=15,top=15,bottom=32;
  const vals=combined.map((item)=>item.value),max=Math.max(10,...vals)*1.12;
  const x=(index)=>left+index*((width-left-right)/Math.max(1,combined.length-1));
  const y=(value)=>height-bottom-(value/max)*(height-top-bottom);
  const actualPts=history.map((item,index)=>[x(index),y(item.actual)]);
  const forecastPts=forecast.map((item,index)=>[x(history.length-1+index),y(item.forecast)]);
  const path=(points)=>points.map((p,i)=>`${i?'L':'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const grid=[0,.33,.66,1].map((f)=>{const gy=height-bottom-f*(height-top-bottom);return `<line class="chart-gridline" x1="${left}" y1="${gy}" x2="${width-right}" y2="${gy}"/><text class="chart-label" x="${left-8}" y="${gy+3}" text-anchor="end">${Math.round(max*f)}</text>`}).join('');
  const indices=[0,Math.floor((combined.length-1)/3),Math.floor(2*(combined.length-1)/3),combined.length-1];
  const labels=[...new Set(indices)].map((i)=>`<text class="chart-label" x="${x(i)}" y="${height-9}" text-anchor="middle">${new Date(`${combined[i].date}T00:00:00`).toLocaleDateString('en-IN',{day:'numeric',month:'short'})}</text>`).join('');
  const splitX=x(history.length-1);
  const actualTips = history.map((item,index)=>`<circle class="chart-hover-point" cx="${actualPts[index][0]}" cy="${actualPts[index][1]}" r="8" tabindex="0" data-chart-tip="<strong>${escapeHtml(new Date(`${item.date}T00:00:00`).toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short',year:'numeric'}))}</strong><span>Actual sales: <b>${number(item.actual)} units</b></span>"/>`).join('');
  const forecastTips = forecast.map((item,index)=>`<circle class="chart-hover-point forecast-hover-point" cx="${forecastPts[index][0]}" cy="${forecastPts[index][1]}" r="8" tabindex="0" data-chart-tip="<strong>${escapeHtml(new Date(`${item.date}T00:00:00`).toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short',year:'numeric'}))}</strong><span>Forecast: <b>${number(item.forecast)} units</b></span>"/>`).join('');
  container.innerHTML=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Actual and forecast demand"><defs><linearGradient id="forecastGradient" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#9b80f3" stop-opacity=".13"/><stop offset="100%" stop-color="#9b80f3" stop-opacity="0"/></linearGradient></defs>${grid}<line x1="${splitX}" y1="${top}" x2="${splitX}" y2="${height-bottom}" stroke="#cbd2e2" stroke-dasharray="4 4"/><path class="chart-line" d="${path(actualPts)}"/><path class="forecast-line" d="${path(forecastPts)}"/><circle class="chart-point" cx="${splitX}" cy="${actualPts.at(-1)[1]}" r="4"/>${actualTips}${forecastTips}${labels}</svg>`;
  showChartTooltips(container);
}

async function loadForecast() {
  const product = $('#forecastProduct').value;
  const store = $('#forecastStore').value;
  const horizon = $('#forecastHorizon').value;
  if (!product || !store) return;
  $('#runForecast').disabled = true;
  $('#runForecast').textContent = 'Calculating…';
  try {
    const data = await api(`/api/forecast?product_id=${encodeURIComponent(product)}&store_id=${encodeURIComponent(store)}&horizon=${horizon}`);
    state.forecast = data;
    $('#forecastUnits').textContent = number(data.forecast_total);
    $('#forecastAverage').textContent = `${data.daily_average} units`;
    $('#forecastModel').textContent = data.model_name;
    $('#forecastModelName').textContent = data.model_name;
    $('#forecastSubtitle').textContent = `${data.product_name} · ${data.store_id} · Last actual: ${data.last_actual_date}`;
    renderForecastChart(data);
    const recentAverage = data.history.slice(-7).reduce((sum,item)=>sum+item.actual,0) / Math.max(1, data.history.slice(-7).length);
    const difference = recentAverage ? ((data.daily_average - recentAverage) / recentAverage) * 100 : 0;
    const direction = difference > 2 ? 'higher' : difference < -2 ? 'lower' : 'similar';
    $('#forecastInsight').textContent = `The model estimates ${number(data.forecast_total)} units over the next ${data.horizon} days, averaging ${data.daily_average} units per day. The forecast daily average is ${Math.abs(difference).toFixed(1)}% ${direction} than the most recent seven-day average (${recentAverage.toFixed(1)} units/day). The forecast assumes no future promotions and uses the latest recorded price. Treat this as a planning estimate, not a guaranteed outcome.`;
  } catch (error) {
    $('#forecastChart').innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
    toast(error.message, true);
  } finally {
    $('#runForecast').disabled = false;
    $('#runForecast').innerHTML = 'Generate forecast <span>→</span>';
  }
}
$('#runForecast').addEventListener('click', loadForecast);
$('#forecastHorizon').addEventListener('change', () => { if (state.forecast) loadForecast(); });
$('#forecastProduct').addEventListener('change', () => { if (state.products.length) loadForecast(); });
$('#forecastStore').addEventListener('change', () => { if (state.stores.length) loadForecast(); });

function renderInventory(items) {
  state.inventory = items;
  const counts = {total:items.length, risk:0, reorder:0, healthy:0};
  items.forEach((item) => {
    if (item.status === 'At risk') counts.risk += 1;
    else if (item.status === 'Reorder soon') counts.reorder += 1;
    else counts.healthy += 1;
  });
  $('#invTotal').textContent = number(counts.total);
  $('#invRisk').textContent = number(counts.risk);
  $('#invReorder').textContent = number(counts.reorder);
  $('#invHealthy').textContent = number(counts.healthy);

  const filter = $('#inventoryFilter').value;
  const query = ($('#inventorySearch')?.value || '').trim().toLowerCase();
  const visible = items.filter((item) => {
    const statusMatch = filter === 'all' || item.status === filter;
    const textMatch = !query || `${item.product_name} ${item.product_id} ${item.store_id} ${item.category || ''}`.toLowerCase().includes(query);
    return statusMatch && textMatch;
  });
  $('#inventoryRows').innerHTML = visible.length ? visible.map((item) => {
    const statusClass = item.status === 'At risk' ? 'status-at-risk' : item.status === 'Reorder soon' ? 'status-reorder' : 'status-healthy';
    return `<tr>
      <td><span class="product-name-cell">${escapeHtml(item.product_name)}</span><span class="product-id">${escapeHtml(item.product_id)} · ${escapeHtml(item.store_id)}</span></td>
      <td><input class="stock-input" type="number" min="0" value="${item.current_stock}" id="stock-${item.id}" aria-label="Current stock for ${escapeHtml(item.product_name)}"></td>
      <td><input class="stock-input" type="number" min="1" max="90" value="${item.lead_time_days}" id="lead-${item.id}" aria-label="Lead time days for ${escapeHtml(item.product_name)}"></td>
      <td><input class="stock-input" type="number" min="0" max="90" value="${item.safety_stock_days}" id="safety-${item.id}" aria-label="Safety stock days for ${escapeHtml(item.product_name)}"></td>
      <td><strong>${number(item.lead_time_demand)}</strong><span class="unit-label">units</span></td>
      <td><strong>${number(item.reorder_point)}</strong><span class="unit-label">units</span></td>
      <td><strong class="order-quantity">${number(item.suggested_order)}</strong><span class="unit-label">units</span></td>
      <td><span class="status-badge ${statusClass}">${escapeHtml(item.status)}</span><span class="coverage-label">${item.coverage_days == null ? 'Coverage n/a' : `${item.coverage_days} days cover`}</span></td>
      <td><button class="small-save" data-save-inventory="${item.id}">Save changes</button></td>
    </tr>`;
  }).join('') : '<tr><td colspan="9" class="empty-cell">No matching products. Try another search or status.</td></tr>';

  document.querySelectorAll('[data-save-inventory]').forEach((button) => button.addEventListener('click', async () => {
    const id = button.dataset.saveInventory;
    const value = Number($(`#stock-${id}`).value);
    const lead = Number($(`#lead-${id}`).value);
    const safety = Number($(`#safety-${id}`).value);
    if (!Number.isInteger(value) || value < 0 || !Number.isInteger(lead) || lead < 1 || lead > 90 || !Number.isInteger(safety) || safety < 0 || safety > 90) { toast('Enter valid whole numbers for stock, lead time and safety stock.', true); return; }
    button.disabled = true;
    button.textContent = 'Saving…';
    try {
      await api(`/api/inventory/${id}`, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({current_stock:value,lead_time_days:lead,safety_stock_days:safety})});
      toast('Inventory inputs saved. Recommendations updated.');
      await loadInventory();
      if (state.overview) loadOverview();
    } catch (error) { toast(error.message,true); }
    finally { button.disabled = false; button.textContent = 'Save changes'; }
  }));
}

async function loadInventory() {
  const button = $('#refreshInventory');
  if (button) { button.disabled = true; button.textContent = 'Updating…'; }
  if (!state.inventory.length) {
    $('#inventoryRows').innerHTML = '<tr><td colspan="9"><div class="inventory-loading"><span class="loading-spinner"></span><strong>Preparing inventory insights</strong><small>Aggregating recent demand and stock inputs…</small></div></td></tr>';
  }
  try {
    const data = await api('/api/inventory');
    renderInventory(data.items);
    $('#inventoryUpdated').textContent = `Updated ${new Date().toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})}`;
  } catch (error) {
    $('#inventoryRows').innerHTML = `<tr><td colspan="9" class="empty-cell">${escapeHtml(error.message)}</td></tr>`;
    toast(error.message,true);
  } finally {
    if (button) { button.disabled = false; button.textContent = '↻ Refresh plan'; }
  }
}
$('#refreshInventory').addEventListener('click', loadInventory);
$('#inventoryFilter').addEventListener('change', () => renderInventory(state.inventory));
$('#inventorySearch').addEventListener('input', () => renderInventory(state.inventory));

$('#retrainModel').addEventListener('click', async () => {
  const button = $('#retrainModel');
  button.disabled = true; button.textContent = 'Training…';
  try {
    const result = await api('/api/retrain',{method:'POST'});
    renderMetrics(result.metrics);
    toast(`Training complete. Selected: ${result.name}`);
    await loadOverview();
  } catch (error) { toast(error.message,true); }
  finally { button.disabled=false; button.textContent='↻ Retrain models'; }
});

$('#uploadCsv').addEventListener('click', async () => {
  const file = $('#csvFile').files[0];
  if (!file) { toast('Choose a CSV file first.', true); return; }
  const data = new FormData(); data.append('file',file);
  $('#uploadCsv').disabled=true; $('#uploadCsv').textContent='Uploading…'; $('#uploadMessage').textContent='';
  try {
    const result = await api('/api/upload',{method:'POST',body:data});
    $('#uploadMessage').textContent = `${result.rows_processed} rows processed across ${result.products_seen} products and ${result.stores_seen} stores.`;
    toast('Dataset imported. Retrain the model to refresh forecasts.');
    await loadProducts(); await loadOverview(); await loadForecast(); await loadInventory();
  } catch(error) { $('#uploadMessage').textContent=error.message; $('#uploadMessage').style.color='#c94d5a'; toast(error.message,true); }
  finally { $('#uploadCsv').disabled=false; $('#uploadCsv').textContent='Upload dataset'; }
});

(async function init() {
  await Promise.all([loadProducts(), loadOverview(), loadInventory()]);
  if ($('#forecastProduct').value && $('#forecastStore').value) loadForecast();
})();
