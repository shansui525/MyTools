const API = "/api/tools/json-formatter/process";

const inputText = document.getElementById("inputText");
const outputTree = document.getElementById("outputTree");
const outputText = document.getElementById("outputText");
const message = document.getElementById("message");
const expandAllBtn = document.getElementById("expandAllBtn");
const collapseAllBtn = document.getElementById("collapseAllBtn");

let outputRawText = "";

function showMessage(text, type) {
  message.textContent = text;
  message.className = `message show ${type}`;
}

function hideMessage() {
  message.textContent = "";
  message.className = "message";
}

function setOutputMode(mode) {
  const isTree = mode === "tree";
  outputTree.classList.toggle("hidden", !isTree);
  outputText.classList.toggle("hidden", isTree);
  expandAllBtn.classList.toggle("hidden", !isTree);
  collapseAllBtn.classList.toggle("hidden", !isTree);
}

function clearOutput() {
  outputRawText = "";
  outputTree.innerHTML = '<div class="json-tree-empty">处理结果将显示在这里</div>';
  outputText.value = "";
  setOutputMode("tree");
}

function createPrimitiveNode(value) {
  const span = document.createElement("span");
  if (value === null) {
    span.className = "json-null";
    span.textContent = "null";
  } else if (typeof value === "boolean") {
    span.className = "json-boolean";
    span.textContent = String(value);
  } else if (typeof value === "number") {
    span.className = "json-number";
    span.textContent = String(value);
  } else {
    span.className = "json-string";
    span.textContent = JSON.stringify(value);
  }
  return span;
}

function buildCollapsibleNode(value, openBracket, closeBracket, previewText) {
  const block = document.createElement("div");
  block.className = "json-block";

  const head = document.createElement("span");
  head.className = "json-block-head";

  const toggle = document.createElement("span");
  toggle.className = "json-toggle";
  toggle.textContent = "▼";

  const open = document.createElement("span");
  open.className = "json-bracket";
  open.textContent = openBracket;

  const preview = document.createElement("span");
  preview.className = "json-preview";
  preview.textContent = previewText;

  head.appendChild(toggle);
  head.appendChild(open);
  head.appendChild(preview);

  const children = document.createElement("div");
  children.className = "json-children";

  const closeLine = document.createElement("span");
  closeLine.className = "json-close-bracket json-line";
  const close = document.createElement("span");
  close.className = "json-bracket";
  close.textContent = closeBracket;
  closeLine.appendChild(close);

  head.addEventListener("click", (e) => {
    e.stopPropagation();
    block.classList.toggle("collapsed");
    toggle.textContent = block.classList.contains("collapsed") ? "▶" : "▼";
  });

  block.appendChild(head);
  block.appendChild(children);
  block.appendChild(closeLine);

  return { block, children };
}

function renderValue(value, container) {
  if (value === null || typeof value !== "object") {
    container.appendChild(createPrimitiveNode(value));
    return;
  }

  const isArray = Array.isArray(value);
  const entries = isArray ? value.map((v, i) => [i, v]) : Object.entries(value);
  const previewText = isArray
    ? ` ${entries.length} 项 `
    : ` ${entries.length} 键 `;

  const { block, children } = buildCollapsibleNode(
    value,
    isArray ? "[" : "{",
    isArray ? "]" : "}",
    previewText
  );

  entries.forEach(([key, val], index) => {
    const line = document.createElement("div");
    line.className = "json-line";

    if (!isArray) {
      const keySpan = document.createElement("span");
      keySpan.className = "json-key";
      keySpan.textContent = JSON.stringify(key);
      line.appendChild(keySpan);

      const colon = document.createElement("span");
      colon.className = "json-colon";
      colon.textContent = ": ";
      line.appendChild(colon);
    }

    if (val !== null && typeof val === "object") {
      renderValue(val, line);
    } else {
      line.appendChild(createPrimitiveNode(val));
    }

    if (index < entries.length - 1) {
      const comma = document.createElement("span");
      comma.className = "json-comma";
      comma.textContent = ",";
      line.appendChild(comma);
    }

    children.appendChild(line);
  });

  container.appendChild(block);
}

function renderOutputTree(jsonText) {
  outputRawText = jsonText;
  setOutputMode("tree");
  const data = JSON.parse(jsonText);
  outputTree.innerHTML = "";
  const root = document.createElement("div");
  root.className = "json-tree";
  renderValue(data, root);
  outputTree.appendChild(root);
}

function renderOutputText(jsonText) {
  outputRawText = jsonText;
  setOutputMode("text");
  outputText.value = jsonText;
}

function setAllCollapsed(collapsed) {
  outputTree.querySelectorAll(".json-block").forEach((block) => {
    block.classList.toggle("collapsed", collapsed);
    const toggle = block.querySelector(".json-toggle");
    if (toggle) toggle.textContent = collapsed ? "▶" : "▼";
  });
}

async function process(action) {
  hideMessage();
  const text = inputText.value;
  if (!text.trim()) {
    showMessage("请输入 JSON 内容", "error");
    return;
  }

  const body = {
    text,
    action,
    indent: parseInt(document.getElementById("indentSelect").value, 10),
    sort_keys: document.getElementById("sortKeys").checked,
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
      if (detail && typeof detail === "object") {
        const loc = detail.line ? `（第 ${detail.line} 行，第 ${detail.column} 列）` : "";
        throw new Error((detail.message || "JSON 解析失败") + loc);
      }
      throw new Error(typeof detail === "string" ? detail : "处理失败");
    }

    if (action === "validate") {
      const typeLabel = { object: "对象", array: "数组" };
      const sizeInfo = data.size != null ? `，包含 ${data.size} 个${data.type === "array" ? "元素" : "键"}` : "";
      clearOutput();
      showMessage(`JSON 格式正确，类型：${typeLabel[data.type] || data.type}${sizeInfo}`, "success");
    } else if (action === "minify") {
      renderOutputText(data.result);
      showMessage("压缩完成", "success");
    } else {
      renderOutputTree(data.result);
      showMessage("格式化完成，点击 ▼/▶ 可折叠展开", "success");
    }
  } catch (e) {
    clearOutput();
    showMessage(e.message, "error");
  }
}

document.getElementById("formatBtn").addEventListener("click", () => process("format"));
document.getElementById("minifyBtn").addEventListener("click", () => process("minify"));
document.getElementById("validateBtn").addEventListener("click", () => process("validate"));

expandAllBtn.addEventListener("click", () => setAllCollapsed(false));
collapseAllBtn.addEventListener("click", () => setAllCollapsed(true));

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
  if (e.key === "Tab") {
    e.preventDefault();
    const start = inputText.selectionStart;
    const end = inputText.selectionEnd;
    inputText.value = inputText.value.substring(0, start) + "  " + inputText.value.substring(end);
    inputText.selectionStart = inputText.selectionEnd = start + 2;
  }
});
