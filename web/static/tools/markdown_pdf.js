const API = "/api/tools/markdown-pdf/convert";

const markdownInput = document.getElementById("markdownInput");
const filenameInput = document.getElementById("filenameInput");
const message = document.getElementById("message");

const EXAMPLE = `# Markdown 转 PDF 示例

## 功能介绍

这是一个 **MyTools** 工具，可将 Markdown 转为 PDF。

### 支持语法

- 标题与列表
- **粗体** 与 *斜体*
- 代码块与表格
- 引用块

> 良好的文档从清晰的结构开始。

### 代码示例

\`\`\`python
def hello(name: str) -> str:
    return f"Hello, {name}!"
\`\`\`

### 表格

| 功能 | 说明 |
|------|------|
| 标题 | H1 ~ H6 |
| 代码 | 语法高亮 |
| 表格 | 自动排版 |
`;

function showMessage(text, type) {
  message.textContent = text;
  message.className = `message show ${type}`;
}

function hideMessage() {
  message.textContent = "";
  message.className = "message";
}

async function convert() {
  hideMessage();
  if (!markdownInput.value.trim()) {
    showMessage("请输入 Markdown 内容", "error");
    return;
  }

  const filename = filenameInput.value.trim() || "document.pdf";
  const title = filename.replace(/\.pdf$/i, "") || "Document";

  try {
    showMessage("正在生成 PDF...", "info");
    const res = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        markdown: markdownInput.value,
        title,
        filename,
      }),
    });

    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "生成失败");
    }

    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/);
    const outName = match ? match[1] : filename;

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = outName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    showMessage("PDF 已生成并下载", "success");
  } catch (e) {
    showMessage(e.message, "error");
  }
}

document.getElementById("convertBtn").addEventListener("click", convert);
document.getElementById("clearBtn").addEventListener("click", () => {
  markdownInput.value = "";
  hideMessage();
});
document.getElementById("exampleBtn").addEventListener("click", () => {
  markdownInput.value = EXAMPLE;
  hideMessage();
});

document.getElementById("fileInput").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    markdownInput.value = reader.result;
    if (!filenameInput.value || filenameInput.value === "document.pdf") {
      const base = file.name.replace(/\.(md|markdown|txt)$/i, "") || "document";
      filenameInput.value = `${base}.pdf`;
    }
    hideMessage();
  };
  reader.readAsText(file, "UTF-8");
  e.target.value = "";
});

markdownInput.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
    e.preventDefault();
    convert();
  }
});
