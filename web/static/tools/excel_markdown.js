const API = "/api/tools/excel-markdown/convert";

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
    $("pickFileBtn").textContent = "上传 Excel";
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

function resetSheetSelect(names) {
  const sheetSelect = $("sheetSelect");
  const current = sheetSelect.value;
  sheetSelect.innerHTML = '<option value="all">全部工作表</option>';
  (names || []).forEach((name) => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    sheetSelect.appendChild(opt);
  });
  sheetSelect.disabled = !selectedFile;
  if ([...sheetSelect.options].some((o) => o.value === current)) {
    sheetSelect.value = current;
  }
}

function onFileSelected(event) {
  hideMessage();
  const input = event.target;
  selectedFile = input.files && input.files[0] ? input.files[0] : null;

  $("mdOutput").value = "";
  $("statsInfo").textContent = "";

  if (!selectedFile) {
    setUploadUi(null);
    $("convertBtn").disabled = true;
    $("sheetSelect").disabled = true;
    return;
  }

  setUploadUi(selectedFile);
  $("convertBtn").disabled = false;
  convert();
}

async function convert() {
  hideMessage();
  if (!selectedFile) {
    showMessage("请先上传 Excel 文件", "error");
    return;
  }

  const form = new FormData();
  form.append("file", selectedFile);
  form.append("sheet", $("sheetSelect").value);
  form.append("with_header", $("withHeader").checked ? "true" : "false");
  form.append("include_sheet_title", $("includeSheetTitle").checked ? "true" : "false");

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
    resetSheetSelect(data.sheet_names || []);

    const st = data.stats || {};
    $("statsInfo").textContent = `${st.chars || 0} 字符 · ${st.rows || 0} 行 · ${(st.sheets || []).length} 表`;
    showMessage("转换完成", "success");
  } catch (e) {
    $("mdOutput").value = "";
    $("statsInfo").textContent = "";
    showMessage(e.message, "error");
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
  resetSheetSelect([]);
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
  $("sheetSelect").addEventListener("change", () => {
    if (selectedFile) convert();
  });
  $("withHeader").addEventListener("change", () => {
    if (selectedFile) convert();
  });
  $("includeSheetTitle").addEventListener("change", () => {
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
