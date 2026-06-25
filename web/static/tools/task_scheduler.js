const API_BASE = "/api/tools/task-scheduler";

let tasks = [];
let selectedId = null;
let logViewId = null;
let refreshTimer = null;
let isNewTask = false;

const $ = (id) => document.getElementById(id);

function showMessage(text, type) {
  const el = $("message");
  el.textContent = text;
  el.className = `message show ${type}`;
}

function hideMessage() {
  $("message").textContent = "";
  $("message").className = "message";
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function statusLabel(status, running) {
  if (running) return { text: "运行中", cls: "running" };
  const map = {
    success: { text: "成功", cls: "success" },
    failed: { text: "失败", cls: "failed" },
    skipped: { text: "已跳过", cls: "skipped" },
    running: { text: "运行中", cls: "running" },
  };
  return map[status] || { text: "未执行", cls: "idle" };
}

function renderTaskList() {
  const list = $("taskList");
  if (!tasks.length) {
    list.innerHTML = '<div class="scheduler-empty">暂无任务，点击「新建任务」</div>';
    return;
  }

  list.innerHTML = tasks
    .map((task) => {
      const st = statusLabel(task.last_status, task.is_running);
      const active = task.id === selectedId ? " active" : "";
      const enabled = task.enabled ? "" : " disabled-task";
      return `
        <button type="button" class="scheduler-task-item${active}${enabled}" data-id="${task.id}">
          <div class="scheduler-task-name">${escapeHtml(task.name)}</div>
          <div class="scheduler-task-meta">
            <span class="scheduler-badge ${st.cls}">${st.text}</span>
            <span>${escapeHtml(task.cron)}</span>
          </div>
          <div class="scheduler-task-meta">${task.next_run_at ? "下次: " + escapeHtml(task.next_run_at) : ""}</div>
        </button>
      `;
    })
    .join("");

  list.querySelectorAll(".scheduler-task-item").forEach((btn) => {
    btn.addEventListener("click", () => selectTask(btn.dataset.id));
  });
}

function renderLogTabs() {
  const tabs = $("logTabs");
  if (!tasks.length) {
    tabs.innerHTML = "";
    return;
  }
  tabs.innerHTML = tasks
    .map((task) => {
      const active = task.id === logViewId ? " active" : "";
      return `<button type="button" class="scheduler-log-tab${active}" data-id="${task.id}">${escapeHtml(task.name)}</button>`;
    })
    .join("");

  tabs.querySelectorAll(".scheduler-log-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      logViewId = btn.dataset.id;
      renderLogTabs();
      loadLogs(logViewId);
    });
  });
}

function updateToggleButton(task) {
  const btn = $("toggleTaskBtn");
  if (!task || isNewTask) {
    btn.textContent = "启用/停用";
    btn.disabled = true;
    return;
  }
  btn.disabled = false;
  btn.textContent = task.enabled ? "停用" : "启用";
}

function fillForm(task) {
  $("taskName").value = task?.name || "";
  $("pythonPath").value = task?.python_path || "";
  $("cronExpr").value = task?.cron || "";
  $("scriptPath").value = task?.script_path || "";
  $("cronDesc").textContent = "";

  const badge = $("taskStatus");
  if (!task) {
    badge.textContent = "";
    badge.className = "scheduler-status-badge";
    $("formTitle").textContent = isNewTask ? "新建任务" : "任务配置";
    updateToggleButton(null);
    return;
  }

  const st = statusLabel(task.last_status, task.is_running);
  badge.textContent = `${task.enabled ? "已启用" : "已停用"} · ${st.text}`;
  badge.className = `scheduler-status-badge ${st.cls}`;
  $("formTitle").textContent = task.name;
  updateToggleButton(task);
}

function clearForm() {
  selectedId = null;
  isNewTask = true;
  fillForm(null);
  $("taskName").focus();
}

async function loadTasks() {
  const res = await fetch(`${API_BASE}/tasks`);
  if (!res.ok) throw new Error("加载任务失败");
  const data = await res.json();
  tasks = data.tasks || [];
  renderTaskList();
  renderLogTabs();

  if (selectedId) {
    const task = tasks.find((t) => t.id === selectedId);
    if (task) fillForm(task);
    else clearForm();
  }
}

async function selectTask(taskId) {
  isNewTask = false;
  selectedId = taskId;
  logViewId = taskId;
  renderTaskList();
  renderLogTabs();

  const res = await fetch(`${API_BASE}/tasks/${taskId}`);
  if (!res.ok) {
    showMessage("加载任务详情失败", "error");
    return;
  }
  const task = await res.json();
  fillForm(task);
  await loadLogs(taskId);
}

async function loadLogs(taskId) {
  if (!taskId) {
    $("logOutput").textContent = "选择任务后查看日志";
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/logs?tail=800`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "加载日志失败");
    $("logOutput").textContent = data.log || "(暂无日志)";
    const el = $("logOutput");
    el.scrollTop = el.scrollHeight;
  } catch (e) {
    $("logOutput").textContent = `加载日志失败: ${e.message}`;
  }
}

async function saveTask() {
  hideMessage();
  const current = tasks.find((t) => t.id === selectedId);
  const payload = {
    name: $("taskName").value.trim(),
    python_path: $("pythonPath").value.trim(),
    cron: $("cronExpr").value.trim(),
    script_path: $("scriptPath").value.trim(),
    enabled: current ? !!current.enabled : true,
  };

  try {
    let res;
    if (isNewTask || !selectedId) {
      res = await fetch(`${API_BASE}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      res = await fetch(`${API_BASE}/tasks/${selectedId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "保存失败");
    isNewTask = false;
    selectedId = data.id;
    logViewId = data.id;
    showMessage("保存成功", "success");
    await loadTasks();
    await selectTask(data.id);
  } catch (e) {
    showMessage(e.message, "error");
  }
}

async function deleteTask() {
  if (!selectedId || isNewTask) {
    showMessage("请先选择要删除的任务", "error");
    return;
  }
  if (!confirm("确定删除该任务？")) return;
  try {
    const res = await fetch(`${API_BASE}/tasks/${selectedId}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "删除失败");
    selectedId = null;
    logViewId = null;
    clearForm();
    showMessage("已删除", "success");
    await loadTasks();
    $("logOutput").textContent = "选择任务后查看日志";
  } catch (e) {
    showMessage(e.message, "error");
  }
}

async function runNow() {
  if (!selectedId || isNewTask) {
    showMessage("请先保存并选择任务", "error");
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/tasks/${selectedId}/run`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "执行失败");
    showMessage(data.message || "已触发执行", data.status === "skipped" ? "error" : "success");
    logViewId = selectedId;
    await loadTasks();
    await loadLogs(selectedId);
  } catch (e) {
    showMessage(e.message, "error");
  }
}

async function toggleTask() {
  if (!selectedId || isNewTask) {
    showMessage("请先选择任务", "error");
    return;
  }
  const task = tasks.find((t) => t.id === selectedId);
  const enabled = !(task && task.enabled);
  try {
    const res = await fetch(`${API_BASE}/tasks/${selectedId}/toggle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "操作失败");
    showMessage(enabled ? "已启用" : "已停用", "success");
    await loadTasks();
    fillForm(data);
    updateToggleButton(data);
  } catch (e) {
    showMessage(e.message, "error");
  }
}

async function validateCron() {
  const cron = $("cronExpr").value.trim();
  if (!cron) {
    showMessage("请输入 Cron 表达式", "error");
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/cron/validate?cron=${encodeURIComponent(cron)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "无效");
    $("cronDesc").textContent = `${data.description}${data.next_run_at ? " · 下次: " + data.next_run_at : ""}`;
    showMessage("Cron 表达式有效", "success");
  } catch (e) {
    $("cronDesc").textContent = "";
    showMessage(e.message, "error");
  }
}

function setupAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  if (!$("autoRefresh").checked) return;
  refreshTimer = setInterval(async () => {
    try {
      await loadTasks();
      if (logViewId) await loadLogs(logViewId);
    } catch (_) { /* ignore */ }
  }, 3000);
}

$("newTaskBtn").addEventListener("click", () => {
  clearForm();
  hideMessage();
});
$("saveTaskBtn").addEventListener("click", saveTask);
$("deleteTaskBtn").addEventListener("click", deleteTask);
$("runNowBtn").addEventListener("click", runNow);
$("toggleTaskBtn").addEventListener("click", toggleTask);
$("refreshBtn").addEventListener("click", async () => {
  await loadTasks();
  if (logViewId) await loadLogs(logViewId);
  showMessage("已刷新", "success");
});
$("validateCronBtn").addEventListener("click", validateCron);
$("autoRefresh").addEventListener("change", setupAutoRefresh);
$("clearLogViewBtn").addEventListener("click", () => {
  $("logOutput").textContent = "";
});

loadTasks()
  .then(() => setupAutoRefresh())
  .catch((e) => showMessage(e.message, "error"));
