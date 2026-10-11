"use strict";

const API = "/api";
const HISTORY_KEY = "flight-delay-history";
const HISTORY_LIMIT = 6;

const FEATURE_LABELS = {
  Airline: "Airline",
  Flight: "Flight number",
  AirportFrom: "Origin airport",
  AirportTo: "Destination airport",
  DayOfWeek: "Day of week",
  Time: "Departure time",
  Length: "Flight length",
};

const DAY_SHORT = { 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun" };

const ICONS = {
  ontime: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/><path d="M7.5 12.5l3 3 6-6.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  delayed: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 6.5V12l3.5 2.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
};

const $ = (id) => document.getElementById(id);
const form = $("flight-form");
const fields = {
  origin: $("origin"),
  destination: $("destination"),
  airline: $("airline"),
  flight: $("flight"),
  departure: $("departure"),
  length: $("length"),
};

const state = {
  airports: new Set(),
  airlineNames: {},
  history: loadHistory(),
};

/* ---------- helpers ---------- */

async function api(path, options) {
  const response = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(body.detail)
      ? body.detail.map((d) => d.msg).join(" ")
      : body.detail;
    throw new Error(detail || `Request failed with status ${response.status}.`);
  }
  return body;
}

const pct = (value, digits = 0) => `${(value * 100).toFixed(digits)}%`;
const fmt = (n) => n.toLocaleString("en-US");

function toMinutes(hhmm) {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

function toClock(minutes) {
  const h = String(Math.floor(minutes / 60)).padStart(2, "0");
  const m = String(minutes % 60).padStart(2, "0");
  return `${h}:${m}`;
}

function durationText(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m`;
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function loadHistory() {
  try {
    const stored = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    return Array.isArray(stored) ? stored : [];
  } catch {
    return [];
  }
}

function saveHistory() {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(state.history));
  } catch {
    /* storage unavailable: the board still works for this visit */
  }
}

/* ---------- departure board ---------- */

function flapText(text) {
  return [...String(text)]
    .map((ch, i) => `<span class="flap-char" style="--i:${i}">${ch === " " ? "&nbsp;" : escapeHtml(ch)}</span>`)
    .join("");
}

function renderBoard(animateFirst = false) {
  const rows = $("board-rows");
  rows.innerHTML = state.history
    .map((entry, index) => {
      const status = entry.delayed ? "delayed" : "ontime";
      const flip = animateFirst && index === 0 ? ' class="flipping"' : "";
      return `<tr${flip}>
        <td>${flapText(toClock(entry.departure_minutes))}</td>
        <td>${flapText(`${entry.airline} ${entry.flight}`)}</td>
        <td>${flapText(entry.origin)}</td>
        <td>${flapText(entry.destination)}</td>
        <td class="num">${flapText(pct(entry.delay_probability))}</td>
        <td><span class="status-cell status-${status}">${ICONS[status]}<span>${flapText(entry.delayed ? "Delayed" : "On time")}</span></span></td>
      </tr>`;
    })
    .join("");
  $("board-empty").hidden = state.history.length > 0;
  $("board-clear").hidden = state.history.length === 0;
}

function tickClock() {
  const now = new Date();
  $("board-clock").textContent = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
}

/* ---------- form ---------- */

function renderDays(days) {
  $("day-options").innerHTML = days
    .map(
      (day) => `<label title="${day.name}">
        <input type="radio" name="day" value="${day.value}" ${day.value === 3 ? "checked" : ""}>
        <span aria-hidden="true">${DAY_SHORT[day.value]}</span>
        <span class="visually-hidden">${day.name}</span>
      </label>`
    )
    .join("");
}

async function loadOptions() {
  const options = await api("/options");
  state.airports = new Set(options.airports);
  options.airlines.forEach((a) => (state.airlineNames[a.code] = a.name));

  fields.airline.innerHTML =
    '<option value="">Choose an airline</option>' +
    options.airlines
      .slice()
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((a) => `<option value="${a.code}">${escapeHtml(a.name)} (${a.code})</option>`)
      .join("");
  fields.airline.value = "DL";

  $("airport-list").innerHTML = options.airports.map((code) => `<option value="${code}">`).join("");
  renderDays(options.days);

  fields.origin.value = "ATL";
  fields.destination.value = "JFK";
  updateStub();
  updateRoute();
}

let routeRequest = 0;
async function updateRoute() {
  const origin = fields.origin.value.trim().toUpperCase();
  const destination = fields.destination.value.trim().toUpperCase();
  const hint = $("route-hint");

  if (!state.airports.has(origin) || !state.airports.has(destination)) {
    hint.textContent = "Pick both airports to fill in the typical flight length.";
    return;
  }
  if (origin === destination) {
    hint.textContent = "Origin and destination need to be different airports.";
    return;
  }

  const request = ++routeRequest;
  try {
    const route = await api(`/route?origin=${origin}&destination=${destination}`);
    if (request !== routeRequest) return;
    if (route.known) {
      fields.length.value = route.median_length;
      hint.textContent = `Typical for ${origin} to ${destination}: ${durationText(route.median_length)}, based on ${fmt(route.flights)} flights in the data.`;
    } else {
      hint.textContent = `No ${origin} to ${destination} flights in the data. Enter the scheduled length yourself; the forecast will be less reliable.`;
    }
  } catch {
    hint.textContent = "Couldn't look up this route. Enter the scheduled length yourself.";
  }
}

function showError(message, field) {
  const box = $("form-error");
  box.textContent = message;
  box.hidden = false;
  Object.values(fields).forEach((f) => f.removeAttribute("aria-invalid"));
  if (field) {
    field.setAttribute("aria-invalid", "true");
    field.focus();
  }
}

function clearError() {
  $("form-error").hidden = true;
  Object.values(fields).forEach((f) => f.removeAttribute("aria-invalid"));
}

function readForm() {
  const origin = fields.origin.value.trim().toUpperCase();
  const destination = fields.destination.value.trim().toUpperCase();
  const flight = Number(fields.flight.value);
  const length = Number(fields.length.value);
  const day = Number(form.querySelector('input[name="day"]:checked')?.value);

  if (!state.airports.has(origin)) return showError(`"${origin || "From"}" isn't an airport in the dataset. Use a 3-letter code like ATL.`, fields.origin);
  if (!state.airports.has(destination)) return showError(`"${destination || "To"}" isn't an airport in the dataset. Use a 3-letter code like JFK.`, fields.destination);
  if (origin === destination) return showError("Origin and destination need to be different airports.", fields.destination);
  if (!fields.airline.value) return showError("Choose an airline.", fields.airline);
  if (!Number.isInteger(flight) || flight < 1 || flight > 9999) return showError("Flight number must be between 1 and 9999.", fields.flight);
  if (!fields.departure.value) return showError("Enter a departure time.", fields.departure);
  if (!Number.isInteger(length) || length < 1 || length > 1000) return showError("Flight length must be between 1 and 1000 minutes.", fields.length);

  return {
    airline: fields.airline.value,
    flight,
    origin,
    destination,
    day_of_week: day,
    departure_minutes: toMinutes(fields.departure.value),
    length_minutes: length,
  };
}

/* ---------- forecast ---------- */

function renderForecast(input, result) {
  $("forecast-empty").hidden = true;
  $("forecast-result").hidden = false;

  const verdict = $("verdict");
  const status = result.delayed ? "delayed" : "ontime";
  verdict.className = `verdict is-${status}`;
  verdict.innerHTML = `${ICONS[status]}<span>${result.delayed ? "Likely delayed" : "Likely on time"}</span>`;

  const dayName = form.querySelector(`input[name="day"][value="${input.day_of_week}"]`)?.closest("label")?.title || "";
  $("verdict-route").textContent = `${state.airlineNames[input.airline] || input.airline} ${input.flight}, ${input.origin} to ${input.destination}, ${dayName} at ${toClock(input.departure_minutes)}`;

  $("meter-fill").style.width = pct(result.delay_probability, 1);
  $("probability").innerHTML = `<strong>${pct(result.delay_probability)}</strong> chance of delay. Flights above 50% are marked as delayed.`;

  const notes = [];
  if (Math.abs(result.delay_probability - 0.5) < 0.1) notes.push("This one is close to the line, so treat it as a coin flip.");
  if (!result.route_known) notes.push("This route doesn't appear in the training data, so the model is guessing from similar flights.");
  notes.push("The model gets about 2 out of 3 unseen flights right. It knows schedules, not weather or air traffic on the day.");
  $("forecast-note").textContent = notes.join(" ");
}

async function onSubmit(event) {
  event.preventDefault();
  clearError();
  const input = readForm();
  if (!input) return;

  const button = $("predict-btn");
  button.disabled = true;
  button.textContent = "Predicting…";
  try {
    const result = await api("/predict", { method: "POST", body: JSON.stringify(input) });
    renderForecast(input, result);
    const key = (e) => [e.airline, e.flight, e.origin, e.destination, e.day_of_week, e.departure_minutes, e.length_minutes].join("|");
    const others = state.history.filter((entry) => key(entry) !== key(input));
    state.history = [{ ...input, ...result }, ...others].slice(0, HISTORY_LIMIT);
    saveHistory();
    renderBoard(true);
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Predict delay";
  }
}

/* ---------- model performance ---------- */

const tooltip = $("tooltip");

function showTip(target, html) {
  tooltip.innerHTML = html;
  tooltip.hidden = false;
  const rect = target.getBoundingClientRect();
  const tipRect = tooltip.getBoundingClientRect();
  let left = rect.left + rect.width / 2 - tipRect.width / 2;
  left = Math.max(8, Math.min(left, window.innerWidth - tipRect.width - 8));
  let top = rect.top - tipRect.height - 8;
  if (top < 8) top = rect.bottom + 8;
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
}

function hideTip() {
  tooltip.hidden = true;
}

function attachTip(element, html) {
  element.tabIndex = 0;
  element.addEventListener("mouseenter", () => showTip(element, html));
  element.addEventListener("focus", () => showTip(element, html));
  element.addEventListener("mouseleave", hideTip);
  element.addEventListener("blur", hideTip);
}

function renderConfusionMatrix({ labels, matrix }) {
  const container = $("confusion-matrix");
  const total = matrix.flat().reduce((a, b) => a + b, 0);
  const max = Math.max(...matrix.flat());

  container.innerHTML = `
    <span></span><span class="cm-axis top">Predicted</span>
    <span></span>${labels.map((l) => `<span class="cm-label col">${l}</span>`).join("")}`;

  matrix.forEach((row, i) => {
    const rowTotal = row.reduce((a, b) => a + b, 0);
    const label = document.createElement("span");
    label.className = "cm-label";
    label.textContent = `Actually ${labels[i].toLowerCase()}`;
    container.appendChild(label);

    row.forEach((count, j) => {
      const share = count / max;
      const cell = document.createElement("div");
      cell.className = "cm-cell";
      const strong = share > 0.55;
      cell.style.background = `color-mix(in oklab, var(--seq-4) ${Math.round(share * 100)}%, var(--seq-1))`;
      cell.style.color = strong ? "var(--cm-strong-ink, #fff)" : "var(--ink)";
      cell.dataset.strong = strong;
      cell.innerHTML = `<strong>${fmt(count)}</strong><span>${pct(count / total, 1)} of test flights</span>`;
      const correct = i === j;
      attachTip(
        cell,
        `<b>${correct ? "Correct" : "Wrong"}:</b> ${fmt(count)} flights that were ${labels[i].toLowerCase()} were predicted ${labels[j].toLowerCase()}.<br>${pct(count / rowTotal, 1)} of all ${labels[i].toLowerCase()} flights.`
      );
      cell.setAttribute("aria-label", `Actually ${labels[i]}, predicted ${labels[j]}: ${fmt(count)} flights`);
      container.appendChild(cell);
    });
  });
}

function renderImportance(items) {
  const max = Math.max(...items.map((i) => i.importance));
  const list = $("importance");
  list.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    const name = FEATURE_LABELS[item.feature] || item.feature;
    li.innerHTML = `<span>${name}</span>
      <span class="bar-track"><span class="bar-fill" style="display:block;width:${(item.importance / max) * 100}%"></span></span>
      <span class="bar-value">${pct(item.importance, 1)}</span>`;
    attachTip(li, `<b>${name}</b>: ${pct(item.importance, 1)} of total feature importance`);
    list.appendChild(li);
  });
}

function renderReport(report) {
  $("report-rows").innerHTML = ["On time", "Delayed"]
    .map((cls) => {
      const r = report[cls];
      return `<tr><td>${cls}</td><td class="num">${pct(r.precision, 1)}</td><td class="num">${pct(r.recall, 1)}</td><td class="num">${r["f1-score"].toFixed(3)}</td><td class="num">${fmt(r.support)}</td></tr>`;
    })
    .join("");
}

async function loadMetrics() {
  const m = await api("/metrics");
  $("stat-accuracy").textContent = pct(m.accuracy, 1);
  $("stat-auc").textContent = m.roc_auc.toFixed(3);
  $("stat-train").textContent = fmt(m.dataset.train_rows);
  $("stat-delay").textContent = pct(m.dataset.delay_rate, 1);
  document.querySelectorAll('[data-metric="rows"]').forEach((el) => (el.textContent = fmt(m.dataset.rows)));
  document.querySelectorAll('[data-metric="test_rows"]').forEach((el) => (el.textContent = fmt(m.dataset.test_rows)));

  renderConfusionMatrix(m.confusion_matrix);
  renderImportance(m.feature_importance);
  renderReport(m.classification_report);

  const trained = new Date(m.trained_at);
  $("trained-at").textContent = `Model trained ${trained.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })} with ${m.params.n_estimators} trees in ${m.train_seconds}s.`;
}

function updateStub() {
  const origin = fields.origin.value.trim().toUpperCase() || "---";
  const destination = fields.destination.value.trim().toUpperCase() || "---";
  const day = Number(form.querySelector('input[name="day"]:checked')?.value);
  $("stub-route").innerHTML = `${escapeHtml(origin)} <span>to</span> ${escapeHtml(destination)}`;
  $("stub-flight").textContent = `${fields.airline.value || "--"} ${fields.flight.value || ""}`.trim();
  $("stub-when").textContent = `${DAY_SHORT[day] || ""} ${fields.departure.value || ""}`.trim();
}

/* ---------- wire up ---------- */

form.addEventListener("submit", onSubmit);
form.addEventListener("input", updateStub);
form.addEventListener("change", updateStub);
[fields.origin, fields.destination].forEach((input) => {
  input.addEventListener("input", () => {
    input.value = input.value.toUpperCase().replace(/[^A-Z]/g, "");
    if (input.value.length === 3) updateRoute();
  });
  input.addEventListener("change", updateRoute);
});
$("swap").addEventListener("click", () => {
  [fields.origin.value, fields.destination.value] = [fields.destination.value, fields.origin.value];
  updateStub();
  updateRoute();
});
$("board-clear").addEventListener("click", () => {
  state.history = [];
  saveHistory();
  renderBoard();
});
window.addEventListener("scroll", hideTip, { passive: true });

tickClock();
setInterval(tickClock, 15000);
renderBoard();

loadOptions().catch((error) => showError(`Couldn't load airlines and airports: ${error.message} Is the backend running?`));
loadMetrics().catch(() => {
  $("stats").insertAdjacentHTML("afterend", '<p class="form-error">Model scores are unavailable. Check that the backend is running and the model is trained.</p>');
});
