const SHEETS_API = "/api/tools/excel-compare/sheets";
const COMPARE_API = "/api/tools/excel-compare/compare";

const form = document.getElementById("compareForm");
const keysGroup = document.getElementById("keysGroup");
const keysInput = document.getElementById("keys");
const submitBtn = document.getElementById("submitBtn");
const loading = document.getElementById("loading");
const message = document.getElementById("message");
const fileAInput = document.getElementById("fileA");
const fileBInput = document.getElementById("fileB");
const sheetASelect = document.getElementById("sheetA");
const sheetBSelect = document.getElementById("sheetB");

document.querySelectorAll('input[name="mode"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    const isKeyMode = document.querySelector('input[name="mode"]:checked').value === "key";
    keysGroup.style.display = isKeyMode ? "block" : "none";
    keysInput.required = isKeyMode;
  });
});

function showMessage(text, type) {
  message.textContent = text;
  message.className = `message show ${type}`;
}

function hideMessage() {
  message.className = "message";
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function setFileLabel(nameId, file) {
  const nameEl = document.getElementById(nameId);
  if (!nameEl) return;
  if (file) {
    nameEl.textContent = `${file.name}（${formatSize(file.size)}）`;
  } else {
    nameEl.textContent = "未选择文件";
  }
}

function resetSheetSelect(selectEl, names, hasFile) {
  const current = selectEl.value;
  selectEl.innerHTML = "";

  if (!hasFile) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "请先选择文件";
    selectEl.appendChild(opt);
    selectEl.disabled = true;
    return;
  }

  if (!names || names.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "未找到工作表";
    selectEl.appendChild(opt);
    selectEl.disabled = true;
    return;
  }

  names.forEach((name, idx) => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = names.length > 1 ? `${name}（第 ${idx + 1} 个）` : name;
    selectEl.appendChild(opt);
  });

  selectEl.disabled = false;
  if ([...selectEl.options].some((o) => o.value === current)) {
    selectEl.value = current;
  }
}

async function loadSheetNames(file, selectEl) {
  resetSheetSelect(selectEl, [], false);

  if (!file) {
    return;
  }

  selectEl.disabled = true;
  selectEl.innerHTML = '<option value="">正在读取工作表...</option>';

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(SHEETS_API, { method: "POST", body: formData });
    if (!res.ok) {
      let detail = "读取工作表失败";
      try {
        const err = await res.json();
        detail = formatErrorDetail(err.detail);
      } catch (_) {
        detail = (await res.text()) || detail;
      }
      throw new Error(detail);
    }

    const data = await res.json();
    resetSheetSelect(selectEl, data.sheet_names || [], true);
  } catch (err) {
    resetSheetSelect(selectEl, [], true);
    selectEl.innerHTML = '<option value="">读取工作表失败</option>';
    selectEl.disabled = true;
    const msg = err && err.message ? err.message : "读取工作表失败";
    showMessage(`工作表列表加载失败：${msg}`, "error");
  }
}

function openFilePicker(input) {
  if (input && !input.disabled) {
    input.click();
  }
}

document.getElementById("pickFileA").addEventListener("click", () => openFilePicker(fileAInput));
document.getElementById("pickFileB").addEventListener("click", () => openFilePicker(fileBInput));

fileAInput.addEventListener("change", async () => {
  hideMessage();
  const file = fileAInput.files[0] || null;
  setFileLabel("fileAName", file);
  await loadSheetNames(file, sheetASelect);
});

fileBInput.addEventListener("change", async () => {
  hideMessage();
  const file = fileBInput.files[0] || null;
  setFileLabel("fileBName", file);
  await loadSheetNames(file, sheetBSelect);
});

function formatErrorDetail(detail) {
  if (!detail) return "对比失败";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join("；");
  }
  return String(detail);
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideMessage();

  const fileA = fileAInput.files[0];
  const fileB = fileBInput.files[0];
  const mode = document.querySelector('input[name="mode"]:checked').value;
  const keys = keysInput.value.trim();
  const sheetA = sheetASelect.value.trim();
  const sheetB = sheetBSelect.value.trim();

  if (!fileA || !fileB) {
    showMessage("请选择两个 Excel 文件", "error");
    return;
  }

  if (mode === "key" && !keys) {
    showMessage("主键对比模式需要指定主键列名", "error");
    return;
  }

  if (sheetASelect.disabled || sheetBSelect.disabled) {
    showMessage("请等待工作表列表加载完成", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file_a", fileA);
  formData.append("file_b", fileB);
  formData.append("mode", mode);
  formData.append("keys", keys);
  if (sheetA) formData.append("sheet_a", sheetA);
  if (sheetB) formData.append("sheet_b", sheetB);

  submitBtn.disabled = true;
  loading.classList.add("show");

  try {
    const res = await fetch(COMPARE_API, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      let detail = "对比失败";
      try {
        const err = await res.json();
        detail = formatErrorDetail(err.detail);
      } catch (_) {
        detail = (await res.text()) || detail;
      }
      throw new Error(detail);
    }

    const diffCount = res.headers.get("X-Diff-Count") || "未知";
    const blob = await res.blob();
    if (!blob.size) {
      throw new Error("服务器返回空结果文件");
    }

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "compare_result.xlsx";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    const sheetInfo =
      sheetA || sheetB
        ? `（A: ${sheetA || "默认"} / B: ${sheetB || "默认"}）`
        : "";
    showMessage(`对比完成${sheetInfo}！共发现 ${diffCount} 处差异，结果文件已下载。`, "success");
  } catch (err) {
    const msg = err && err.message ? err.message : "对比过程中发生错误";
    if (msg === "Failed to fetch") {
      showMessage("无法连接服务器，请确认服务已启动且对比未超时后重试", "error");
    } else {
      showMessage(msg, "error");
    }
  } finally {
    submitBtn.disabled = false;
    loading.classList.remove("show");
  }
});
