/**
 * myoneAI / Tamil JARVIS - Local Web Dashboard JavaScript Client
 * Safe, modern, zero-dependency client with XSS protection
 */

// State
let currentTab = "dashboard";
let statusIntervalId = null;
let refreshIntervalSeconds = 10;
let authToken = localStorage.getItem("myoneai_auth_token") || "";

// DOM Elements
const views = {};
const navItems = {};

// Helper: API Fetch wrapper with Auth header
async function apiFetch(url, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  const response = await fetch(url, { ...options, headers });
  
  if (response.status === 401) {
    showToast("Authentication required or token invalid.", "error");
  }

  const data = await response.json();
  if (!response.ok) {
    const errorMsg = data?.error?.message || `HTTP ${response.status} Error`;
    throw new Error(errorMsg);
  }
  return data;
}

// Helper: Safe element creation (Zero raw innerHTML injection)
function createSafeElement(tag, text = "", className = "") {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text) el.textContent = text;
  return el;
}

// Toast Notifications
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = createSafeElement("div", message, `toast toast-${type}`);
  toast.style.cssText = `
    background: ${type === 'error' ? '#ef4444' : (type === 'success' ? '#10b981' : '#1e293b')};
    color: #fff;
    padding: 10px 16px;
    border-radius: 8px;
    margin-top: 8px;
    font-size: 13px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    transition: opacity 0.3s ease;
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Tab Navigation
function switchTab(tabName) {
  currentTab = tabName;
  document.querySelectorAll(".view-section").forEach(v => v.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));

  const targetView = document.getElementById(`view-${tabName}`);
  const targetNav = document.getElementById(`nav-${tabName}`);
  if (targetView) targetView.classList.add("active");
  if (targetNav) targetNav.classList.add("active");

  const pageTitle = document.getElementById("page-title");
  if (pageTitle) {
    pageTitle.textContent = tabName.charAt(0).toUpperCase() + tabName.slice(1);
  }

  // Refresh tab specific data
  if (tabName === "dashboard") loadDashboardData();
  else if (tabName === "tasks") loadTasks();
  else if (tabName === "reminders") loadReminders();
  else if (tabName === "notes") loadNotes();
  else if (tabName === "memory") loadMemory();
  else if (tabName === "system") loadSystemDiagnosis();
  else if (tabName === "settings") loadSettings();
}

// -----------------------------------------------------------------------------
// Telemetry & Assistant Polling
// -----------------------------------------------------------------------------

async function pollStatus() {
  try {
    // 1. Fetch system status
    const sys = await apiFetch("/api/system/status");
    updateSystemMetrics(sys);

    // 2. Fetch assistant status
    const asst = await apiFetch("/api/assistant/status");
    updateAssistantStatus(asst);
  } catch (err) {
    console.debug("Status poll failed:", err.message);
  }
}

function updateSystemMetrics(sys) {
  // Update CPU
  const cpuVal = document.getElementById("cpu-value");
  const cpuBar = document.getElementById("cpu-bar");
  if (cpuVal) cpuVal.textContent = `${sys.cpu_percent}%`;
  if (cpuBar) cpuBar.style.width = `${Math.min(100, sys.cpu_percent)}%`;

  // Update RAM
  const ramVal = document.getElementById("ram-value");
  const ramBar = document.getElementById("ram-bar");
  if (ramVal) ramVal.textContent = `${sys.memory_percent}%`;
  if (ramBar) ramBar.style.width = `${Math.min(100, sys.memory_percent)}%`;

  // Update Disk
  const diskVal = document.getElementById("disk-value");
  const diskBar = document.getElementById("disk-bar");
  if (diskVal) diskVal.textContent = `${sys.disk_percent}%`;
  if (diskBar) diskBar.style.width = `${Math.min(100, sys.disk_percent)}%`;

  // Update Battery
  const batVal = document.getElementById("battery-value");
  const batBar = document.getElementById("battery-bar");
  if (batVal) {
    if (sys.battery_percent !== null) {
      batVal.textContent = `${sys.battery_percent}% ${sys.battery_plugged ? '⚡' : ''}`;
      if (batBar) batBar.style.width = `${Math.min(100, sys.battery_percent)}%`;
    } else {
      batVal.textContent = "N/A (AC Power)";
      if (batBar) batBar.style.width = "100%";
    }
  }

  // Update Network
  const netVal = document.getElementById("network-value");
  if (netVal) {
    netVal.textContent = sys.network_available ? "Connected" : "Offline";
    netVal.style.color = sys.network_available ? "var(--accent-green)" : "var(--accent-red)";
  }
}

function updateAssistantStatus(asst) {
  const state = asst.state || "idle";
  
  // Topbar badge
  const badge = document.getElementById("assistant-status-badge");
  const badgeText = document.getElementById("assistant-status-text");
  if (badge) {
    badge.className = `status-badge ${state}`;
  }
  if (badgeText) {
    badgeText.textContent = state.toUpperCase();
  }

  // Orb in Assistant view
  const orb = document.getElementById("jarvis-orb");
  const orbStateText = document.getElementById("orb-state-text");
  if (orb) {
    orb.className = `jarvis-orb ${state}`;
  }
  if (orbStateText) {
    orbStateText.textContent = `JARVIS is ${state.toUpperCase()}`;
  }
}

// -----------------------------------------------------------------------------
// Assistant Controls & Chat
// -----------------------------------------------------------------------------

async function setAssistantState(action) {
  try {
    const res = await apiFetch(`/api/assistant/${action}`, { method: "POST" });
    showToast(res.message || `Assistant set to ${action}`, "success");
    pollStatus();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function sendChatMessage() {
  const input = document.getElementById("chat-input");
  if (!input) return;

  const msg = input.value.trim();
  if (!msg) return;

  // Render user message safely
  appendChatMessage("user", msg);
  input.value = "";

  // Set visualizer to thinking
  const badge = document.getElementById("assistant-status-badge");
  if (badge) badge.className = "status-badge thinking";
  const badgeText = document.getElementById("assistant-status-text");
  if (badgeText) badgeText.textContent = "THINKING";

  try {
    const data = await apiFetch("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message: msg }),
    });
    appendChatMessage("assistant", data.response);
  } catch (err) {
    appendChatMessage("assistant", `Error: ${err.message}`);
  } finally {
    pollStatus();
  }
}

function appendChatMessage(role, text) {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  const bubble = createSafeElement("div", "", `chat-bubble ${role}`);
  const content = createSafeElement("div", text, "bubble-text");
  const meta = createSafeElement("span", role === "user" ? "You" : "JARVIS", "meta");
  
  bubble.appendChild(meta);
  bubble.appendChild(content);
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

function clearChatHistory() {
  const container = document.getElementById("chat-messages");
  if (container) {
    container.replaceChildren();
    appendChatMessage("assistant", "Chat history cleared. How can I assist you?");
  }
}

// -----------------------------------------------------------------------------
// Tasks View
// -----------------------------------------------------------------------------

async function loadTasks() {
  const listEl = document.getElementById("tasks-list");
  if (!listEl) return;

  try {
    const tasks = await apiFetch("/api/tasks");
    listEl.replaceChildren();

    if (tasks.length === 0) {
      listEl.appendChild(createSafeElement("p", "No tasks found. Create one above!", "text-muted"));
      return;
    }

    tasks.forEach(task => {
      const card = createSafeElement("div", "", "card task-card");
      card.style.marginBottom = "10px";

      const header = createSafeElement("div", "", "card-header");
      const titleSpan = createSafeElement("strong", task.title);
      if (task.status === "COMPLETED") {
        titleSpan.style.textDecoration = "line-through";
        titleSpan.style.color = "var(--text-muted)";
      }

      const badge = createSafeElement("span", task.priority, `badge badge-${task.priority.toLowerCase()}`);
      header.appendChild(titleSpan);
      header.appendChild(badge);

      const body = createSafeElement("div", task.description || "No description", "task-desc");
      body.style.fontSize = "13px";
      body.style.color = "var(--text-secondary)";
      body.style.margin = "8px 0";

      const footer = createSafeElement("div", "", "task-footer");
      footer.style.display = "flex";
      footer.style.justifyContent = "space-between";
      footer.style.alignItems = "center";

      const statusBadge = createSafeElement("span", task.status, `badge badge-${task.status.toLowerCase()}`);
      
      const actions = createSafeElement("div");
      actions.style.display = "flex";
      actions.style.gap = "8px";

      const toggleBtn = createSafeElement("button", task.status === "COMPLETED" ? "Mark Pending" : "Complete", "btn btn-secondary btn-sm");
      toggleBtn.onclick = async () => {
        const nextStatus = task.status === "COMPLETED" ? "TODO" : "COMPLETED";
        await apiFetch(`/api/tasks/${task.id}`, {
          method: "PATCH",
          body: JSON.stringify({ status: nextStatus }),
        });
        loadTasks();
      };

      const delBtn = createSafeElement("button", "Delete", "btn btn-danger btn-sm");
      delBtn.onclick = async () => {
        if (confirm(`Delete task "${task.title}"?`)) {
          await apiFetch(`/api/tasks/${task.id}`, { method: "DELETE" });
          loadTasks();
        }
      };

      actions.appendChild(toggleBtn);
      actions.appendChild(delBtn);

      footer.appendChild(statusBadge);
      footer.appendChild(actions);

      card.appendChild(header);
      card.appendChild(body);
      card.appendChild(footer);
      listEl.appendChild(card);
    });
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleCreateTask(e) {
  e.preventDefault();
  const title = document.getElementById("task-title-input").value.trim();
  const desc = document.getElementById("task-desc-input").value.trim();
  const priority = document.getElementById("task-priority-input").value;
  const due = document.getElementById("task-due-input").value.trim() || null;

  if (!title) return;

  try {
    await apiFetch("/api/tasks", {
      method: "POST",
      body: JSON.stringify({ title, description: desc, priority, due_at: due }),
    });
    showToast("Task created successfully!", "success");
    document.getElementById("task-form").reset();
    loadTasks();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// -----------------------------------------------------------------------------
// Reminders View
// -----------------------------------------------------------------------------

async function loadReminders() {
  const listEl = document.getElementById("reminders-list");
  if (!listEl) return;

  try {
    const reminders = await apiFetch("/api/reminders");
    listEl.replaceChildren();

    if (reminders.length === 0) {
      listEl.appendChild(createSafeElement("p", "No reminders scheduled.", "text-muted"));
      return;
    }

    reminders.forEach(r => {
      const card = createSafeElement("div", "", "card");
      card.style.marginBottom = "10px";

      const header = createSafeElement("div", "", "card-header");
      const msg = createSafeElement("strong", r.message);
      const badge = createSafeElement("span", r.status, `badge badge-${r.status.toLowerCase()}`);
      header.appendChild(msg);
      header.appendChild(badge);

      const timeText = createSafeElement("div", `Trigger: ${new Date(r.trigger_at).toLocaleString()} (${r.recurrence})`, "metric-sub");
      timeText.style.margin = "8px 0";

      const delBtn = createSafeElement("button", "Cancel Reminder", "btn btn-danger btn-sm");
      delBtn.onclick = async () => {
        await apiFetch(`/api/reminders/${r.id}`, { method: "DELETE" });
        loadReminders();
      };

      card.appendChild(header);
      card.appendChild(timeText);
      card.appendChild(delBtn);
      listEl.appendChild(card);
    });
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleCreateReminder(e) {
  e.preventDefault();
  const message = document.getElementById("reminder-msg-input").value.trim();
  const triggerAt = document.getElementById("reminder-time-input").value.trim() || null;
  const recurrence = document.getElementById("reminder-recurrence-input").value;

  if (!message) return;

  try {
    await apiFetch("/api/reminders", {
      method: "POST",
      body: JSON.stringify({ message, trigger_at: triggerAt, recurrence }),
    });
    showToast("Reminder created!", "success");
    document.getElementById("reminder-form").reset();
    loadReminders();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// -----------------------------------------------------------------------------
// Notes View
// -----------------------------------------------------------------------------

async function loadNotes(query = "") {
  const listEl = document.getElementById("notes-list");
  if (!listEl) return;

  try {
    const url = query ? `/api/notes?q=${encodeURIComponent(query)}` : "/api/notes";
    const notes = await apiFetch(url);
    listEl.replaceChildren();

    if (notes.length === 0) {
      listEl.appendChild(createSafeElement("p", "No notes found.", "text-muted"));
      return;
    }

    notes.forEach(note => {
      const card = createSafeElement("div", "", "card");
      card.style.marginBottom = "12px";

      const header = createSafeElement("div", "", "card-header");
      header.appendChild(createSafeElement("strong", note.title));

      const delBtn = createSafeElement("button", "Delete", "btn btn-danger btn-sm");
      delBtn.onclick = async () => {
        if (confirm(`Delete note "${note.title}"?`)) {
          await apiFetch(`/api/notes/${note.id}`, { method: "DELETE" });
          loadNotes();
        }
      };
      header.appendChild(delBtn);

      const content = createSafeElement("p", note.content);
      content.style.fontSize = "13px";
      content.style.color = "var(--text-secondary)";
      content.style.margin = "10px 0";
      content.style.whiteSpace = "pre-wrap";

      const tagsDiv = createSafeElement("div");
      if (note.tags && note.tags.length > 0) {
        note.tags.forEach(t => {
          const pill = createSafeElement("span", `#${t}`, "badge badge-todo");
          pill.style.marginRight = "6px";
          tagsDiv.appendChild(pill);
        });
      }

      card.appendChild(header);
      card.appendChild(content);
      card.appendChild(tagsDiv);
      listEl.appendChild(card);
    });
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleCreateNote(e) {
  e.preventDefault();
  const title = document.getElementById("note-title-input").value.trim();
  const content = document.getElementById("note-content-input").value.trim();
  const tagsRaw = document.getElementById("note-tags-input").value.trim();
  const tags = tagsRaw ? tagsRaw.split(",").map(s => s.trim()).filter(Boolean) : [];

  if (!title || !content) return;

  try {
    await apiFetch("/api/notes", {
      method: "POST",
      body: JSON.stringify({ title, content, tags }),
    });
    showToast("Note saved!", "success");
    document.getElementById("note-form").reset();
    loadNotes();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// -----------------------------------------------------------------------------
// Memory View
// -----------------------------------------------------------------------------

async function loadMemory() {
  const tbody = document.getElementById("memory-table-body");
  const countEl = document.getElementById("memory-total-count");
  if (!tbody) return;

  try {
    const stats = await apiFetch("/api/memory/stats");
    if (countEl) countEl.textContent = `${stats.total_memories} saved memories`;

    const memories = await apiFetch("/api/memory");
    tbody.replaceChildren();

    if (memories.length === 0) {
      const tr = createSafeElement("tr");
      const td = createSafeElement("td", "No memory items stored yet.", "text-muted");
      td.colSpan = 5;
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }

    memories.forEach(m => {
      const tr = createSafeElement("tr");
      
      const catTd = createSafeElement("td");
      catTd.appendChild(createSafeElement("span", m.category, "badge badge-medium"));
      
      const keyTd = createSafeElement("td", m.key);
      const valTd = createSafeElement("td", m.value);
      const upTd = createSafeElement("td", new Date(m.updated).toLocaleDateString());

      const actTd = createSafeElement("td");
      const delBtn = createSafeElement("button", "Delete", "btn btn-danger btn-sm");
      delBtn.onclick = async () => {
        if (confirm(`Delete memory "${m.key}"?`)) {
          await apiFetch(`/api/memory/${m.id}`, { method: "DELETE" });
          loadMemory();
        }
      };
      actTd.appendChild(delBtn);

      tr.appendChild(catTd);
      tr.appendChild(keyTd);
      tr.appendChild(valTd);
      tr.appendChild(upTd);
      tr.appendChild(actTd);
      tbody.appendChild(tr);
    });
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleClearAllMemories() {
  const confirmed = confirm("Are you sure you want to delete all saved memories? This cannot be undone.");
  if (!confirmed) return;

  try {
    await apiFetch("/api/memory?confirmed=true", { method: "DELETE" });
    showToast("All memories cleared.", "success");
    loadMemory();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// -----------------------------------------------------------------------------
// Dashboard Home & Activity
// -----------------------------------------------------------------------------

async function loadDashboardData() {
  await pollStatus();
  loadActivityFeed();
  loadDashboardTaskSummary();
  loadDashboardMemorySummary();
}

async function loadDashboardTaskSummary() {
  const container = document.getElementById("home-tasks-summary");
  if (!container) return;

  try {
    const tasks = await apiFetch("/api/tasks?limit=5");
    container.replaceChildren();
    if (tasks.length === 0) {
      container.appendChild(createSafeElement("p", "No pending tasks for today.", "text-muted"));
      return;
    }
    tasks.slice(0, 4).forEach(t => {
      const row = createSafeElement("div", "", "task-item-row");
      row.style.cssText = "display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid var(--border-subtle); font-size:13px;";
      row.appendChild(createSafeElement("span", t.title));
      row.appendChild(createSafeElement("span", t.status, `badge badge-${t.status.toLowerCase()}`));
      container.appendChild(row);
    });
  } catch (err) {
    console.debug("Dashboard tasks summary err:", err);
  }
}

async function loadDashboardMemorySummary() {
  const countEl = document.getElementById("home-memory-count");
  if (!countEl) return;
  try {
    const stats = await apiFetch("/api/memory/stats");
    countEl.textContent = `${stats.total_memories} items`;
  } catch (err) {
    countEl.textContent = "0 items";
  }
}

async function loadActivityFeed() {
  const feed = document.getElementById("activity-feed-list");
  if (!feed) return;

  try {
    const events = await apiFetch("/api/activity?limit=15");
    feed.replaceChildren();

    if (events.length === 0) {
      feed.appendChild(createSafeElement("li", "No activity recorded yet.", "text-muted"));
      return;
    }

    events.forEach(ev => {
      const li = createSafeElement("li", "", `activity-item ${ev.level.toLowerCase()}`);
      const time = createSafeElement("span", new Date(ev.timestamp).toLocaleTimeString(), "activity-time");
      const text = createSafeElement("span", `[${ev.event_type}] ${ev.description}`, "activity-text");
      li.appendChild(time);
      li.appendChild(text);
      feed.appendChild(li);
    });
  } catch (err) {
    console.debug("Activity feed err:", err);
  }
}

// -----------------------------------------------------------------------------
// System Diagnosis View
// -----------------------------------------------------------------------------

async function loadSystemDiagnosis() {
  try {
    const diag = await apiFetch("/api/system/diagnosis");
    const warnContainer = document.getElementById("system-warnings");
    if (warnContainer) {
      warnContainer.replaceChildren();
      if (diag.warnings.length === 0) {
        warnContainer.appendChild(createSafeElement("div", "All system metrics are within normal operational limits.", "badge badge-low"));
      } else {
        diag.warnings.forEach(w => {
          warnContainer.appendChild(createSafeElement("div", `⚠️ ${w}`, "activity-item warning"));
        });
      }
    }

    // Render top CPU table
    const cpuTbody = document.getElementById("top-cpu-tbody");
    if (cpuTbody) {
      cpuTbody.replaceChildren();
      diag.top_cpu_processes.forEach(p => {
        const tr = createSafeElement("tr");
        tr.appendChild(createSafeElement("td", String(p.pid)));
        tr.appendChild(createSafeElement("td", p.name));
        tr.appendChild(createSafeElement("td", `${p.cpu_percent}%`));
        tr.appendChild(createSafeElement("td", `${p.memory_mb} MB`));
        cpuTbody.appendChild(tr);
      });
    }

    // Render top Memory table
    const memTbody = document.getElementById("top-mem-tbody");
    if (memTbody) {
      memTbody.replaceChildren();
      diag.top_memory_processes.forEach(p => {
        const tr = createSafeElement("tr");
        tr.appendChild(createSafeElement("td", String(p.pid)));
        tr.appendChild(createSafeElement("td", p.name));
        tr.appendChild(createSafeElement("td", `${p.memory_mb} MB`));
        tr.appendChild(createSafeElement("td", `${p.memory_percent}%`));
        memTbody.appendChild(tr);
      });
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

// -----------------------------------------------------------------------------
// Settings View
// -----------------------------------------------------------------------------

async function loadSettings() {
  try {
    const cfg = await apiFetch("/api/settings");
    const appInfo = document.getElementById("settings-app-info");
    if (appInfo) {
      appInfo.textContent = `${cfg.app_name} v${cfg.version} (${cfg.language})`;
    }

    const authState = document.getElementById("settings-auth-status");
    if (authState) {
      authState.textContent = cfg.web_auth_enabled ? "ENABLED" : "DISABLED (Development Mode)";
      authState.style.color = cfg.web_auth_enabled ? "var(--accent-green)" : "var(--accent-yellow)";
    }

    const tokenInput = document.getElementById("settings-token-input");
    if (tokenInput) {
      tokenInput.value = authToken;
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

function handleSaveToken(e) {
  e.preventDefault();
  const tokenInput = document.getElementById("settings-token-input");
  if (!tokenInput) return;

  authToken = tokenInput.value.trim();
  localStorage.setItem("myoneai_auth_token", authToken);
  showToast("Authentication token saved.", "success");
  pollStatus();
}

// -----------------------------------------------------------------------------
// Initialization
// -----------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  // Setup navigation tabs
  document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const tab = item.getAttribute("data-tab");
      if (tab) switchTab(tab);
    });
  });

  // Setup Chat Form
  const chatForm = document.getElementById("chat-form");
  if (chatForm) {
    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      sendChatMessage();
    });
  }

  // Setup Task Form
  const taskForm = document.getElementById("task-form");
  if (taskForm) taskForm.addEventListener("submit", handleCreateTask);

  // Setup Reminder Form
  const reminderForm = document.getElementById("reminder-form");
  if (reminderForm) reminderForm.addEventListener("submit", handleCreateReminder);

  // Setup Note Form
  const noteForm = document.getElementById("note-form");
  if (noteForm) noteForm.addEventListener("submit", handleCreateNote);

  // Setup Note Search
  const noteSearch = document.getElementById("note-search-input");
  if (noteSearch) {
    noteSearch.addEventListener("input", (e) => {
      loadNotes(e.target.value);
    });
  }

  // Setup Token Form
  const tokenForm = document.getElementById("token-form");
  if (tokenForm) tokenForm.addEventListener("submit", handleSaveToken);

  // Initial load
  loadDashboardData();

  // Start periodic status polling
  statusIntervalId = setInterval(pollStatus, refreshIntervalSeconds * 1000);
});
