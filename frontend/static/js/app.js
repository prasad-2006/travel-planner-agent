/**
 * Travel Planner Agent – Client-Side JavaScript
 * IBM Cloud Lite / IBM Granite Powered
 */

const API = "/api";
let sessionId = null;
let chatEngine = { label: "IBM Granite", langflow: false };

// ─────────────────────────────────────────────────────────────────────────────
//  Utilities
// ─────────────────────────────────────────────────────────────────────────────

async function post(endpoint, body) {
  const resp = await fetch(API + endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error(`API error ${resp.status}`);
  return resp.json();
}

async function get(endpoint) {
  const resp = await fetch(API + endpoint);
  if (!resp.ok) throw new Error(`API error ${resp.status}`);
  return resp.json();
}

function setLoading(btn, loading, label = "Submit") {
  btn.disabled = loading;
  btn.innerHTML = loading
    ? `<span class="spinner"></span> Working…`
    : label;
}

function showResult(panelId, content, isError = false) {
  const panel = document.getElementById(panelId);
  if (!panel) return;
  panel.classList.remove("loading");
  panel.style.color = isError ? "var(--danger)" : "var(--text)";
  panel.textContent = content;
}

function formatMarkdown(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g,     "<em>$1</em>")
    .replace(/^### (.+)$/gm,   "<h4>$1</h4>")
    .replace(/^## (.+)$/gm,    "<h3>$1</h3>")
    .replace(/^# (.+)$/gm,     "<h2>$1</h2>")
    .replace(/^(\d+)\. (.+)$/gm, "<li>$2</li>")
    .replace(/^- (.+)$/gm,    "<li>$1</li>")
    .replace(/\n{2,}/g, "<br><br>")
    .replace(/\n/g,     "<br>");
}

function showAlert(container, type, msg) {
  const div = document.createElement("div");
  div.className = `alert alert-${type}`;
  div.textContent = msg;
  container.prepend(div);
  setTimeout(() => div.remove(), 5000);
}

// ─────────────────────────────────────────────────────────────────────────────
//  Session bootstrap
// ─────────────────────────────────────────────────────────────────────────────

async function initSession() {
  try {
    sessionId = localStorage.getItem("tpa_session");
    if (!sessionId) {
      const data = await post("/session", {});
      sessionId = data.session_id;
      localStorage.setItem("tpa_session", sessionId);
    }
    window.sessionId = sessionId;
    console.log("Session:", sessionId);
  } catch (e) {
    console.warn("Could not create session:", e);
    sessionId = "local-" + Math.random().toString(36).slice(2, 10);
    window.sessionId = sessionId;
  }
}

async function initEngineStatus() {
  try {
    const h = await get("/health");
    chatEngine.langflow = !!h.langflow_enabled;
    chatEngine.label    = h.langflow_enabled
      ? "Langflow + IBM Granite"
      : "IBM Granite";
    window.chatEngine = chatEngine;

    // Update any engine badges already in the DOM
    document.querySelectorAll(".engine-label").forEach((el) => {
      el.textContent = chatEngine.langflow
        ? "⚡ Langflow · IBM Granite"
        : "⚡ IBM Granite";
    });
    const badge = document.getElementById("engine-badge");
    if (badge) {
      badge.textContent = chatEngine.langflow
        ? "Langflow ✓"
        : "IBM Granite";
      badge.className = chatEngine.langflow
        ? "engine-status-badge langflow-active"
        : "engine-status-badge";
    }
  } catch (_) {
    // health endpoint unreachable — keep defaults
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  Tab switching
// ─────────────────────────────────────────────────────────────────────────────

function initTabs(containerSelector) {
  const container = document.querySelector(containerSelector);
  if (!container) return;
  container.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      container.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      container.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      const target = document.getElementById(btn.dataset.tab);
      if (target) target.classList.add("active");
    });
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  Destination Suggestion
// ─────────────────────────────────────────────────────────────────────────────

function initDestinationForm() {
  const form = document.getElementById("dest-form");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = form.querySelector("button[type=submit]");
    setLoading(btn, true);
    const panel = document.getElementById("dest-result");
    panel.classList.add("loading");
    panel.textContent = "";

    const interests = Array.from(form.querySelectorAll("input[name=interest]:checked"))
      .map((cb) => cb.value);

    const payload = {
      interests,
      budget:            parseFloat(form.budget.value) || 2000,
      currency:          form.currency.value,
      duration:          parseInt(form.duration.value) || 7,
      travel_style:      form.travel_style.value,
      origin:            form.origin.value,
      climate:           form.climate.value,
      avoid:             form.avoid.value,
      destination_query: form.destination_query.value,
      session_id:        sessionId,
    };

    try {
      const data = await post("/destinations/suggest", payload);
      panel.innerHTML = formatMarkdown(data.suggestions);
      // Update session context
      if (sessionId) {
        await fetch(API + "/session/" + sessionId, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      }
    } catch (err) {
      showResult("dest-result", "Error: " + err.message, true);
    } finally {
      setLoading(btn, false, "✈️ Suggest Destinations");
    }
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  Itinerary Builder
// ─────────────────────────────────────────────────────────────────────────────

function initItineraryForm() {
  const form = document.getElementById("itin-form");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = form.querySelector("button[type=submit]");
    setLoading(btn, true);
    const panel = document.getElementById("itin-result");
    panel.classList.add("loading");
    panel.textContent = "";

    const interests = Array.from(form.querySelectorAll("input[name=itin_interest]:checked"))
      .map((cb) => cb.value);

    const payload = {
      destination:  form.itin_destination.value,
      duration:     parseInt(form.itin_duration.value) || 5,
      start_date:   form.itin_start_date.value,
      daily_budget: parseFloat(form.itin_budget.value) || 150,
      currency:     form.itin_currency.value,
      travel_style: form.itin_style.value,
      travellers:   parseInt(form.itin_travellers.value) || 1,
      interests,
      session_id:   sessionId,
    };

    try {
      const data = await post("/itinerary/build", payload);
      // Weather info
      const weather = data.weather_current;
      let weatherHtml = "";
      if (weather) {
        weatherHtml = `\n\n🌤️ Current Weather in ${weather.city}: ${weather.temperature}°C, ${weather.description} | Humidity: ${weather.humidity}%\n\n`;
      }
      panel.innerHTML = weatherHtml + formatMarkdown(data.itinerary);

      // Update stats
      const statsEl = document.getElementById("itin-stats");
      if (statsEl) {
        statsEl.innerHTML = `
          <div class="metric-tile"><div class="value">${data.duration}</div><div class="label">Days</div></div>
          <div class="metric-tile"><div class="value">${data.currency} ${(data.total_budget || 0).toLocaleString()}</div><div class="label">Est. Budget</div></div>
          <div class="metric-tile"><div class="value">${weather ? weather.temperature + "°C" : "–"}</div><div class="label">Current Temp</div></div>
          <div class="metric-tile"><div class="value">${data.travellers || 1}</div><div class="label">Travellers</div></div>
        `;
      }
    } catch (err) {
      showResult("itin-result", "Error: " + err.message, true);
    } finally {
      setLoading(btn, false, "📅 Build Itinerary");
    }
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  Accommodation
// ─────────────────────────────────────────────────────────────────────────────

function initAccomForm() {
  const form = document.getElementById("accom-form");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = form.querySelector("button[type=submit]");
    setLoading(btn, true);
    document.getElementById("accom-result").classList.add("loading");

    const payload = {
      destination:      form.accom_dest.value,
      check_in:         form.accom_checkin.value,
      check_out:        form.accom_checkout.value,
      travellers:       parseInt(form.accom_travellers.value) || 1,
      budget_per_night: parseFloat(form.accom_budget.value) || 100,
      currency:         form.accom_currency.value,
      preferences:      form.accom_prefs.value.split(",").map((s) => s.trim()),
    };

    try {
      const data = await post("/accommodation/recommend", payload);
      document.getElementById("accom-result").innerHTML = formatMarkdown(data.recommendations);
    } catch (err) {
      showResult("accom-result", "Error: " + err.message, true);
    } finally {
      setLoading(btn, false, "🏨 Find Accommodation");
    }
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  Transport
// ─────────────────────────────────────────────────────────────────────────────

function initTransportForm() {
  const form = document.getElementById("transport-form");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = form.querySelector("button[type=submit]");
    setLoading(btn, true);
    document.getElementById("transport-result").classList.add("loading");

    const payload = {
      origin:       form.transport_origin.value,
      destination:  form.transport_dest.value,
      travel_dates: form.transport_dates.value,
      travellers:   parseInt(form.transport_travellers.value) || 1,
      budget:       parseFloat(form.transport_budget.value) || 500,
      currency:     form.transport_currency.value,
      preferences:  ["comfort", "value for money"],
    };

    try {
      const data = await post("/transport/recommend", payload);
      document.getElementById("transport-result").innerHTML = formatMarkdown(data.recommendations);
    } catch (err) {
      showResult("transport-result", "Error: " + err.message, true);
    } finally {
      setLoading(btn, false, "🚀 Get Transport Options");
    }
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  Budget Calculator
// ─────────────────────────────────────────────────────────────────────────────

function initBudgetForm() {
  const form = document.getElementById("budget-form");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = form.querySelector("button[type=submit]");
    setLoading(btn, true);
    document.getElementById("budget-result").classList.add("loading");

    const payload = {
      destination:  form.budget_dest.value,
      duration:     parseInt(form.budget_duration.value) || 7,
      total_budget: parseFloat(form.budget_amount.value) || 2000,
      currency:     form.budget_currency.value,
      travellers:   parseInt(form.budget_travellers.value) || 1,
      travel_style: form.budget_style.value,
    };

    try {
      const data = await post("/budget/calculate", payload);
      document.getElementById("budget-result").innerHTML = formatMarkdown(data.analysis);

      const conv = data.currency_conversions || {};
      const convEl = document.getElementById("currency-conversions");
      if (convEl && Object.keys(conv).length > 0) {
        convEl.innerHTML = Object.entries(conv).map(([k, v]) =>
          `<div class="metric-tile"><div class="value">${k}</div><div class="label">${v.toLocaleString()}</div></div>`
        ).join("");
      }
    } catch (err) {
      showResult("budget-result", "Error: " + err.message, true);
    } finally {
      setLoading(btn, false, "💰 Calculate Budget");
    }
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  Chat
// ─────────────────────────────────────────────────────────────────────────────

function initChat() {
  const input = document.getElementById("chat-input");
  const sendBtn = document.getElementById("chat-send");
  const messages = document.getElementById("chat-messages");
  if (!input || !messages) return;

  function appendBubble(role, text) {
    const div = document.createElement("div");
    div.className = `chat-bubble ${role}`;
    if (role === "assistant") {
      const engineLabel = chatEngine.langflow
        ? "⚡ Langflow · IBM Granite"
        : "⚡ IBM Granite";
      div.innerHTML = `<div class="bubble-header engine-label">${engineLabel}</div>${formatMarkdown(text)}`;
    } else {
      div.textContent = text;
    }
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function showTyping() {
    const div = document.createElement("div");
    div.className = "chat-bubble assistant";
    div.id = "typing-bubble";
    div.innerHTML = `<div class="bubble-header">⚡ IBM Granite</div>
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>`;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  async function sendMessage() {
    const msg = input.value.trim();
    if (!msg) return;
    input.value = "";
    input.style.height = "44px";
    appendBubble("user", msg);
    showTyping();
    sendBtn.disabled = true;

    try {
      const data = await post("/chat", { message: msg, session_id: sessionId });
      if (data.session_id) sessionId = data.session_id;
      document.getElementById("typing-bubble")?.remove();
      appendBubble("assistant", data.response);
    } catch (err) {
      document.getElementById("typing-bubble")?.remove();
      appendBubble("assistant", "⚠️ Connection error. Please try again.");
    } finally {
      sendBtn.disabled = false;
    }
  }

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  input.addEventListener("input", () => {
    input.style.height = "44px";
    input.style.height = Math.min(input.scrollHeight, 120) + "px";
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  Boot
// ─────────────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  await initSession();
  await initEngineStatus();
  initTabs(".planner-tabs");
  initDestinationForm();
  initItineraryForm();
  initAccomForm();
  initTransportForm();
  initBudgetForm();
  initChat();
});
