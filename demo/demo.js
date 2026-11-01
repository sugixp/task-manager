// Static demo of Task Manager for GitHub Pages.
// Mirrors the rules of task_manager/core.py, storing tasks in localStorage
// instead of SQLite. The markup matches the Flask templates so both share
// the same style.css.

"use strict";

const STORAGE_KEY = "task-manager-demo";
const MAX_TITLE_LENGTH = 200;
const PRIORITIES = ["low", "medium", "high"];
const PRIORITY_RANK = { high: 0, medium: 1, low: 2 };
const STATUSES = ["all", "pending", "done"];

const SAMPLE_TASKS = [
  { title: "Update portfolio with the new web UI", priority: "high", done: false },
  { title: "Prepare for the technical interview", priority: "high", done: false },
  { title: "Plan next sprint", priority: "medium", done: false },
  { title: "Read Fluent Python, chapter 5", priority: "low", done: false },
  { title: "Write unit tests for the core", priority: "high", done: true },
  { title: "Review pull requests", priority: "medium", done: true },
];

const EMPTY_MESSAGES = {
  all: ["No tasks yet", "Add your first task above to get started."],
  pending: ["Nothing pending", "You're all caught up!"],
  done: ["No completed tasks yet", "Finished tasks will show up here."],
};

class ValidationError extends Error {}

// ---------- Storage ----------

function sampleState() {
  const tasks = SAMPLE_TASKS.map((task, index) => ({ id: index + 1, ...task }));
  return { nextId: tasks.length + 1, tasks };
}

function loadState() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw === null) {
    return { state: sampleState(), recovered: false }; // first visit
  }
  try {
    const state = JSON.parse(raw);
    if (!Array.isArray(state.tasks) || !Number.isInteger(state.nextId)) {
      throw new Error("Unexpected format");
    }
    return { state, recovered: false };
  } catch {
    return { state: sampleState(), recovered: true };
  }
}

function saveState() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Storage may be full or disabled; the demo keeps working in memory.
  }
}

// ---------- Business rules (same as core.py) ----------

function cleanTitle(title) {
  const cleaned = (title || "").trim();
  if (!cleaned) {
    throw new ValidationError("Title cannot be empty.");
  }
  if (cleaned.length > MAX_TITLE_LENGTH) {
    throw new ValidationError(`Title must be at most ${MAX_TITLE_LENGTH} characters.`);
  }
  return cleaned;
}

function cleanPriority(priority) {
  const cleaned = (priority || "").trim().toLowerCase();
  if (!PRIORITIES.includes(cleaned)) {
    throw new ValidationError(`Priority must be one of: ${PRIORITIES.join(", ")}.`);
  }
  return cleaned;
}

function getTask(id) {
  const task = state.tasks.find((t) => t.id === id);
  if (!task) {
    throw new ValidationError(`Task ${id} not found.`);
  }
  return task;
}

function addTask(title, priority) {
  const task = {
    id: state.nextId,
    title: cleanTitle(title),
    priority: cleanPriority(priority),
    done: false,
  };
  state.nextId += 1;
  state.tasks.push(task);
  saveState();
  return task;
}

function updateTask(id, title, priority) {
  const task = getTask(id);
  const cleaned = { title: cleanTitle(title), priority: cleanPriority(priority) };
  Object.assign(task, cleaned);
  saveState();
  return task;
}

function toggleDone(id) {
  const task = getTask(id);
  task.done = !task.done;
  saveState();
  return task;
}

function deleteTask(id) {
  const task = getTask(id);
  state.tasks = state.tasks.filter((t) => t.id !== id);
  saveState();
  return task;
}

// Pending first, then by priority (high first), then oldest first.
function listTasks(status) {
  return state.tasks
    .filter((t) => status === "all" || t.done === (status === "done"))
    .sort(
      (a, b) =>
        a.done - b.done ||
        PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority] ||
        a.id - b.id
    );
}

function countTasks() {
  const done = state.tasks.filter((t) => t.done).length;
  return { all: state.tasks.length, pending: state.tasks.length - done, done };
}

// ---------- UI ----------

const $ = (id) => document.getElementById(id);

let { state, recovered } = loadState();
let editingId = null;

function currentStatus() {
  const status = location.hash.slice(1);
  return STATUSES.includes(status) ? status : "all";
}

function el(tag, attributes = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    node.setAttribute(name, value);
  }
  node.append(...children); // strings become text nodes, so titles are never parsed as HTML
  return node;
}

function showAlert(message, kind = "success") {
  $("alerts").replaceChildren(
    el("p", { class: `alert alert-${kind}`, role: "status" }, message)
  );
}

function clearAlert() {
  $("alerts").replaceChildren();
}

function showFieldError(id, message) {
  const field = $(id);
  field.textContent = message || "";
  field.hidden = !message;
}

function renderTask(task) {
  const nextState = task.done ? "pending" : "done";
  return el(
    "li",
    { class: task.done ? "task is-done" : "task" },
    el(
      "button",
      {
        type: "button",
        class: "check",
        "data-action": "toggle",
        "data-id": task.id,
        "aria-label": `Mark "${task.title}" as ${nextState}`,
        title: `Mark as ${nextState}`,
      },
      task.done ? "✓" : ""
    ),
    el("span", { class: "task-title" }, task.title),
    el("span", { class: `badge badge-${task.priority}` }, task.priority),
    el(
      "div",
      { class: "task-actions" },
      el("button", { type: "button", class: "btn btn-ghost", "data-action": "edit", "data-id": task.id }, "Edit"),
      el(
        "button",
        { type: "button", class: "btn btn-ghost btn-danger", "data-action": "delete", "data-id": task.id },
        "Delete"
      )
    )
  );
}

function render() {
  const status = currentStatus();
  const counts = countTasks();
  const tasks = listTasks(status);
  const editing = editingId !== null;

  $("list-view").hidden = editing;
  $("edit-form").hidden = !editing;
  $("progress").hidden = editing;

  const percent = counts.all ? Math.round((100 * counts.done) / counts.all) : 0;
  $("progress-label").textContent = `${counts.done} of ${counts.all} tasks done`;
  $("progress-bar").style.width = `${percent}%`;

  for (const link of document.querySelectorAll(".filter")) {
    const active = link.dataset.status === status;
    link.classList.toggle("is-active", active);
    if (active) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
    link.querySelector(".count").textContent = counts[link.dataset.status];
  }

  $("task-list").replaceChildren(...tasks.map(renderTask));
  $("task-list").hidden = tasks.length === 0;
  $("empty-state").hidden = tasks.length > 0;
  [$("empty-title").textContent, $("empty-text").textContent] = EMPTY_MESSAGES[status];
}

function openEditor(id) {
  const task = getTask(id);
  editingId = id;
  $("edit-title").value = task.title;
  $("edit-priority").value = task.priority;
  showFieldError("edit-error", null);
  clearAlert();
  render();
  $("edit-title").focus();
}

function closeEditor() {
  editingId = null;
  render();
}

// ---------- Event handlers ----------

$("add-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const title = $("title");
  try {
    const task = addTask(title.value, $("priority").value);
    title.value = "";
    title.removeAttribute("aria-invalid");
    showFieldError("add-error", null);
    showAlert(`Task "${task.title}" added.`);
    // A new task is pending, so don't stay on the "done" view.
    if (currentStatus() === "done") {
      location.hash = "all";
    }
  } catch (error) {
    if (!(error instanceof ValidationError)) throw error;
    title.setAttribute("aria-invalid", "true");
    clearAlert();
    showFieldError("add-error", error.message);
  }
  render();
});

$("task-list").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = Number(button.dataset.id);

  if (button.dataset.action === "toggle") {
    toggleDone(id);
    clearAlert();
  } else if (button.dataset.action === "edit") {
    openEditor(id);
    return;
  } else if (button.dataset.action === "delete") {
    const task = getTask(id);
    if (!window.confirm(`Delete "${task.title}"? This cannot be undone.`)) return;
    deleteTask(id);
    showAlert(`Task "${task.title}" deleted.`);
  }
  render();
});

$("edit-form").addEventListener("submit", (event) => {
  event.preventDefault();
  try {
    updateTask(editingId, $("edit-title").value, $("edit-priority").value);
  } catch (error) {
    if (!(error instanceof ValidationError)) throw error;
    showFieldError("edit-error", error.message);
    return;
  }
  showAlert("Task updated.");
  closeEditor();
});

$("edit-cancel").addEventListener("click", closeEditor);

$("reset-demo").addEventListener("click", () => {
  if (!window.confirm("Reset the demo? Your changes will be replaced by the sample tasks.")) return;
  state = sampleState();
  saveState();
  editingId = null;
  showAlert("Demo data reset.");
  render();
});

window.addEventListener("hashchange", () => {
  clearAlert();
  render();
});

// ---------- Start ----------

saveState(); // persist the sample tasks on the first visit
if (recovered) {
  showAlert("Saved demo data was unreadable, so the sample tasks were restored.", "error");
}
render();
