const API = "/api/tools/word-markdown/convert";

let selectedFile = null;

function $(id) {
  return document.getElementById(id);
}

function showMessage(text, type) {
  const el = $("message");
  el.textContent = text;
  el.className = `message show ${type}`;
}

function hideMessage() {
  $("message").textContent = "";
  $("message").className = "message";
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function setUploadUi(file) {
  const zoneBtn = $("fileZoneBtn");
  const nameEl = $("fileInfoName");
  const wrap = $("fileInfoWrap");

  if (file) {
    zoneBtn.classList.add("hidden");
    nameEl.classList.remove("hidden");
    nameEl.textContent = `已选择：${file.name}（${formatSize(file.size)}）`;
    wrap.classList.remove("excel-md-upload-zone");
    $("pickFileBtn").textContent = "重新上传";
  } else {
    zoneBtn.classList.remove("hidden");
    nameEl.classList.add("hidden");
    nameEl.textContent = "";
    wrap.classList.add("excel-md-upload-zone");
    $("pickFileBtn").textContent = "上传 Word";
  }
}

function setBusy(busy) {
  const fileInput = $("fileInput");
  if (fileInput) fileInput.disabled = busy;
  $("pickFileBtn").disabled = busy;
  $("fileZoneBtn").disabled = busy;
  $("convertBtn").disabled = busy || !selectedFile;
}

function openFilePicker() {
  const fileInput = $("fileInput");
  if (!fileInput || fileInput.disabled) return;
  fileInput.click();
}

function onFileSelected() {
  hideMessage();
  const fileInput = $("fileInput");
  selectedFile = fileInput.files && fileInput.files[0] ? fileInput.files[0] : null;

  $("mdOutput").value = "";
  $("statsInfo").textContent = "";

  if (!selectedFile) {
    setUploadUi(null);
    $("convertBtn").disabled = true;
    return;
  }

  setUploadUi(selectedFile);
  $("convertBtn").disabled = false;
  convert();
}

async function convert() {
  hideMessage();
  if (!selectedFile) {
    showMessage("请先上传 Word 文件", "error");
    return;
  }

  const form = new FormData();
  form.append("file", selectedFile);
  form.append("ignore_images", $("ignoreImages").checked ? "true" : "false");

  setBusy(true);
  showMessage("正在转换...", "info");

  try {
    const res = await fetch(API, { method: "POST", body: form });
    let data = {};
    try {
      data = await res.json();
    } catch (_) {
      throw new Error("服务器响应异常");
    }
    if (!res.ok) throw new Error(data.detail || "转换失败");

    $("mdOutput").value = data.markdown || "";
    const st = data.stats || {};
    const warnCount = st.warnings || 0;
    $("statsInfo").textContent = `${st.chars || 0} 字符 · ${st.lines || 0} 行${warnCount ? ` · ${warnCount} 条警告` : ""}`;

    if (warnCount > 0) {
      showMessage(`转换完成（有 ${warnCount} 条格式警告，部分样式可能未完全保留）`, "success");
    } else {
      showMessage("转换完成", "success");
    }
  } catch (e) {
    $("mdOutput").value = "";
    $("statsInfo").textContent = "";
    const msg = e && e.message ? e.message : "转换失败";
    showMessage(msg === "Failed to fetch" ? "无法连接服务器，请确认服务已启动" : msg, "error");
  } finally {
    setBusy(false);
  }
}

function clearAll() {
  selectedFile = null;
  $("fileInput").value = "";
  $("mdOutput").value = "";
  $("statsInfo").textContent = "";
  $("convertBtn").disabled = true;
  setUploadUi(null);
  hideMessage();
}

function init() {
  const fileInput = $("fileInput");
  if (!fileInput) {
    showMessage("页面初始化失败，请刷新重试", "error");
    return;
  }

  $("pickFileBtn").addEventListener("click", openFilePicker);
  $("fileZoneBtn").addEventListener("click", openFilePicker);
  fileInput.addEventListener("change", onFileSelected);
  $("convertBtn").addEventListener("click", convert);
  $("ignoreImages").addEventListener("change", () => {
    if (selectedFile) convert();
  });
  $("copyBtn").addEventListener("click", () => {
    if (!$("mdOutput").value) return;
    navigator.clipboard.writeText($("mdOutput").value).then(
      () => showMessage("已复制到剪贴板", "success"),
      () => showMessage("复制失败", "error")
    );
  });
  $("clearBtn").addEventListener("click", clearAll);
  setUploadUi(null);
}

init();
