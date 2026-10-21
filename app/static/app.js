/**
 * Study Streak Tracker - Frontend Application
 * Lightweight Vanilla JavaScript client communicating with FastAPI endpoints.
 */

// Application State
const state = {
  today: null,
  timezone: "UTC",
  streak: null,
  goals: null,
  weekly: null,
  chart: null,
  chartGranularity: "day",
  chartDays: 30,
  sessions: [],
  sessionsTotal: 0,
  sessionsLimit: 50,
  sessionsOffset: 0,
  sessionToDeleteId: null,
};

// --- API Client ---
async function api(path, options = {}) {
  const url = path.startsWith("/api") ? path : `/api${path}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const errorMsg = data && data.detail ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)) : "Request failed";
    throw new Error(errorMsg);
  }
  return data;
}

// --- Toast System ---
function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    toast.style.transition = "all 200ms ease";
    setTimeout(() => toast.remove(), 200);
  }, 3500);
}

// --- Renderers ---

function renderStreak(streak) {
  if (!streak) return;
  state.streak = streak;
  state.today = streak.today;

  // Current Streak
  const valCurrent = document.getElementById("val-current-streak");
  valCurrent.textContent = "";
  const countText = document.createTextNode(`${streak.current_streak} `);
  const unitSpan = document.createElement("span");
  unitSpan.className = "unit";
  unitSpan.textContent = "days";
  valCurrent.appendChild(countText);
  valCurrent.appendChild(unitSpan);

  // Today Status
  const subStatus = document.getElementById("sub-today-status");
  if (streak.studied_today) {
    subStatus.textContent = "Studied today ✅";
    subStatus.className = "subtext status-studied";
  } else if (streak.streak_at_risk) {
    subStatus.textContent = "Pending today — streak at risk ⚠️";
    subStatus.className = "subtext status-risk";
  } else {
    subStatus.textContent = "No active streak yet";
    subStatus.className = "subtext";
  }

  // Longest Streak
  const valLongest = document.getElementById("val-longest-streak");
  valLongest.textContent = "";
  const longestText = document.createTextNode(`${streak.longest_streak} `);
  const longestUnit = document.createElement("span");
  longestUnit.className = "unit";
  longestUnit.textContent = "days";
  valLongest.appendChild(longestText);
  valLongest.appendChild(longestUnit);

  // Freeze Status
  const valFreeze = document.getElementById("val-freeze-status");
  const subFreeze = document.getElementById("sub-freeze-info");

  if (!streak.freeze_enabled) {
    valFreeze.textContent = "Disabled";
    subFreeze.textContent = "Turn on in Settings";
  } else if (streak.freeze_available_this_week) {
    valFreeze.textContent = "Available ❄️";
    subFreeze.textContent = "Protected for 1 miss this week";
  } else {
    const lastFrozen = streak.frozen_dates && streak.frozen_dates.length > 0
      ? streak.frozen_dates[streak.frozen_dates.length - 1]
      : "this week";
    valFreeze.textContent = "Used ❄️";
    subFreeze.textContent = `Consumed on ${lastFrozen}`;
  }

  // Set default date on form if empty
  const formDate = document.getElementById("form-date");
  if (!formDate.value && streak.today) {
    formDate.value = streak.today;
    formDate.max = streak.today;
  }
}

function renderGoals(goals) {
  const container = document.getElementById("goals-content");
  if (!container) return;
  container.innerHTML = "";

  if (!goals || (!goals.daily && !goals.weekly)) {
    const emptyMsg = document.createElement("p");
    emptyMsg.className = "subtext";
    emptyMsg.textContent = "No study goals set yet. Click 'Adjust Goals' to set daily or weekly targets.";
    container.appendChild(emptyMsg);
    return;
  }

  // Daily Goal
  if (goals.daily) {
    const item = createGoalBar(
      "Daily Goal",
      goals.daily.done_minutes,
      goals.daily.goal_minutes,
      goals.daily.percent,
      goals.daily.met,
      goals.daily.met ? "Daily goal achieved! 🎉" : `${goals.daily.remaining} min remaining today`
    );
    container.appendChild(item);
  }

  // Weekly Goal
  if (goals.weekly) {
    const weeklySub = goals.weekly.met
      ? "Weekly goal achieved! 🚀"
      : `${goals.weekly.remaining} min remaining (${goals.weekly.required_per_day} min/day required)`;
    const item = createGoalBar(
      "Weekly Goal",
      goals.weekly.done_minutes,
      goals.weekly.goal_minutes,
      goals.weekly.percent,
      goals.weekly.met,
      weeklySub
    );
    container.appendChild(item);
  }
}

function createGoalBar(title, done, goal, percent, met, subtext) {
  const wrap = document.createElement("div");
  wrap.className = "goal-item";

  const header = document.createElement("div");
  header.className = "goal-header";

  const titleSpan = document.createElement("span");
  titleSpan.textContent = title;

  const progressSpan = document.createElement("span");
  progressSpan.textContent = `${done} / ${goal} min (${percent}%)`;

  header.appendChild(titleSpan);
  header.appendChild(progressSpan);

  const track = document.createElement("div");
  track.className = "progress-track";

  const fill = document.createElement("div");
  fill.className = `progress-fill ${met ? "met" : ""}`;
  fill.style.width = `${Math.min(100, percent)}%`;
  track.appendChild(fill);

  const sub = document.createElement("span");
  sub.className = "goal-subtext";
  sub.textContent = subtext;

  wrap.appendChild(header);
  wrap.appendChild(track);
  wrap.appendChild(sub);
  return wrap;
}

function renderWeeklyStats(weekly) {
  const container = document.getElementById("weekly-stats-container");
  const badge = document.getElementById("weekly-total-badge");
  if (!container || !badge) return;
  container.innerHTML = "";

  badge.textContent = `${weekly.total_minutes} min`;

  if (!weekly.subjects || weekly.subjects.length === 0) {
    const emptyP = document.createElement("p");
    emptyP.className = "subtext";
    emptyP.textContent = "No sessions logged yet this week.";
    container.appendChild(emptyP);
    return;
  }

  const maxMinutes = Math.max(...weekly.subjects.map(s => s.minutes), 1);

  weekly.subjects.forEach(stat => {
    const item = document.createElement("div");
    item.className = "subject-bar-item";

    const info = document.createElement("div");
    info.className = "subject-bar-info";

    const nameSpan = document.createElement("span");
    nameSpan.textContent = stat.subject;

    const valSpan = document.createElement("span");
    valSpan.textContent = `${stat.minutes}m (${stat.sessions} ${stat.sessions === 1 ? "session" : "sessions"})`;

    info.appendChild(nameSpan);
    info.appendChild(valSpan);

    const track = document.createElement("div");
    track.className = "subject-bar-track";

    const fill = document.createElement("div");
    fill.className = "subject-bar-fill";
    fill.style.width = `${(stat.minutes / maxMinutes) * 100}%`;

    track.appendChild(fill);
    item.appendChild(info);
    item.appendChild(track);
    container.appendChild(item);
  });
}

function renderChart(timeseries) {
  const canvas = document.getElementById("study-chart");
  if (!canvas || !window.Chart) return;

  const labels = timeseries.points.map(p => {
    if (state.chartGranularity === "week") {
      return `Wk of ${p.date.slice(5)}`;
    }
    return p.date.slice(5); // MM-DD
  });
  const dataValues = timeseries.points.map(p => p.minutes);

  const isDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const gridColor = isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)";
  const textColor = isDark ? "#94A3B8" : "#64748B";

  if (state.chart) {
    state.chart.data.labels = labels;
    state.chart.data.datasets[0].data = dataValues;
    state.chart.update();
    return;
  }

  state.chart = new Chart(canvas, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Minutes Studied",
          data: dataValues,
          backgroundColor: isDark ? "rgba(59, 130, 246, 0.7)" : "rgba(37, 99, 235, 0.7)",
          borderColor: isDark ? "#3B82F6" : "#2563EB",
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.parsed.y} minutes`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: textColor, font: { size: 11 } },
        },
        y: {
          beginAtZero: true,
          grid: { color: gridColor },
          ticks: { color: textColor, font: { size: 11 } },
        },
      },
    },
  });
}

function renderSessionsTable(data, append = false) {
  const tbody = document.getElementById("sessions-tbody");
  const paginationInfo = document.getElementById("pagination-info");
  const loadMoreBtn = document.getElementById("load-more-btn");
  if (!tbody) return;

  if (!append) {
    tbody.innerHTML = "";
    state.sessions = [];
  }

  state.sessions.push(...data.items);
  state.sessionsTotal = data.total;

  if (state.sessions.length === 0) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.className = "text-center subtext";
    cell.textContent = "No study sessions found matching criteria.";
    row.appendChild(cell);
    tbody.appendChild(row);
    paginationInfo.textContent = "0 sessions";
    loadMoreBtn.style.display = "none";
    return;
  }

  data.items.forEach(session => {
    const tr = document.createElement("tr");

    // Date
    const tdDate = document.createElement("td");
    tdDate.textContent = session.date;
    tr.appendChild(tdDate);

    // Subject
    const tdSubject = document.createElement("td");
    const strongSubject = document.createElement("strong");
    strongSubject.textContent = session.subject;
    tdSubject.appendChild(strongSubject);
    tr.appendChild(tdSubject);

    // Duration
    const tdDuration = document.createElement("td");
    tdDuration.textContent = `${session.duration_minutes} min`;
    tr.appendChild(tdDuration);

    // Notes
    const tdNotes = document.createElement("td");
    tdNotes.className = "subtext";
    tdNotes.textContent = session.notes || "—";
    tr.appendChild(tdNotes);

    // Actions
    const tdActions = document.createElement("td");
    tdActions.className = "text-right";
    const actionsWrap = document.createElement("div");
    actionsWrap.className = "action-btns";

    const editBtn = document.createElement("button");
    editBtn.className = "btn btn-secondary btn-xs";
    editBtn.textContent = "Edit";
    editBtn.onclick = () => openEditModal(session);

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "btn btn-danger btn-xs";
    deleteBtn.textContent = "Delete";
    deleteBtn.onclick = () => openDeleteModal(session.id);

    actionsWrap.appendChild(editBtn);
    actionsWrap.appendChild(deleteBtn);
    tdActions.appendChild(actionsWrap);
    tr.appendChild(tdActions);

    tbody.appendChild(tr);
  });

  paginationInfo.textContent = `Showing ${state.sessions.length} of ${data.total}`;
  loadMoreBtn.style.display = state.sessions.length < data.total ? "inline-flex" : "none";

  // Update datalist options
  updateSubjectDatalist();
}

function updateSubjectDatalist() {
  const datalist = document.getElementById("subject-datalist");
  if (!datalist) return;

  const uniqueSubjects = Array.from(new Set(state.sessions.map(s => s.subject)));
  datalist.innerHTML = "";
  uniqueSubjects.forEach(sub => {
    const option = document.createElement("option");
    option.value = sub;
    datalist.appendChild(option);
  });
}

// --- Data Fetchers & Coordinator ---

async function fetchStreak() {
  const data = await api("/streak");
  renderStreak(data);
}

async function fetchGoals() {
  const data = await api("/goals/progress");
  renderGoals(data);
}

async function fetchWeeklyStats() {
  const data = await api("/stats/weekly");
  renderWeeklyStats(data);
}

async function fetchChart() {
  const endDate = state.today || new Date().toISOString().slice(0, 10);
  const startDate = new Date(new Date(endDate).getTime() - (state.chartDays - 1) * 86400000)
    .toISOString()
    .slice(0, 10);

  const data = await api(
    `/stats/timeseries?from=${startDate}&to=${endDate}&granularity=${state.chartGranularity}`
  );
  renderChart(data);
}

async function fetchSessions(append = false) {
  const subject = document.getElementById("filter-subject").value.trim();
  const fromDate = document.getElementById("filter-from").value;
  const toDate = document.getElementById("filter-to").value;

  const offset = append ? state.sessions.length : 0;
  let query = `?limit=${state.sessionsLimit}&offset=${offset}`;
  if (subject) query += `&subject=${encodeURIComponent(subject)}`;
  if (fromDate) query += `&from=${fromDate}`;
  if (toDate) query += `&to=${toDate}`;

  const data = await api(`/sessions${query}`);
  renderSessionsTable(data, append);
}

async function fetchSettings() {
  const data = await api("/settings");
  state.timezone = data.timezone;
  const badge = document.getElementById("timezone-badge");
  if (badge) badge.textContent = data.timezone;
  return data;
}

async function fetchInsights() {
  const container = document.getElementById("insights-content");
  const badge = document.getElementById("ml-confidence-badge");
  if (!container) return;

  try {
    const [risk, forecast, recs] = await Promise.all([
      api("/insights/streak-risk"),
      api("/insights/forecast"),
      api("/insights/recommendations"),
    ]);

    if (badge) {
      badge.textContent = `${risk.confidence.toUpperCase()} CONFIDENCE (${risk.data_days}d data)`;
      badge.className = `badge ${risk.confidence === "high" ? "badge-accent" : (risk.confidence === "medium" ? "badge" : "badge-warning")}`;
    }

    renderInsights(risk, forecast, recs.recommendations);
  } catch (err) {
    container.innerHTML = "";
    const p = document.createElement("p");
    p.className = "subtext";
    p.textContent = "Insights activating as study sessions are recorded.";
    container.appendChild(p);
  }
}

function renderInsights(risk, forecast, recs) {
  const container = document.getElementById("insights-content");
  if (!container) return;
  container.innerHTML = "";

  const grid = document.createElement("div");
  grid.className = "insights-grid";

  // 1. Streak Risk Card
  const riskBox = document.createElement("div");
  riskBox.className = "insight-metric-box";

  const riskHeader = document.createElement("div");
  riskHeader.className = "insight-metric-header";
  const riskTitle = document.createElement("span");
  riskTitle.className = "insight-metric-title";
  riskTitle.textContent = "Tomorrow's Study Probability";
  riskHeader.appendChild(riskTitle);

  const probPercent = Math.round(risk.probability_study_tomorrow * 100);
  const probWrap = document.createElement("div");
  probWrap.className = "insight-prob-display";
  const probVal = document.createElement("span");
  probVal.className = "insight-prob-value";
  probVal.textContent = `${probPercent}%`;
  const riskBadge = document.createElement("span");
  riskBadge.className = `badge ${risk.risk_level === "low" ? "badge-accent" : (risk.risk_level === "medium" ? "badge" : "badge-warning")}`;
  riskBadge.textContent = `${risk.risk_level.toUpperCase()} RISK`;
  probWrap.appendChild(probVal);
  probWrap.appendChild(riskBadge);

  const track = document.createElement("div");
  track.className = "progress-track";
  const fill = document.createElement("div");
  fill.className = `progress-fill ${risk.risk_level === "low" ? "met" : ""}`;
  fill.style.width = `${probPercent}%`;
  track.appendChild(fill);

  const factorList = document.createElement("ul");
  factorList.className = "factors-list";
  risk.top_factors.forEach(f => {
    const li = document.createElement("li");
    li.className = "factor-item";
    const dot = document.createElement("span");
    dot.className = "factor-bullet";
    dot.textContent = "•";
    const text = document.createElement("span");
    text.textContent = f;
    li.appendChild(dot);
    li.appendChild(text);
    factorList.appendChild(li);
  });

  const modelNote = document.createElement("span");
  modelNote.className = "subtext";
  modelNote.style.fontSize = "0.7rem";
  modelNote.textContent = `Model: ${risk.model_used}`;

  riskBox.appendChild(riskHeader);
  riskBox.appendChild(probWrap);
  riskBox.appendChild(track);
  riskBox.appendChild(factorList);
  riskBox.appendChild(modelNote);
  grid.appendChild(riskBox);

  // 2. 7-Day Forecast Card
  const fcBox = document.createElement("div");
  fcBox.className = "insight-metric-box";

  const fcHeader = document.createElement("div");
  fcHeader.className = "insight-metric-header";
  const fcTitle = document.createElement("span");
  fcTitle.className = "insight-metric-title";
  fcTitle.textContent = "7-Day Study Forecast";
  fcHeader.appendChild(fcTitle);

  const fcTotalWrap = document.createElement("div");
  fcTotalWrap.className = "insight-prob-display";
  const fcTotalVal = document.createElement("span");
  fcTotalVal.className = "insight-prob-value";
  fcTotalVal.textContent = `~${forecast.weekly_total}`;
  const fcUnit = document.createElement("span");
  fcUnit.className = "unit";
  fcUnit.textContent = "min next week";
  fcTotalWrap.appendChild(fcTotalVal);
  fcTotalWrap.appendChild(fcUnit);

  // Sparkline bars
  const maxDay = Math.max(...forecast.days.map(d => d.predicted_minutes), 60);
  const sparkline = document.createElement("div");
  sparkline.className = "forecast-sparkline";

  forecast.days.forEach(d => {
    const col = document.createElement("div");
    col.className = "forecast-day-bar";
    const bar = document.createElement("div");
    bar.className = "forecast-bar-fill";
    bar.style.height = `${Math.max(4, (d.predicted_minutes / maxDay) * 100)}%`;
    bar.title = `${d.date}: ${d.predicted_minutes}m`;

    const lbl = document.createElement("span");
    lbl.className = "forecast-day-label";
    lbl.textContent = d.date.slice(8); // day DD
    col.appendChild(bar);
    col.appendChild(lbl);
    sparkline.appendChild(col);
  });

  const fcModelNote = document.createElement("span");
  fcModelNote.className = "subtext";
  fcModelNote.style.fontSize = "0.7rem";
  fcModelNote.textContent = `Model: ${forecast.model_used}` + (forecast.backtest_mae > 0 ? ` (MAE: ${forecast.backtest_mae}m vs naive ${forecast.baseline_mae}m)` : "");

  fcBox.appendChild(fcHeader);
  fcBox.appendChild(fcTotalWrap);
  fcBox.appendChild(sparkline);
  fcBox.appendChild(fcModelNote);
  grid.appendChild(fcBox);

  // 3. Explainable Recommendations List
  if (recs && recs.length > 0) {
    const recsWrap = document.createElement("div");
    recsWrap.className = "recs-container";

    recs.forEach(r => {
      const recItem = document.createElement("div");
      recItem.className = `rec-item ${r.type}`;

      const badge = document.createElement("span");
      badge.className = "rec-badge";
      badge.textContent = r.type.replace("_", " ");

      const msg = document.createElement("span");
      msg.textContent = r.message;

      recItem.appendChild(badge);
      recItem.appendChild(msg);
      recsWrap.appendChild(recItem);
    });

    grid.appendChild(recsWrap);
  }

  container.appendChild(grid);
}

async function refreshAll() {
  try {
    await Promise.all([
      fetchStreak(),
      fetchGoals(),
      fetchWeeklyStats(),
      fetchChart(),
      fetchSessions(false),
      fetchInsights(),
    ]);
  } catch (err) {
    showToast(err.message, "error");
  }
}

// --- Modals & Actions ---

function openEditModal(session) {
  document.getElementById("edit-id").value = session.id;
  document.getElementById("edit-subject").value = session.subject;
  document.getElementById("edit-duration").value = session.duration_minutes;
  const dateInput = document.getElementById("edit-date");
  dateInput.value = session.date;
  dateInput.max = state.today || "";
  document.getElementById("edit-notes").value = session.notes || "";

  document.getElementById("edit-modal").showModal();
}

function openDeleteModal(sessionId) {
  state.sessionToDeleteId = sessionId;
  document.getElementById("delete-modal").showModal();
}

async function openSettingsModal() {
  try {
    const current = await fetchSettings();
    document.getElementById("settings-timezone").value = current.timezone;
    document.getElementById("settings-freeze-enabled").checked = current.freeze_enabled;
    document.getElementById("settings-daily-goal").value = current.daily_goal_minutes || "";
    document.getElementById("settings-weekly-goal").value = current.weekly_goal_minutes || "";
    document.getElementById("settings-modal").showModal();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// --- Event Wiring ---

document.addEventListener("DOMContentLoaded", () => {
  // Initial load
  fetchSettings().then(() => refreshAll());

  // 1. Session Form Submit
  const sessionForm = document.getElementById("session-form");
  const submitBtn = document.getElementById("submit-session-btn");
  const submitBtnText = document.getElementById("submit-btn-text");

  sessionForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    document.getElementById("err-subject").textContent = "";
    document.getElementById("err-duration").textContent = "";
    document.getElementById("err-date").textContent = "";

    const subject = document.getElementById("form-subject").value.trim();
    const duration = parseInt(document.getElementById("form-duration").value, 10);
    const dateVal = document.getElementById("form-date").value;
    const notes = document.getElementById("form-notes").value.trim();

    if (!subject) {
      document.getElementById("err-subject").textContent = "Subject is required.";
      return;
    }
    if (isNaN(duration) || duration < 1 || duration > 1440) {
      document.getElementById("err-duration").textContent = "Duration must be between 1 and 1440 minutes.";
      return;
    }
    if (!dateVal) {
      document.getElementById("err-date").textContent = "Date is required.";
      return;
    }

    try {
      submitBtn.disabled = true;
      submitBtnText.textContent = "Saving...";

      await api("/sessions", {
        method: "POST",
        body: JSON.stringify({
          subject,
          duration_minutes: duration,
          date: dateVal,
          notes: notes || null,
        }),
      });

      showToast(`Logged ${duration} min of ${subject}!`, "success");
      // Reset form but retain today's date
      sessionForm.reset();
      document.getElementById("form-date").value = state.today || "";
      await refreshAll();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      submitBtn.disabled = false;
      submitBtnText.textContent = "Save Session";
    }
  });

  // 2. Quick Date Buttons
  document.getElementById("quick-today-btn").onclick = () => {
    if (state.today) document.getElementById("form-date").value = state.today;
  };
  document.getElementById("quick-yesterday-btn").onclick = () => {
    if (state.today) {
      const yesterday = new Date(new Date(state.today).getTime() - 86400000).toISOString().slice(0, 10);
      document.getElementById("form-date").value = yesterday;
    }
  };

  // 3. Edit Form Submit
  document.getElementById("edit-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const sessionId = document.getElementById("edit-id").value;
    const subject = document.getElementById("edit-subject").value.trim();
    const duration = parseInt(document.getElementById("edit-duration").value, 10);
    const dateVal = document.getElementById("edit-date").value;
    const notes = document.getElementById("edit-notes").value.trim();

    try {
      await api(`/sessions/${sessionId}`, {
        method: "PUT",
        body: JSON.stringify({
          subject,
          duration_minutes: duration,
          date: dateVal,
          notes: notes || null,
        }),
      });
      document.getElementById("edit-modal").close();
      showToast("Session updated successfully!", "success");
      await refreshAll();
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  document.getElementById("cancel-edit-btn").onclick = () => document.getElementById("edit-modal").close();
  document.getElementById("close-edit-modal-btn").onclick = () => document.getElementById("edit-modal").close();

  // 4. Delete Confirmation
  document.getElementById("confirm-delete-btn").onclick = async () => {
    if (!state.sessionToDeleteId) return;
    try {
      await api(`/sessions/${state.sessionToDeleteId}`, { method: "DELETE" });
      document.getElementById("delete-modal").close();
      showToast("Session deleted", "info");
      state.sessionToDeleteId = null;
      await refreshAll();
    } catch (err) {
      showToast(err.message, "error");
    }
  };
  document.getElementById("cancel-delete-btn").onclick = () => document.getElementById("delete-modal").close();
  document.getElementById("close-delete-modal-btn").onclick = () => document.getElementById("delete-modal").close();

  // 5. Settings Modal
  document.getElementById("settings-btn").onclick = openSettingsModal;
  document.getElementById("edit-goals-btn").onclick = openSettingsModal;
  document.getElementById("cancel-settings-btn").onclick = () => document.getElementById("settings-modal").close();
  document.getElementById("close-settings-modal-btn").onclick = () => document.getElementById("settings-modal").close();

  document.getElementById("settings-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const tz = document.getElementById("settings-timezone").value.trim();
    const freeze = document.getElementById("settings-freeze-enabled").checked;
    const dailyRaw = document.getElementById("settings-daily-goal").value;
    const weeklyRaw = document.getElementById("settings-weekly-goal").value;

    const payload = {
      timezone: tz,
      freeze_enabled: freeze,
      daily_goal_minutes: dailyRaw ? parseInt(dailyRaw, 10) : null,
      weekly_goal_minutes: weeklyRaw ? parseInt(weeklyRaw, 10) : null,
    };

    try {
      await api("/settings", {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      document.getElementById("settings-modal").close();
      showToast("Settings saved!", "success");
      await fetchSettings();
      await refreshAll();
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  // 6. CSV Export Trigger
  document.getElementById("export-csv-btn").onclick = () => {
    window.location.href = "/api/export.csv";
  };

  // 7. Chart Toggles
  document.querySelectorAll(".btn-toggle-option[data-granularity]").forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll(".btn-toggle-option[data-granularity]").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.chartGranularity = btn.getAttribute("data-granularity");
      fetchChart();
    };
  });

  document.querySelectorAll(".btn-toggle-option[data-days]").forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll(".btn-toggle-option[data-days]").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.chartDays = parseInt(btn.getAttribute("data-days"), 10);
      fetchChart();
    };
  });

  // 8. Filters & Load More
  let filterTimer = null;
  const triggerFilteredSearch = () => {
    clearTimeout(filterTimer);
    filterTimer = setTimeout(() => fetchSessions(false), 250);
  };

  document.getElementById("filter-subject").addEventListener("input", triggerFilteredSearch);
  document.getElementById("filter-from").addEventListener("change", triggerFilteredSearch);
  document.getElementById("filter-to").addEventListener("change", triggerFilteredSearch);

  document.getElementById("clear-filters-btn").onclick = () => {
    document.getElementById("filter-subject").value = "";
    document.getElementById("filter-from").value = "";
    document.getElementById("filter-to").value = "";
    fetchSessions(false);
  };

  document.getElementById("load-more-btn").onclick = () => {
    fetchSessions(true);
  };
});
