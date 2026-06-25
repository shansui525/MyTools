const API = "/api/tools/curl-converter/convert";

const curlInput = document.getElementById("curlInput");
const codeOutput = document.getElementById("codeOutput");
const message = document.getElementById("message");

const EXAMPLE = `curl -X POST 'https://api.example.com/users' \\
  -H 'Content-Type: application/json' \\
  -H 'Authorization: Bearer token123' \\
  -d '{"name": "张三", "age": 25}'`;

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
  if (!curlInput.value.trim()) {
    showMessage("请输入 curl 命令", "error");
    return;
  }
  try {
    const res = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        curl: curlInput.value,
        include_response: document.getElementById("includeResponse").checked,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "转换失败");
    codeOutput.value = data.code;
    showMessage("转换完成", "success");
  } catch (e) {
    codeOutput.value = "";
    showMessage(e.message, "error");
  }
}

document.getElementById("convertBtn").addEventListener("click", convert);
document.getElementById("clearBtn").addEventListener("click", () => {
  curlInput.value = "";
  codeOutput.value = "";
  hideMessage();
});
document.getElementById("copyBtn").addEventListener("click", () => {
  if (!codeOutput.value) return;
  navigator.clipboard.writeText(codeOutput.value).then(() => {
    showMessage("已复制到剪贴板", "success");
  }).catch(() => showMessage("复制失败", "error"));
});
document.getElementById("exampleBtn").addEventListener("click", () => {
  curlInput.value = EXAMPLE;
  hideMessage();
});

curlInput.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
    e.preventDefault();
    convert();
  }
});
