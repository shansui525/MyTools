const API = "/api/tools/text-diff/compare";
const EXPORT_API = "/api/tools/text-diff/export";

const textA = document.getElementById("textA");
const textB = document.getElementById("textB");
const resultA = document.getElementById("resultA");
const resultB = document.getElementById("resultB");
const resultSection = document.getElementById("resultSection");
const diffCard = document.getElementById("diffCard");
const toggleInputBtn = document.getElementById("toggleInputBtn");
const exportHtmlBtn = document.getElementById("exportHtmlBtn");
const diffStats = document.getElementById("diffStats");
const diffSummaryPanel = document.getElementById("diffSummaryPanel");
const diffSummaryText = document.getElementById("diffSummaryText");
const diffSummaryList = document.getElementById("diffSummaryList");
const message = document.getElementById("message");

const TYPE_LABELS = { delete: "删除", insert: "新增", replace: "修改" };
const TYPE_CLASS = { delete: "diff-change-delete", insert: "diff-change-insert", replace: "diff-change-replace" };

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

function renderSegments(segments, fallbackText) {
  if (segments && segments.length) {
    return segments.map((seg) => {
      const cls = seg.type === "equal" ? "" : ` diff-char-${seg.type}`;
      return `<span class="diff-char${cls}">${escapeHtml(seg.text)}</span>`;
    }).join("");
  }
  return escapeHtml(fallbackText);
}

function renderLine(line, index, side) {
  const resultRow = index;
  const srcLine = side === "a" ? line.line_a : line.line_b;
  const lineNoDisplay = srcLine != null ? srcLine : "·";
  const typeClass = line.type === "empty" ? "diff-line-empty" : `diff-line-${line.type}`;
  const content = line.type === "empty"
    ? "&nbsp;"
    : renderSegments(line.segments, line.text);
  return `<div class="diff-line ${typeClass}" data-result-row="${resultRow}">
    <span class="diff-lineno">${lineNoDisplay}</span>
    <span class="diff-content">${content || "&nbsp;"}</span>
  </div>`;
}

function formatChangePos(change) {
  const parts = [];
  if (change.line_a != null) parts.push(`A:${change.line_a}`);
  if (change.line_b != null) parts.push(`B:${change.line_b}`);
  return parts.join(" ↔ ") || `#${change.result_row + 1}`;
}

function formatChangePreview(change) {
  if (change.type === "delete") return change.preview_a || "(空行)";
  if (change.type === "insert") return change.preview_b || "(空行)";
  if (change.preview_a && change.preview_b && change.preview_a !== change.preview_b) {
    return `${change.preview_a} → ${change.preview_b}`;
  }
  return change.preview_a || change.preview_b || "(空行)";
}

function renderDiffSummary(data) {
  const changes = data.changes || [];
  if (!changes.length) {
    diffSummaryPanel.classList.add("hidden");
    diffSummaryList.innerHTML = "";
    return;
  }

  const s = data.stats;
  diffSummaryPanel.classList.remove("hidden");
  diffSummaryText.textContent =
    `共 ${changes.length} 处差异（删除 ${s.deleted} 行、新增 ${s.inserted} 行、修改 ${s.replaced} 行），点击行号可跳转查看`;

  diffSummaryList.innerHTML = changes
    .map((change) => {
      const typeLabel = TYPE_LABELS[change.type] || change.type;
      const typeClass = TYPE_CLASS[change.type] || "";
      return `<li class="diff-summary-item ${typeClass}">
        <span class="diff-summary-type">${typeLabel}</span>
        <button type="button" class="diff-summary-pos" data-row="${change.result_row}" title="跳转到差异行">
          ${formatChangePos(change)}
        </button>
        <span class="diff-summary-preview">${escapeHtml(formatChangePreview(change))}</span>
      </li>`;
    })
    .join("");
}

function scrollRowIntoView(container, row) {
  const lineEl = container.querySelector(`.diff-line[data-result-row="${row}"]`);
  if (!lineEl) return null;
  const lineRect = lineEl.getBoundingClientRect();
  const containerRect = container.getBoundingClientRect();
  const offset = lineRect.top - containerRect.top + container.scrollTop;
  container.scrollTop = Math.max(0, offset - container.clientHeight / 2 + lineEl.clientHeight / 2);
  return lineEl;
}

function jumpToDiffRow(row) {
  scrollRowIntoView(resultA, row);
  scrollRowIntoView(resultB, row);

  [resultA, resultB].forEach((panel) => {
    panel.querySelectorAll(".diff-line-active").forEach((el) => el.classList.remove("diff-line-active"));
    const el = panel.querySelector(`.diff-line[data-result-row="${row}"]`);
    if (el) el.classList.add("diff-line-active");
  });

  diffSummaryList.querySelectorAll(".diff-summary-pos.active").forEach((btn) => btn.classList.remove("active"));
  const activeBtn = diffSummaryList.querySelector(`.diff-summary-pos[data-row="${row}"]`);
  if (activeBtn) {
    activeBtn.classList.add("active");
    activeBtn.scrollIntoView({ block: "nearest" });
  }
}

function renderResult(data) {
  resultA.innerHTML = data.left.map((line, i) => renderLine(line, i, "a")).join("");
  resultB.innerHTML = data.right.map((line, i) => renderLine(line, i, "b")).join("");
  resultSection.classList.remove("hidden");
  diffCard.classList.add("has-result");
  diffCard.classList.remove("inputs-collapsed");
  toggleInputBtn.classList.remove("hidden");
  exportHtmlBtn.classList.remove("hidden");
  toggleInputBtn.textContent = "收起输入";

  const s = data.stats;
  diffStats.textContent = `共 ${data.total_lines} 行 · 相同 ${s.equal} · 差异 ${data.change_count || 0} 处`;
  renderDiffSummary(data);
}

function syncScroll(source, target) {
  target.scrollTop = source.scrollTop;
}

let scrollBound = false;
function bindScrollSync() {
  if (scrollBound) return;
  scrollBound = true;
  resultA.addEventListener("scroll", () => syncScroll(resultA, resultB));
  resultB.addEventListener("scroll", () => syncScroll(resultB, resultA));
}

async function compare() {
  hideMessage();
  try {
    const res = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text_a: textA.value, text_b: textB.value }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "对比失败");
    renderResult(data);
    bindScrollSync();
    if (data.has_diff) {
      showMessage(`对比完成，发现 ${data.change_count} 处差异`, "info");
    } else {
      showMessage("对比完成，两段文本完全一致", "success");
    }
  } catch (e) {
    showMessage(e.message, "error");
  }
}

document.getElementById("compareBtn").addEventListener("click", compare);

diffSummaryList.addEventListener("click", (e) => {
  const btn = e.target.closest(".diff-summary-pos");
  if (!btn) return;
  jumpToDiffRow(parseInt(btn.dataset.row, 10));
});

document.getElementById("clearBtn").addEventListener("click", () => {
  textA.value = "";
  textB.value = "";
  resultA.innerHTML = "";
  resultB.innerHTML = "";
  resultSection.classList.add("hidden");
  diffSummaryPanel.classList.add("hidden");
  diffSummaryList.innerHTML = "";
  diffCard.classList.remove("has-result", "inputs-collapsed");
  toggleInputBtn.classList.add("hidden");
  exportHtmlBtn.classList.add("hidden");
  diffStats.textContent = "";
  hideMessage();
});

toggleInputBtn.addEventListener("click", () => {
  const collapsed = diffCard.classList.toggle("inputs-collapsed");
  toggleInputBtn.textContent = collapsed ? "展开输入" : "收起输入";
});

exportHtmlBtn.addEventListener("click", async () => {
  hideMessage();
  try {
    const res = await fetch(EXPORT_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text_a: textA.value, text_b: textB.value }),
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "导出失败");
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/);
    const filename = match ? match[1] : "text_diff.html";
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    showMessage("HTML 已导出", "success");
  } catch (e) {
    showMessage(e.message, "error");
  }
});

document.getElementById("swapBtn").addEventListener("click", () => {
  const tmp = textA.value;
  textA.value = textB.value;
  textB.value = tmp;
});

function loadFile(input, target) {
  input.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => { target.value = reader.result; };
    reader.readAsText(file, "UTF-8");
    e.target.value = "";
  });
}

loadFile(document.getElementById("fileA"), textA);
loadFile(document.getElementById("fileB"), textB);
