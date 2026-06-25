const API = "/api/tools/password-manager";

const CATEGORY_LABELS = { website: "网站", computer: "电脑", other: "其他" };
const CATEGORY_ICONS = { website: "🌐", computer: "💻", other: "📁" };

let currentDetailId = null;
let selectedExportType = null;

async function api(path, options = {}) {
  const res = await fetch(API + path, { credentials: "include", ...options });
  if (!res.ok) {
    let detail = "请求失败";
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch (_) {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res;
}

function showMessage(el, text, type) {
  el.textContent = text;
  el.className = `message show ${type}`;
}

function hideMessage(el) {
  el.className = "message";
}

function showScreen(id) {
  ["loadingScreen", "errorScreen", "initScreen", "unlockScreen", "mainScreen"].forEach((s) => {
    document.getElementById(s).classList.toggle("hidden", s !== id);
  });
}

function showError(message) {
  document.getElementById("errorMessage").textContent = message;
  showScreen("errorScreen");
}

async function checkStatus() {
  showScreen("loadingScreen");
  try {
    const status = await api("/status");
    if (!status.initialized) {
      showScreen("initScreen");
    } else if (!status.unlocked) {
      showScreen("unlockScreen");
    } else {
      showScreen("mainScreen");
      loadEntries();
    }
  } catch (e) {
    showError(e.message || "无法连接密码管理器服务，请确认 MyTools 已启动后刷新页面");
  }
}

async function loadEntries() {
  const q = document.getElementById("searchInput").value;
  const list = document.getElementById("entryList");
  try {
    const data = await api("/entries" + (q ? `?q=${encodeURIComponent(q)}` : ""));

    if (!data.entries.length) {
      list.innerHTML = '<div class="empty-state">暂无密码条目，点击「新增」添加</div>';
      return;
    }

    list.innerHTML = data.entries.map((e) => `
    <div class="entry-item" data-id="${e.id}">
      <div class="entry-icon">${CATEGORY_ICONS[e.category] || "📁"}</div>
      <div class="entry-info">
        <h4>${escapeHtml(e.title)} <span class="badge badge-${e.category}">${CATEGORY_LABELS[e.category] || e.category}</span></h4>
        <div class="meta">${escapeHtml(e.target || "—")} · 更新于 ${e.updated_at}</div>
      </div>
      <div class="entry-actions">
        <button class="btn btn-secondary btn-sm view-btn" data-id="${e.id}">查看</button>
      </div>
    </div>
  `).join("");

  list.querySelectorAll(".entry-item, .view-btn").forEach((el) => {
    el.addEventListener("click", (ev) => {
      if (ev.target.classList.contains("view-btn")) ev.stopPropagation();
      const id = el.dataset.id || el.closest(".entry-item")?.dataset.id;
      if (id) showDetail(parseInt(id));
    });
  });
  } catch (e) {
    list.innerHTML = `<div class="empty-state message show error">加载条目失败: ${escapeHtml(e.message)}</div>`;
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ---------- 初始化 / 解锁 / 锁定 ----------

document.getElementById("initBtn").addEventListener("click", async () => {
  const msg = document.getElementById("initMessage");
  hideMessage(msg);
  const pwd = document.getElementById("initPassword").value;
  const confirm = document.getElementById("initPasswordConfirm").value;
  if (pwd.length < 8) return showMessage(msg, "主密码至少 8 位", "error");
  if (pwd !== confirm) return showMessage(msg, "两次密码不一致", "error");
  try {
    await api("/vault/init", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pwd }),
    });
    showScreen("mainScreen");
    loadEntries();
  } catch (e) {
    showMessage(msg, e.message, "error");
  }
});

document.getElementById("unlockBtn").addEventListener("click", async () => {
  const msg = document.getElementById("unlockMessage");
  hideMessage(msg);
  const pwd = document.getElementById("unlockPassword").value;
  try {
    await api("/vault/unlock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pwd }),
    });
    showScreen("mainScreen");
    loadEntries();
  } catch (e) {
    showMessage(msg, e.message, "error");
  }
});

document.getElementById("resetVaultLink").addEventListener("click", async (e) => {
  e.preventDefault();
  if (!confirm("确定重置密码库？所有密码条目将被永久删除，此操作不可恢复。")) return;
  if (!confirm("再次确认：重置后将回到首次使用，需重新设置主密码。")) return;
  try {
    await api("/vault/reset", { method: "POST" });
    document.getElementById("unlockPassword").value = "";
    document.getElementById("initPassword").value = "";
    document.getElementById("initPasswordConfirm").value = "";
    showScreen("initScreen");
  } catch (err) {
    const msg = document.getElementById("unlockMessage");
    showMessage(msg, err.message, "error");
  }
});

document.getElementById("lockBtn").addEventListener("click", async () => {
  await api("/vault/lock", { method: "POST" });
  showScreen("unlockScreen");
});

document.getElementById("searchInput").addEventListener("input", debounce(loadEntries, 300));

// ---------- 新增 / 编辑 ----------

document.getElementById("addBtn").addEventListener("click", () => openEntryModal());

function openEntryModal(entry) {
  document.getElementById("entryModalTitle").textContent = entry ? "编辑密码" : "新增密码";
  document.getElementById("entryId").value = entry ? entry.id : "";
  document.getElementById("entryTitle").value = entry?.title || "";
  document.getElementById("entryCategory").value = entry?.category || "website";
  document.getElementById("entryTarget").value = entry?.target || "";
  document.getElementById("entryUsername").value = entry?.username || "";
  document.getElementById("entryPassword").value = entry?.password || "";
  document.getElementById("entryNotes").value = entry?.notes || "";
  hideMessage(document.getElementById("entryMessage"));
  document.getElementById("entryModal").classList.add("show");
}

document.getElementById("entryCancelBtn").addEventListener("click", () => {
  document.getElementById("entryModal").classList.remove("show");
});

document.getElementById("toggleEntryPwd").addEventListener("click", () => {
  const input = document.getElementById("entryPassword");
  const btn = document.getElementById("toggleEntryPwd");
  if (input.type === "password") {
    input.type = "text";
    btn.textContent = "隐藏";
  } else {
    input.type = "password";
    btn.textContent = "显示";
  }
});

document.getElementById("entryForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = document.getElementById("entryMessage");
  hideMessage(msg);
  const id = document.getElementById("entryId").value;
  const body = {
    title: document.getElementById("entryTitle").value.trim(),
    category: document.getElementById("entryCategory").value,
    target: document.getElementById("entryTarget").value.trim(),
    username: document.getElementById("entryUsername").value,
    password: document.getElementById("entryPassword").value,
    notes: document.getElementById("entryNotes").value,
  };
  if (!body.title) return showMessage(msg, "标识名称不能为空", "error");
  try {
    if (id) {
      await api(`/entries/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } else {
      await api("/entries", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    }
    document.getElementById("entryModal").classList.remove("show");
    loadEntries();
  } catch (err) {
    showMessage(msg, err.message, "error");
  }
});

// ---------- 详情 ----------

async function showDetail(id) {
  currentDetailId = id;
  const entry = await api(`/entries/${id}`);
  document.getElementById("detailTitle").textContent = entry.title;
  document.getElementById("detailContent").innerHTML = `
    <div class="detail-row"><span class="label">类型</span><span class="value">${CATEGORY_LABELS[entry.category] || entry.category}</span></div>
    <div class="detail-row"><span class="label">网址/电脑</span><span class="value">${escapeHtml(entry.target || "—")}</span></div>
    <div class="detail-row"><span class="label">用户名</span><span class="value" id="detailUsername">${escapeHtml(entry.username)}</span></div>
    <div class="detail-row"><span class="label">密码</span><span class="value"><span id="detailPassword" data-pwd="${escapeHtml(entry.password)}">••••••••</span> <button class="btn btn-secondary btn-sm" id="toggleDetailPwd">显示</button></span></div>
    <div class="detail-row"><span class="label">备注</span><span class="value">${escapeHtml(entry.notes || "—")}</span></div>
    <div class="detail-row"><span class="label">更新时间</span><span class="value">${entry.updated_at}</span></div>
  `;
  document.getElementById("detailModal").classList.add("show");

  document.getElementById("toggleDetailPwd").addEventListener("click", () => {
    const el = document.getElementById("detailPassword");
    const btn = document.getElementById("toggleDetailPwd");
    if (btn.textContent === "显示") {
      el.textContent = el.dataset.pwd;
      btn.textContent = "隐藏";
    } else {
      el.textContent = "••••••••";
      btn.textContent = "显示";
    }
  });
}

document.getElementById("detailCloseBtn").addEventListener("click", () => {
  document.getElementById("detailModal").classList.remove("show");
});

document.getElementById("copyUsernameBtn").addEventListener("click", () => {
  const text = document.getElementById("detailUsername")?.textContent;
  if (text) copyToClipboard(text);
});

document.getElementById("copyPasswordBtn").addEventListener("click", () => {
  const el = document.getElementById("detailPassword");
  if (el) copyToClipboard(el.dataset.pwd);
});

document.getElementById("editEntryBtn").addEventListener("click", async () => {
  if (!currentDetailId) return;
  const entry = await api(`/entries/${currentDetailId}`);
  document.getElementById("detailModal").classList.remove("show");
  openEntryModal(entry);
});

document.getElementById("deleteEntryBtn").addEventListener("click", async () => {
  if (!currentDetailId || !confirm("确定删除此密码条目？")) return;
  await api(`/entries/${currentDetailId}`, { method: "DELETE" });
  document.getElementById("detailModal").classList.remove("show");
  loadEntries();
});

// ---------- 导出 ----------

document.getElementById("exportBtn").addEventListener("click", () => {
  selectedExportType = null;
  document.getElementById("exportPasswordGroup").classList.add("hidden");
  document.getElementById("exportConfirmBtn").classList.add("hidden");
  document.getElementById("exportPassword").value = "";
  hideMessage(document.getElementById("exportMessage"));
  document.getElementById("exportModal").classList.add("show");
});

document.getElementById("exportCancelBtn").addEventListener("click", () => {
  document.getElementById("exportModal").classList.remove("show");
});

document.querySelectorAll(".export-option").forEach((el) => {
  el.addEventListener("click", () => {
    selectedExportType = el.dataset.export;
    const isEncrypted = selectedExportType === "encrypted";
    document.getElementById("exportPasswordGroup").classList.toggle("hidden", !isEncrypted);
    document.getElementById("exportConfirmBtn").classList.remove("hidden");
  });
});

document.getElementById("exportConfirmBtn").addEventListener("click", async () => {
  const msg = document.getElementById("exportMessage");
  hideMessage(msg);
  try {
    if (selectedExportType === "json") {
      const res = await fetch(API + "/export/json", { credentials: "include" });
      if (!res.ok) throw new Error("导出失败");
      await downloadResponse(res, "password_vault_export.json");
    } else if (selectedExportType === "csv") {
      const res = await fetch(API + "/export/csv", { credentials: "include" });
      if (!res.ok) throw new Error("导出失败");
      await downloadResponse(res, "password_vault_export.csv");
    } else if (selectedExportType === "encrypted") {
      const pwd = document.getElementById("exportPassword").value;
      if (pwd.length < 8) return showMessage(msg, "导出密码至少 8 位", "error");
      const res = await fetch(API + "/export/encrypted", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ export_password: pwd }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "导出失败");
      }
      await downloadResponse(res, "password_vault_backup.mytools-vault");
    } else {
      return showMessage(msg, "请选择导出方式", "error");
    }
    showMessage(msg, "导出成功，文件已下载", "success");
  } catch (e) {
    showMessage(msg, e.message, "error");
  }
});

// ---------- 导入 ----------

let activeImportTab = "json";

document.getElementById("importBtn").addEventListener("click", () => {
  hideMessage(document.getElementById("importMessage"));
  document.getElementById("importModal").classList.add("show");
});

document.getElementById("importCancelBtn").addEventListener("click", () => {
  document.getElementById("importModal").classList.remove("show");
});

document.querySelectorAll(".tabs .tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    activeImportTab = tab.dataset.tab;
    document.querySelectorAll(".tabs .tab").forEach((t) => t.classList.toggle("active", t === tab));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${activeImportTab}`));
  });
});

document.getElementById("importConfirmBtn").addEventListener("click", async () => {
  const msg = document.getElementById("importMessage");
  hideMessage(msg);
  const mode = document.querySelector('input[name="importMode"]:checked').value;
  const formData = new FormData();
  formData.append("mode", mode);

  try {
    let url;
    if (activeImportTab === "json") {
      const file = document.getElementById("importJsonFile").files[0];
      if (!file) return showMessage(msg, "请选择 JSON 文件", "error");
      formData.append("file", file);
      url = "/import/json";
    } else if (activeImportTab === "csv") {
      const file = document.getElementById("importCsvFile").files[0];
      if (!file) return showMessage(msg, "请选择 CSV 文件", "error");
      formData.append("file", file);
      url = "/import/csv";
    } else {
      const file = document.getElementById("importEncryptedFile").files[0];
      const pwd = document.getElementById("importExportPassword").value;
      if (!file) return showMessage(msg, "请选择加密备份文件", "error");
      if (!pwd) return showMessage(msg, "请输入导出密码", "error");
      formData.append("file", file);
      formData.append("export_password", pwd);
      url = "/import/encrypted";
    }

    const res = await fetch(API + url, { method: "POST", credentials: "include", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "导入失败");
    showMessage(msg, data.message, "success");
    loadEntries();
  } catch (e) {
    showMessage(msg, e.message, "error");
  }
});

// ---------- 工具函数 ----------

async function downloadResponse(res, filename) {
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    alert("已复制到剪贴板");
  }).catch(() => {
    alert("复制失败，请手动复制");
  });
}

function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

checkStatus();
