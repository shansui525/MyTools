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
const message = document.getElementById("message");

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

function renderSegments(segments, fallbackText, fallbackType) {
  if (segments && segments.length) {
    return segments.map((seg) => {
      const cls = seg.type === "equal" ? "" : ` diff-char-${seg.type}`;
      return `<span class="diff-char${cls}">${escapeHtml(seg.text)}</span>`;
    }).join("");
  }
  return escapeHtml(fallbackText);
}

function renderLine(line, index) {
  const lineNo = index + 1;
  const typeClass = line.type === "empty" ? "diff-line-empty" : `diff-line-${line.type}`;
  const content = line.type === "empty"
    ? "&nbsp;"
    : renderSegments(line.segments, line.text, line.type);
  return `<div class="diff-line ${typeClass}"><span class="diff-lineno">${lineNo}</span><span class="diff-content">${content || "&nbsp;"}</span></div>`;
}

function renderResult(data) {
  resultA.innerHTML = data.left.map(renderLine).join("");
  resultB.innerHTML = data.right.map(renderLine).join("");
  resultSection.classList.remove("hidden");
  diffCard.classList.add("has-result");
  diffCard.classList.remove("inputs-collapsed");
  toggleInputBtn.classList.remove("hidden");
  exportHtmlBtn.classList.remove("hidden");
  toggleInputBtn.textContent = "收起输入";

  const s = data.stats;
  diffStats.textContent = `共 ${data.total_lines} 行 · 相同 ${s.equal} · 删除 ${s.deleted} · 新增 ${s.inserted} · 修改 ${s.replaced}`;
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
    showMessage("对比完成", "success");
  } catch (e) {
    showMessage(e.message, "error");
  }
}

document.getElementById("compareBtn").addEventListener("click", compare);

document.getElementById("clearBtn").addEventListener("click", () => {
  textA.value = "";
  textB.value = "";
  resultA.innerHTML = "";
  resultB.innerHTML = "";
  resultSection.classList.add("hidden");
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
