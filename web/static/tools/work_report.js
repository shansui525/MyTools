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
const reportMeta = document.getElementById("reportMeta");
const savedReportList = document.getElementById("savedReportList");
const message = document.getElementById("message");

let entryDates = new Set();
let viewYear = new Date().getFullYear();
let viewMonth = new Date().getMonth();
let currentReport = null;
let savedReportsCache = [];

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];
const PERIOD_LABELS = { week: "周报", month: "月报", quarter: "季报", year: "年报" };

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
  if (name === "report") {
    updateReportRangeInfo();
    loadSavedReports();
  }
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

function updateReportMeta() {
  if (!currentReport?.id) {
    reportMeta.textContent = currentReport?.content
      ? "当前为未保存的生成内容，编辑后请点击「保存报告」"
      : "";
    return;
  }
  reportMeta.textContent = `已保存 · 最后更新：${currentReport.updated_at || "—"}`;
}

function setCurrentReport(report) {
  currentReport = report
    ? {
        id: report.id || null,
        period: report.period,
        reference_date: report.reference_date,
        title: report.title,
        start_date: report.start_date,
        end_date: report.end_date,
        entry_count: report.entry_count ?? 0,
        content: report.content || "",
        updated_at: report.updated_at || "",
      }
    : null;

  if (currentReport) {
    reportPeriod.value = currentReport.period;
    reportDate.value = currentReport.reference_date;
    reportOutput.value = currentReport.content;
    reportRangeInfo.textContent = `${currentReport.title} · ${currentReport.start_date} 至 ${currentReport.end_date}`;
  }
  updateReportMeta();
  renderSavedReportList();
}

function renderSavedReportList() {
  if (!savedReportsCache.length) {
    savedReportList.innerHTML = '<li class="wr-empty">暂无已保存报告</li>';
    return;
  }

  savedReportList.innerHTML = "";
  savedReportsCache.forEach((item) => {
    const li = document.createElement("li");
    li.className = "wr-saved-report-item";
    const active = currentReport?.id === item.id;
    li.innerHTML = `
      <button type="button" class="wr-saved-report-btn${active ? " active" : ""}" data-id="${item.id}">
        <span class="wr-saved-report-title">${escapeHtml(item.title)}</span>
        <span class="wr-saved-report-meta">${PERIOD_LABELS[item.period] || item.period} · ${item.updated_at || ""}</span>
      </button>`;
    li.querySelector(".wr-saved-report-btn").addEventListener("click", () => {
      openSavedReport(item.id).catch((e) => showMessage(e.message, "error"));
    });
    savedReportList.appendChild(li);
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
    if (!currentReport || currentReport.reference_date !== reportDate.value || currentReport.period !== reportPeriod.value) {
      reportRangeInfo.textContent = `${data.title} · ${data.start_date} 至 ${data.end_date} · 共 ${data.entry_count} 天有记录`;
    }
    return data;
  } catch (err) {
    reportRangeInfo.textContent = err.message;
    return null;
  }
}

async function loadSavedReports() {
  const data = await api("/reports");
  savedReportsCache = data.reports || [];
  renderSavedReportList();
}

async function openSavedReport(reportId) {
  const data = await api(`/reports/${reportId}`);
  setCurrentReport(data.report);
  showMessage("已加载保存的报告", "success");
}

async function generateReport() {
  hideMessage();
  generateBtn.disabled = true;
  reportOutput.value = "正在生成报告，请稍候…";
  reportOutput.disabled = true;
  try {
    const data = await api("/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        period: reportPeriod.value,
        reference_date: reportDate.value,
      }),
    });
    setCurrentReport({
      id: null,
      period: data.period,
      reference_date: reportDate.value,
      title: data.title,
      start_date: data.start_date,
      end_date: data.end_date,
      entry_count: data.entry_count,
      content: data.report,
    });
    reportRangeInfo.textContent = `${data.title} · ${data.start_date} 至 ${data.end_date} · 共 ${data.entry_count} 天有记录`;
    showMessage("报告已生成，可编辑后保存", "success");
  } catch (err) {
    reportOutput.value = "";
    setCurrentReport(null);
    showMessage(err.message, "error");
  } finally {
    reportOutput.disabled = false;
    generateBtn.disabled = false;
  }
}

async function saveReport() {
  hideMessage();
  const content = reportOutput.value.trim();
  if (!content) {
    showMessage("报告内容为空，无法保存", "error");
    return;
  }

  const range = await updateReportRangeInfo();
  if (!range) return;

  saveReportBtn.disabled = true;
  try {
    const payload = {
      period: reportPeriod.value,
      reference_date: reportDate.value,
      title: range.title,
      start_date: range.start_date,
      end_date: range.end_date,
      content,
      entry_count: range.entry_count,
      report_id: currentReport?.id || null,
    };

    const data = currentReport?.id
      ? await api(`/reports/${currentReport.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content, title: range.title }),
        })
      : await api("/reports", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

    setCurrentReport(data.report);
    await loadSavedReports();
    showMessage("报告已保存", "success");
  } catch (err) {
    showMessage(err.message, "error");
  } finally {
    saveReportBtn.disabled = false;
  }
}

async function deleteSavedReport() {
  if (!currentReport?.id) {
    showMessage("当前报告尚未保存", "error");
    return;
  }
  if (!confirm(`确定删除已保存报告「${currentReport.title}」？`)) return;

  await api(`/reports/${currentReport.id}`, { method: "DELETE" });
  reportOutput.value = "";
  setCurrentReport(null);
  reportRangeInfo.textContent = "选择报告类型与参考日期";
  await loadSavedReports();
  showMessage("已删除保存的报告", "success");
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
const saveReportBtn = document.getElementById("saveReportBtn");
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
document.getElementById("saveReportBtn").addEventListener("click", () => saveReport().catch((e) => showMessage(e.message, "error")));
document.getElementById("deleteReportBtn").addEventListener("click", () => deleteSavedReport().catch((e) => showMessage(e.message, "error")));
document.getElementById("copyReportBtn").addEventListener("click", async () => {
  const text = reportOutput.value.trim();
  if (!text) {
    showMessage("暂无报告可复制", "error");
    return;
  }
  await navigator.clipboard.writeText(text);
  showMessage("已复制到剪贴板", "success");
});
document.getElementById("saveSettingsBtn").addEventListener("click", () => saveSettings().catch((e) => showMessage(e.message, "error")));
document.getElementById("testSettingsBtn").addEventListener("click", () => testSettings());

reportPeriod.addEventListener("change", () => {
  if (currentReport?.id && currentReport.period === reportPeriod.value && currentReport.reference_date === reportDate.value) {
    return;
  }
  if (currentReport?.id) {
    currentReport.id = null;
    updateReportMeta();
  }
  updateReportRangeInfo();
});
reportDate.addEventListener("change", () => {
  if (currentReport?.id && currentReport.period === reportPeriod.value && currentReport.reference_date === reportDate.value) {
    return;
  }
  if (currentReport?.id) {
    currentReport.id = null;
    updateReportMeta();
  }
  updateReportRangeInfo();
});
entryDate.addEventListener("change", () => selectDate(entryDate.value));

entryDate.value = todayStr();
reportDate.value = todayStr();
loadEntryDates();
loadRecentEntries();
loadEntry(todayStr());
loadSettings();
renderMiniCalendar();
