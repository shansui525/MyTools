const API = "/api/tools/sql-formatter/process";
const LINT_API = "/api/tools/sql-formatter/lint";

const inputText = document.getElementById("inputText");
const inputLineGutter = document.getElementById("inputLineGutter");
const outputPre = document.getElementById("outputPre");
const outputLineGutter = document.getElementById("outputLineGutter");
const outputCode = document.getElementById("outputCode");
const message = document.getElementById("message");
const issuesPanel = document.getElementById("issuesPanel");
const issuesList = document.getElementById("issuesList");
const issuesSummary = document.getElementById("issuesSummary");

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

function countLines(text) {
  if (!text) return 1;
  return text.split("\n").length;
}

function renderLineNumbers(gutterEl, lineCount) {
  gutterEl.innerHTML = Array.from({ length: lineCount }, (_, i) => `<span>${i + 1}</span>`).join("");
}

function syncGutterScroll(source, gutter) {
  gutter.scrollTop = source.scrollTop;
}

function updateInputLineNumbers() {
  renderLineNumbers(inputLineGutter, countLines(inputText.value));
  syncGutterScroll(inputText, inputLineGutter);
}

function updateOutputLineNumbers() {
  renderLineNumbers(outputLineGutter, countLines(outputRawText));
  syncGutterScroll(outputPre, outputLineGutter);
}

function clearOutput() {
  outputRawText = "";
  outputCode.innerHTML = '<span class="sql-output-empty">格式化结果将显示在这里</span>';
  updateOutputLineNumbers();
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
  updateOutputLineNumbers();
}

function getRequestBody() {
  return {
    text: inputText.value,
    indent: parseInt(document.getElementById("indentSelect").value, 10),
    keyword_case: document.getElementById("keywordCaseSelect").value,
    dialect: document.getElementById("dialectSelect").value,
  };
}

function renderIssues(data) {
  const issues = data.issues || [];
  const summary = data.issue_summary || { errors: 0, warnings: 0 };

  if (!issues.length) {
    issuesPanel.classList.add("hidden");
    issuesList.innerHTML = "";
    return;
  }

  issuesPanel.classList.remove("hidden");
  issuesSummary.textContent = `语法检查：${summary.errors} 个错误，${summary.warnings} 个警告`;

  issuesList.innerHTML = issues
    .map((item) => {
      const levelClass = item.level === "error" ? "sql-issue-error" : "sql-issue-warning";
      return `<li class="sql-issue-item ${levelClass}">
        <span class="sql-issue-level">${item.level === "error" ? "错误" : "警告"}</span>
        <span class="sql-issue-pos">L${item.line}:C${item.column}</span>
        <span class="sql-issue-msg">${escapeHtml(item.message)}</span>
      </li>`;
    })
    .join("");
}

async function formatSql() {
  hideMessage();
  const body = getRequestBody();
  if (!body.text.trim()) {
    showMessage("请输入 SQL 内容", "error");
    return;
  }

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
    renderIssues(data);

    const { errors, warnings } = data.issue_summary || { errors: 0, warnings: 0 };
    if (errors > 0) {
      showMessage(`格式化完成，发现 ${errors} 个语法错误`, "error");
    } else if (warnings > 0) {
      showMessage(`格式化完成，发现 ${warnings} 个警告`, "info");
    } else {
      showMessage("格式化完成，未发现语法问题", "success");
    }
  } catch (e) {
    clearOutput();
    issuesPanel.classList.add("hidden");
    showMessage(e.message, "error");
  }
}

async function lintSql() {
  hideMessage();
  const body = getRequestBody();
  if (!body.text.trim()) {
    showMessage("请输入 SQL 内容", "error");
    return;
  }

  try {
    const res = await fetch(LINT_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: body.text, dialect: body.dialect }),
    });
    const data = await res.json();
    if (!res.ok) {
      const detail = data.detail;
      throw new Error(typeof detail === "string" ? detail : "检查失败");
    }

    renderIssues(data);
    const { errors, warnings } = data.issue_summary || { errors: 0, warnings: 0 };
    if (errors > 0) {
      showMessage(`发现 ${errors} 个语法错误`, "error");
    } else if (warnings > 0) {
      showMessage(`发现 ${warnings} 个警告`, "info");
    } else {
      showMessage("未发现语法问题", "success");
    }
  } catch (e) {
    issuesPanel.classList.add("hidden");
    showMessage(e.message, "error");
  }
}

document.getElementById("formatBtn").addEventListener("click", formatSql);
document.getElementById("lintBtn").addEventListener("click", lintSql);

document.getElementById("clearInputBtn").addEventListener("click", () => {
  inputText.value = "";
  updateInputLineNumbers();
  clearOutput();
  issuesPanel.classList.add("hidden");
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
    updateInputLineNumbers();
    hideMessage();
  };
  reader.readAsText(file, "UTF-8");
  e.target.value = "";
});

inputText.addEventListener("input", updateInputLineNumbers);
inputText.addEventListener("scroll", () => syncGutterScroll(inputText, inputLineGutter));
outputPre.addEventListener("scroll", () => syncGutterScroll(outputPre, outputLineGutter));

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
    updateInputLineNumbers();
  }
});

inputText.value = `INSERT OVERWRITE TABLE dwd.trade_detail PARTITION(dt='2026-07-08')
SELECT
  t.trade_id,
  t.customer_id,
  from_unixtime(t.trade_ts) AS trade_time,
  get_json_object(t.ext_info, '$.channel') AS channel
FROM ods.core_trade_log t
LATERAL VIEW explode(split(t.product_list, ',')) p AS product_id
WHERE t.dt = '2026-07-08'
  AND t.trade_status IN ('SUCCESS', 'SETTLED')
GROUP BY t.trade_id, t.customer_id, trade_time, channel;`;

updateInputLineNumbers();
updateOutputLineNumbers();
