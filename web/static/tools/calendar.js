const API_BASE = "/api/tools/calendar";
const WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"];
const EXPORT_WIDTH_PX = 1120;

const yearInput = document.getElementById("yearInput");
const calendarGrid = document.getElementById("calendarGrid");
const calendarYearTitle = document.getElementById("calendarYearTitle");
const calendarExportArea = document.getElementById("calendarExportArea");
const message = document.getElementById("message");
const eventModal = document.getElementById("eventModal");
const modalDateTitle = document.getElementById("modalDateTitle");
const modalHoliday = document.getElementById("modalHoliday");
const modalEventsInput = document.getElementById("modalEventsInput");

let calendarData = null;
let editingDate = null;

function showMessage(text, type) {
  message.textContent = text;
  message.className = `message show ${type}`;
}

function hideMessage() {
  message.textContent = "";
  message.className = "message";
}

function getYear() {
  return parseInt(yearInput.value, 10) || new Date().getFullYear();
}

function setYear(y) {
  yearInput.value = Math.min(2100, Math.max(1970, y));
}

function updateYearTitle(year) {
  calendarYearTitle.textContent = `${year}年日历`;
}

async function loadCalendar() {
  const year = getYear();
  updateYearTitle(year);
  calendarGrid.innerHTML = '<div class="calendar-loading">加载中...</div>';
  try {
    const res = await fetch(`${API_BASE}/data?year=${year}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "加载失败");
    calendarData = data;
    updateYearTitle(data.year);
    if (data.lunar_enabled === false) {
      showMessage("农历不可用：请在后端环境安装 zhdate（pip install zhdate）并重启服务", "error");
    } else {
      hideMessage();
    }
    renderCalendar(data);
  } catch (e) {
    calendarGrid.innerHTML = `<div class="calendar-loading">${escapeHtml(e.message)}</div>`;
  }
}

function renderCalendar(data) {
  calendarGrid.innerHTML = "";
  data.months.forEach((month) => {
    calendarGrid.appendChild(buildMonthEl(month, data.holidays));
  });
}

function fitLabelText(text, dual) {
  const maxLen = dual ? 6 : 8;
  if (text.length <= maxLen) return text;
  return `${text.slice(0, maxLen)}…`;
}

function appendDayLabels(cell, holiday, events) {
  const lines = [];
  if (holiday) lines.push({ text: holiday, type: "holiday" });
  if (events.length) {
    if (holiday) {
      lines.push({ text: events[0], type: "event" });
    } else if (events.length >= 2) {
      lines.push({ text: events[0], type: "event" });
      lines.push({ text: events[1], type: "event" });
    } else {
      lines.push({ text: events[0], type: "event" });
    }
  }

  const displayLines = lines.slice(0, 2);
  if (!displayLines.length) return;

  const dual = displayLines.length >= 2;
  if (dual) cell.classList.add("has-dual-labels");

  const wrap = document.createElement("div");
  wrap.className = "day-labels";

  displayLines.forEach((line) => {
    const span = document.createElement("span");
    span.className = `day-label day-label-${line.type}`;
    const displayText = fitLabelText(line.text, dual);
    span.textContent = displayText;
    span.title = line.type === "holiday" ? line.text : events.join("\n");
    const compactThreshold = dual ? 5 : 7;
    if (line.text.length > compactThreshold) {
      span.classList.add("day-label-compact");
    }
    wrap.appendChild(span);
  });

  cell.appendChild(wrap);

  const extraCount = (holiday ? events.length : Math.max(0, events.length - 2));
  if (extraCount > 0) {
    const dot = document.createElement("i");
    dot.className = "day-more-dot";
    dot.title = `还有 ${extraCount} 条事件`;
    cell.appendChild(dot);
  }
}

function buildMonthEl(month, holidays) {
  const wrap = document.createElement("div");
  wrap.className = "calendar-month";

  const title = document.createElement("div");
  title.className = "calendar-month-title";
  title.textContent = month.name;
  wrap.appendChild(title);

  const weekdays = document.createElement("div");
  weekdays.className = "calendar-weekdays";
  WEEKDAYS.forEach((wd, i) => {
    const cell = document.createElement("div");
    cell.className = "calendar-weekday" + (i === 0 || i === 6 ? " weekend" : "");
    cell.textContent = wd;
    weekdays.appendChild(cell);
  });
  wrap.appendChild(weekdays);

  const days = document.createElement("div");
  days.className = "calendar-days";

  month.weeks.forEach((week) => {
    week.forEach((day, di) => {
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "calendar-day";
      if (day === 0) {
        cell.classList.add("empty");
        cell.disabled = true;
      } else {
        const fullDate = `${calendarData.year}-${String(month.month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
        const holiday = holidays[fullDate];
        const events = calendarData.events[fullDate] || [];
        const lunar = (calendarData.lunar && calendarData.lunar[fullDate]) || "";

        cell.dataset.date = fullDate;
        if (di === 0 || di === 6) cell.classList.add("weekend");
        if (holiday) cell.classList.add("holiday");
        if (events.length) cell.classList.add("has-event");

        const num = document.createElement("span");
        num.className = "day-num";
        num.textContent = day;
        cell.appendChild(num);

        if (lunar) {
          const lunarEl = document.createElement("span");
          lunarEl.className = "day-lunar";
          lunarEl.textContent = lunar;
          cell.appendChild(lunarEl);
        }

        appendDayLabels(cell, holiday, events);

        cell.addEventListener("click", () => openEventModal(fullDate, holiday, events));
      }
      days.appendChild(cell);
    });
  });

  wrap.appendChild(days);
  return wrap;
}

function openEventModal(dateKey, holiday, events) {
  editingDate = dateKey;
  modalDateTitle.textContent = dateKey;
  if (holiday) {
    modalHoliday.textContent = `节日：${holiday}`;
    modalHoliday.classList.remove("hidden");
  } else {
    modalHoliday.classList.add("hidden");
  }
  modalEventsInput.value = (events || []).join("\n");
  eventModal.classList.remove("hidden");
  modalEventsInput.focus();
}

function closeEventModal() {
  eventModal.classList.add("hidden");
  editingDate = null;
}

async function saveEvents() {
  if (!editingDate) return;
  const events = modalEventsInput.value
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);

  try {
    const res = await fetch(`${API_BASE}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        year: getYear(),
        date: editingDate,
        events,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "保存失败");
    calendarData = data;
    updateYearTitle(data.year);
    renderCalendar(data);
    closeEventModal();
    showMessage("事件已保存", "success");
  } catch (e) {
    showMessage(e.message, "error");
  }
}

async function captureExportCanvas() {
  if (typeof html2canvas === "undefined") {
    throw new Error("html2canvas 未加载，请刷新页面重试");
  }

  calendarExportArea.classList.add("is-capturing");
  const prevWidth = calendarExportArea.style.width;
  calendarExportArea.style.width = `${EXPORT_WIDTH_PX}px`;

  try {
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    return await html2canvas(calendarExportArea, {
      scale: 2,
      backgroundColor: "#ffffff",
      useCORS: true,
      logging: false,
      onclone: (doc) => {
        const cloned = doc.getElementById("calendarExportArea");
        if (cloned) {
          cloned.style.width = `${EXPORT_WIDTH_PX}px`;
          cloned.style.border = "none";
          cloned.style.padding = "10px 8px 8px";
        }
      },
    });
  } finally {
    calendarExportArea.style.width = prevWidth;
    calendarExportArea.classList.remove("is-capturing");
  }
}

function downloadDataUrl(dataUrl, filename) {
  const link = document.createElement("a");
  link.href = dataUrl;
  link.download = filename;
  link.click();
}

async function exportImage() {
  hideMessage();
  showMessage("正在生成图片…", "success");
  try {
    const canvas = await captureExportCanvas();
    downloadDataUrl(canvas.toDataURL("image/png"), `calendar_${getYear()}.png`);
    showMessage("图片已下载", "success");
  } catch (e) {
    showMessage(e.message || "导出图片失败", "error");
  }
}

function getJsPDFConstructor() {
  if (window.jspdf && window.jspdf.jsPDF) return window.jspdf.jsPDF;
  if (typeof window.jsPDF === "function") return window.jsPDF;
  if (window.jsPDF && window.jsPDF.jsPDF) return window.jsPDF.jsPDF;
  return null;
}

async function exportPdf() {
  hideMessage();
  const JsPDF = getJsPDFConstructor();
  if (!JsPDF) {
    showMessage("正在使用服务端导出 PDF…", "success");
    window.open(`${API_BASE}/pdf?year=${getYear()}`, "_blank");
    return;
  }

  showMessage("正在生成 PDF…", "success");
  try {
    const canvas = await captureExportCanvas();
    const imgData = canvas.toDataURL("image/png");
    const margin = 8;
    const pageW = 297;
    const contentW = pageW - margin * 2;
    const contentH = (canvas.height / canvas.width) * contentW;
    const pageH = contentH + margin * 2;
    const pdf = new JsPDF({
      orientation: pageW >= pageH ? "landscape" : "portrait",
      unit: "mm",
      format: [pageW, pageH],
    });
    pdf.addImage(imgData, "PNG", margin, margin, contentW, contentH);
    pdf.save(`calendar_${getYear()}.pdf`);
    showMessage("PDF 已下载", "success");
  } catch (e) {
    showMessage(e.message || "导出 PDF 失败", "error");
  }
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

document.getElementById("prevYearBtn").addEventListener("click", () => {
  setYear(getYear() - 1);
  hideMessage();
  loadCalendar();
});

document.getElementById("nextYearBtn").addEventListener("click", () => {
  setYear(getYear() + 1);
  hideMessage();
  loadCalendar();
});

yearInput.addEventListener("change", () => {
  hideMessage();
  loadCalendar();
});

document.getElementById("exportImageBtn").addEventListener("click", exportImage);
document.getElementById("exportPdfBtn").addEventListener("click", exportPdf);
document.getElementById("modalCloseBtn").addEventListener("click", closeEventModal);
document.getElementById("modalBackdrop").addEventListener("click", closeEventModal);
document.getElementById("modalClearBtn").addEventListener("click", () => {
  modalEventsInput.value = "";
});
document.getElementById("modalSaveBtn").addEventListener("click", saveEvents);

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeEventModal();
});

loadCalendar();
