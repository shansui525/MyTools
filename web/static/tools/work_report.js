const API = "/api/tools/work-report";

const entryDate = document.getElementById("entryDate");
const entryContent = document.getElementById("entryContent");
const entryMeta = document.getElementById("entryMeta");
const monthLabel = document.getElementById("monthLabel");
const miniCalendar = document.getElementById("miniCalendar");
const recentList = document.getElementById("recentList");
const reportPeriod = document.getElementById("reportPeriod");
const reportDate = document.getElementById("reportDate");
const reportRangeInfo = document.getElementById("reportRangeInfo");
const reportOutput = document.getElementById("reportOutput");
const message = document.getElementById("message");

let entryDates = new Set();
let viewYear = new Date().getFullYear();
let viewMonth = new Date().getMonth();
let lastReport = "";

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

function showMessage(text, type) {
  message.textContent = text;
  message.className = `message show ${type}`;
}

function hideMessage() {
  message.textContent = "";
  message.className = "message";
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function api(path, options = {}) {
  const res = await fetch(API + path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "请求失败");
  return data;
}

function switchTab(name) {
  document.querySelectorAll(".wr-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === name);
  });
  document.getElementById("tabEntry").classList.toggle("hidden", name !== "entry");
  document.getElementById("tabReport").classList.toggle("hidden", name !== "report");
  document.getElementById("tabSettings").classList.toggle("hidden", name !== "settings");
  if (name === "report") updateReportRangeInfo();
}

function renderMiniCalendar() {
  monthLabel.textContent = `${viewYear} 年 ${viewMonth + 1} 月`;
  const firstDay = new Date(viewYear, viewMonth, 1);
  const startWeekday = (firstDay.getDay() + 6) % 7;
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const selected = entryDate.value;

  let html = '<div class="wr-cal-head">';
  WEEKDAYS.forEach((d) => {
    html += `<span>${d}</span>`;
  });
  html += '</div><div class="wr-cal-grid">';

  for (let i = 0; i < startWeekday; i += 1) {
    html += '<span class="wr-cal-cell empty"></span>';
  }
  for (let day = 1; day <= daysInMonth; day += 1) {
    const ds = `${viewYear}-${String(viewMonth + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const classes = ["wr-cal-cell", "day"];
    if (ds === selected) classes.push("selected");
    if (ds === todayStr()) classes.push("today");
    if (entryDates.has(ds)) classes.push("has-entry");
    html += `<button type="button" class="${classes.join(" ")}" data-date="${ds}">${day}</button>`;
  }
  html += "</div>";
  miniCalendar.innerHTML = html;

  miniCalendar.querySelectorAll(".wr-cal-cell.day").forEach((btn) => {
    btn.addEventListener("click", () => selectDate(btn.dataset.date));
  });
}

function renderRecentList(entries) {
  if (!entries.length) {
    recentList.innerHTML = '<li class="wr-empty">暂无记录</li>';
    return;
  }
  recentList.innerHTML = "";
  entries.slice(0, 12).forEach((item) => {
    const li = document.createElement("li");
    li.className = "wr-recent-item";
    const preview = item.content.replace(/\s+/g, " ").slice(0, 36);
    li.innerHTML = `
      <button type="button" class="wr-recent-btn" data-date="${item.date}">
        <span class="wr-recent-date">${item.date}</span>
        <span class="wr-recent-preview">${escapeHtml(preview)}${item.content.length > 36 ? "…" : ""}</span>
      </button>`;
    li.querySelector(".wr-recent-btn").addEventListener("click", () => selectDate(item.date));
    recentList.appendChild(li);
  });
}

async function loadEntryDates() {
  const data = await api("/entries/dates");
  entryDates = new Set(data.dates || []);
  renderMiniCalendar();
}

async function loadRecentEntries() {
  const data = await api("/entries");
  renderRecentList(data.entries || []);
}

async function loadEntry(dateStr) {
  const data = await api(`/entries/${dateStr}`);
  if (data.entry) {
    entryContent.value = data.entry.content;
    entryMeta.textContent = data.entry.updated_at ? `最后保存：${data.entry.updated_at}` : "";
  } else {
    entryContent.value = "";
    entryMeta.textContent = "该日期尚无记录";
  }
}

function selectDate(dateStr) {
  entryDate.value = dateStr;
  const d = new Date(dateStr);
  viewYear = d.getFullYear();
  viewMonth = d.getMonth();
  renderMiniCalendar();
  loadEntry(dateStr);
}

async function saveEntry() {
  hideMessage();
  const content = entryContent.value.trim();
  if (!content) {
    showMessage("请填写工作内容", "error");
    return;
  }
  const data = await api(`/entries/${entryDate.value}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  entryMeta.textContent = `最后保存：${data.entry.updated_at}`;
  await loadEntryDates();
  await loadRecentEntries();
  showMessage("已保存", "success");
}

async function deleteEntry() {
  if (!confirm(`确定删除 ${entryDate.value} 的工作记录？`)) return;
  await api(`/entries/${entryDate.value}`, { method: "DELETE" });
  entryContent.value = "";
  entryMeta.textContent = "";
  await loadEntryDates();
  await loadRecentEntries();
  showMessage("已删除", "success");
}

async function updateReportRangeInfo() {
  try {
    const q = `?period=${reportPeriod.value}&reference_date=${reportDate.value}`;
    const data = await api(`/period-range${q}`);
    reportRangeInfo.textContent = `${data.title} · ${data.start_date} 至 ${data.end_date} · 共 ${data.entry_count} 天有记录`;
  } catch (err) {
    reportRangeInfo.textContent = err.message;
  }
}

async function generateReport() {
  hideMessage();
  generateBtn.disabled = true;
  reportOutput.textContent = "正在生成报告，请稍候…";
  try {
    const data = await api("/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        period: reportPeriod.value,
        reference_date: reportDate.value,
      }),
    });
    lastReport = data.report;
    reportOutput.textContent = data.report;
    reportRangeInfo.textContent = `${data.title} · ${data.start_date} 至 ${data.end_date} · 共 ${data.entry_count} 天有记录`;
    showMessage("报告已生成", "success");
  } catch (err) {
    reportOutput.textContent = "生成失败";
    showMessage(err.message, "error");
  } finally {
    generateBtn.disabled = false;
  }
}

async function loadSettings() {
  const data = await api("/settings");
  llmApiBase.value = data.llm_api_base || "";
  llmModel.value = data.llm_model || "";
  llmApiKey.value = "";
  llmApiKey.placeholder = data.llm_api_key_set ? data.llm_api_key_masked : "sk-...";
  keyHint.textContent = data.llm_api_key_set
    ? `已配置密钥 ${data.llm_api_key_masked}，留空则保持不变`
    : "也可通过环境变量 MYTOOLS_LLM_API_KEY 配置";
}

async function saveSettings() {
  hideMessage();
  const body = {
    llm_api_base: llmApiBase.value.trim(),
    llm_model: llmModel.value.trim(),
    llm_api_key: llmApiKey.value.trim() || null,
  };
  const data = await api("/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  llmApiKey.value = "";
  llmApiKey.placeholder = data.llm_api_key_set ? data.llm_api_key_masked : "sk-...";
  showMessage("设置已保存", "success");
}

async function testSettings() {
  hideMessage();
  testSettingsBtn.disabled = true;
  try {
    const data = await api("/settings/test", { method: "POST" });
    showMessage(`连接成功：${data.message}`, "success");
  } catch (err) {
    showMessage(err.message, "error");
  } finally {
    testSettingsBtn.disabled = false;
  }
}

const generateBtn = document.getElementById("generateBtn");
const testSettingsBtn = document.getElementById("testSettingsBtn");
const llmApiBase = document.getElementById("llmApiBase");
const llmApiKey = document.getElementById("llmApiKey");
const llmModel = document.getElementById("llmModel");
const keyHint = document.getElementById("keyHint");

document.querySelectorAll(".wr-tab").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

document.getElementById("prevMonthBtn").addEventListener("click", () => {
  viewMonth -= 1;
  if (viewMonth < 0) {
    viewMonth = 11;
    viewYear -= 1;
  }
  renderMiniCalendar();
});

document.getElementById("nextMonthBtn").addEventListener("click", () => {
  viewMonth += 1;
  if (viewMonth > 11) {
    viewMonth = 0;
    viewYear += 1;
  }
  renderMiniCalendar();
});

document.getElementById("todayBtn").addEventListener("click", () => selectDate(todayStr()));
document.getElementById("saveEntryBtn").addEventListener("click", () => saveEntry().catch((e) => showMessage(e.message, "error")));
document.getElementById("deleteEntryBtn").addEventListener("click", () => deleteEntry().catch((e) => showMessage(e.message, "error")));
document.getElementById("generateBtn").addEventListener("click", () => generateReport());
document.getElementById("copyReportBtn").addEventListener("click", async () => {
  if (!lastReport) {
    showMessage("暂无报告可复制", "error");
    return;
  }
  await navigator.clipboard.writeText(lastReport);
  showMessage("已复制到剪贴板", "success");
});
document.getElementById("saveSettingsBtn").addEventListener("click", () => saveSettings().catch((e) => showMessage(e.message, "error")));
document.getElementById("testSettingsBtn").addEventListener("click", () => testSettings());

reportPeriod.addEventListener("change", updateReportRangeInfo);
reportDate.addEventListener("change", updateReportRangeInfo);
entryDate.addEventListener("change", () => selectDate(entryDate.value));

entryDate.value = todayStr();
reportDate.value = todayStr();
loadEntryDates();
loadRecentEntries();
loadEntry(todayStr());
loadSettings();
renderMiniCalendar();
