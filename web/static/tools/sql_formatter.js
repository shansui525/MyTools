const API = "/api/tools/sql-formatter/process";

const inputText = document.getElementById("inputText");
const outputCode = document.getElementById("outputCode");
const message = document.getElementById("message");

let outputRawText = "";

const SEGMENT_CLASS = {
  keyword: "sql-kw",
  table: "sql-table",
  identifier: "sql-id",
  string: "sql-str",
  number: "sql-num",
  operator: "sql-op",
  punctuation: "sql-punc",
  comment: "sql-comment",
  whitespace: "",
  text: "",
};

function showMessage(text, type) {
  message.textContent = text;
  message.className = `message show ${type}`;
}

function hideMessage() {
  message.textContent = "";
  message.className = "message";
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function clearOutput() {
  outputRawText = "";
  outputCode.innerHTML = '<span class="sql-output-empty">格式化结果将显示在这里</span>';
}

function renderHighlighted(segments) {
  if (!segments || !segments.length) {
    clearOutput();
    return;
  }

  const html = segments
    .map(({ type, value }) => {
      const cls = SEGMENT_CLASS[type];
      const escaped = escapeHtml(value);
      if (!cls) return escaped;
      return `<span class="${cls}">${escaped}</span>`;
    })
    .join("");

  outputCode.innerHTML = html;
}

async function formatSql() {
  hideMessage();
  const text = inputText.value;
  if (!text.trim()) {
    showMessage("请输入 SQL 内容", "error");
    return;
  }

  const body = {
    text,
    indent: parseInt(document.getElementById("indentSelect").value, 10),
    keyword_case: document.getElementById("keywordCaseSelect").value,
  };

  try {
    const res = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) {
      const detail = data.detail;
      throw new Error(typeof detail === "string" ? detail : "处理失败");
    }

    outputRawText = data.result;
    renderHighlighted(data.segments);
    showMessage("格式化完成", "success");
  } catch (e) {
    clearOutput();
    showMessage(e.message, "error");
  }
}

document.getElementById("formatBtn").addEventListener("click", formatSql);

document.getElementById("clearInputBtn").addEventListener("click", () => {
  inputText.value = "";
  clearOutput();
  hideMessage();
  inputText.focus();
});

document.getElementById("copyOutputBtn").addEventListener("click", () => {
  if (!outputRawText) return;
  navigator.clipboard.writeText(outputRawText).then(() => {
    showMessage("已复制到剪贴板", "success");
  }).catch(() => showMessage("复制失败", "error"));
});

document.getElementById("fileInput").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    inputText.value = reader.result;
    hideMessage();
  };
  reader.readAsText(file, "UTF-8");
  e.target.value = "";
});

inputText.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    formatSql();
  }
  if (e.key === "Tab") {
    e.preventDefault();
    const start = inputText.selectionStart;
    const end = inputText.selectionEnd;
    inputText.value = inputText.value.substring(0, start) + "  " + inputText.value.substring(end);
    inputText.selectionStart = inputText.selectionEnd = start + 2;
  }
});
