const API = "/api/tools/sqlite-browser";

let currentDbId = null;
let metadataCache = null;
let databasesCache = [];

const dbSelect = document.getElementById("dbSelect");
const dbPathInput = document.getElementById("dbPathInput");
const sqlInput = document.getElementById("sqlInput");
const metaTree = document.getElementById("metaTree");
const metaEmpty = document.getElementById("metaEmpty");
const historyList = document.getElementById("historyList");
const resultWrap = document.getElementById("resultWrap");
const resultSection = document.getElementById("resultSection");
const resultMsg = document.getElementById("resultMsg");
const resultFullscreenBtn = document.getElementById("resultFullscreenBtn");
const importFileInput = document.getElementById("importFileInput");
const message = document.getElementById("message");

function showMessage(text, type) {
  message.textContent = text;
  message.className = `message show ${type}`;
}

function hideMessage() {
  message.textContent = "";
  message.className = "message";
}

function setConnected(connected) {
  document.getElementById("runBtn").disabled = !connected;
  document.getElementById("refreshMetaBtn").disabled = !connected;
  document.getElementById("removeDbBtn").disabled = !connected;
  importFileInput.disabled = !connected;
  sqlInput.disabled = !connected;
}

function setResultFullscreen(on) {
  resultSection.classList.toggle("is-fullscreen", on);
  resultFullscreenBtn.textContent = on ? "退出全屏" : "全屏";
  document.body.classList.toggle("sqlite-result-fullscreen-open", on);
}

function toggleResultFullscreen() {
  setResultFullscreen(!resultSection.classList.contains("is-fullscreen"));
}

async function api(path, options = {}) {
  const res = await fetch(API + path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "请求失败");
  return data;
}

function formatDbLabel(db) {
  const size = formatSize(db.size || 0);
  if (db.source_type === "temp") {
    const parts = [db.filename || "临时库", size];
    if (db.table_count > 0) {
      parts.push(`${db.table_count} 表`);
    }
    if (db.summary) {
      parts.push(db.summary);
    }
    return parts.join(" · ");
  }
  if (db.source_type === "local" && db.path) {
    return `${db.filename} · ${size}`;
  }
  return `${db.filename} (${size})`;
}

function updateDbInfo(dbId) {
  const dbInfo = document.getElementById("dbInfo");
  if (!dbId) {
    dbInfo.textContent = "";
    return;
  }
  const db = databasesCache.find((item) => item.db_id === dbId);
  if (!db) {
    dbInfo.textContent = "";
    return;
  }
  if (db.source_type === "temp") {
    dbInfo.textContent = db.summary ? `${db.filename} · ${db.summary}` : (db.filename || "临时库");
    dbInfo.title = dbInfo.textContent;
    return;
  }
  if (db.source_type === "local" && db.path) {
    dbInfo.textContent = db.path;
    dbInfo.title = db.path;
    return;
  }
  dbInfo.textContent = db.filename || "";
  dbInfo.title = db.filename || "";
}

async function loadDatabases(selectId) {
  const data = await api("/databases");
  databasesCache = data.databases || [];
  dbSelect.innerHTML = '<option value="">— 选择已链接的数据库 —</option>';
  databasesCache.forEach((db) => {
    const opt = document.createElement("option");
    opt.value = db.db_id;
    opt.textContent = formatDbLabel(db);
    dbSelect.appendChild(opt);
  });
  if (selectId) dbSelect.value = selectId;
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1024 / 1024).toFixed(1) + " MB";
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function selectDatabase(dbId) {
  currentDbId = dbId || null;
  if (!currentDbId) {
    metadataCache = null;
    metaTree.classList.add("hidden");
    metaEmpty.classList.remove("hidden");
    updateDbInfo(null);
    setConnected(false);
    loadHistory();
    return;
  }
  setConnected(true);
  updateDbInfo(currentDbId);
  const db = databasesCache.find((item) => item.db_id === currentDbId);
  if (db && db.path) {
    dbPathInput.value = db.path;
  }
  await loadMetadata();
  await loadHistory();
}

async function loadMetadata() {
  if (!currentDbId) return;
  try {
    metadataCache = await api(`/databases/${currentDbId}/metadata`);
    renderMetadata(metadataCache);
    updateDbInfo(currentDbId);
  } catch (e) {
    showMessage(e.message, "error");
  }
}

function tableQueryName(tableName, schema) {
  if (!schema || schema === "main") {
    return `"${tableName.replace(/"/g, '""')}"`;
  }
  return `"${schema.replace(/"/g, '""')}"."${tableName.replace(/"/g, '""')}"`;
}

function renderTableGroup(title, tables, meta, options = {}) {
  const { temporary = false, schemaPrefix = "" } = options;
  if (!tables.length) return "";

  let html = `<div class="meta-group"><div class="meta-group-title">${title} (${tables.length})</div>`;
  tables.forEach((t, idx) => {
    const schema = meta.table_schemas[t.name] || {};
    const cols = schema.columns || [];
    const rowCount = schema.row_count != null ? schema.row_count : "?";
    const qualified = schema.qualified_name || t.name;
    const groupKey = `${schemaPrefix}${temporary ? "imp" : "tbl"}-${idx}`;
    const tempBadge = temporary ? '<span class="meta-badge meta-badge-temp">临时</span>' : "";

    html += `<div class="meta-table-item${temporary ? " meta-table-temp" : ""}">
      <div class="meta-table-head" data-idx="${groupKey}">
        <span class="meta-icon">${temporary ? "📥" : "📋"}</span>
        <span class="meta-name" title="${escapeHtml(qualified)}">${escapeHtml(t.name)}</span>
        ${tempBadge}
        <span class="meta-badge">${rowCount} 行</span>
      </div>
      <div class="meta-columns hidden" id="meta-cols-${groupKey}">`;
    cols.forEach((c) => {
      const pk = c.pk ? " 🔑" : "";
      const nn = c.notnull ? " NOT NULL" : "";
      html += `<div class="meta-col" title="${escapeHtml(t.name)}.${escapeHtml(c.name)}">
        ${escapeHtml(c.name)} <span class="meta-col-type">${escapeHtml(c.type || "TEXT")}${pk}${nn}</span>
      </div>`;
    });
    html += `<button class="btn btn-secondary btn-sm meta-preview-btn" data-table="${escapeHtml(t.name)}" data-schema="${escapeHtml(schema.schema || schemaPrefix || "")}">预览数据</button>`;
    if (temporary) {
      html += `<button class="btn btn-danger btn-sm meta-drop-import-btn" data-table="${escapeHtml(t.name)}">删除临时表</button>`;
    }
    html += `</div></div>`;
  });
  html += `</div>`;
  return html;
}

function renderMetadata(meta) {
  metaEmpty.classList.add("hidden");
  metaTree.classList.remove("hidden");

  let html = "";

  const db = databasesCache.find((item) => item.db_id === currentDbId);
  const isTempDb = db && db.source_type === "temp";

  if (meta.tables.length) {
    if (isTempDb) {
      html += renderTableGroup("导入临时表", meta.tables, meta, { temporary: true });
    } else {
      html += renderTableGroup("表", meta.tables, meta);
    }
  }

  if (meta.imported_tables && meta.imported_tables.length) {
    html += renderTableGroup("导入临时表", meta.imported_tables, meta, { temporary: true, schemaPrefix: "imported" });
  }

  if (meta.views.length) {
    html += `<div class="meta-group"><div class="meta-group-title">视图 (${meta.views.length})</div>`;
    meta.views.forEach((v, idx) => {
      html += `<div class="meta-view-item" data-view-idx="${idx}">${escapeHtml(v.name)}</div>`;
    });
    html += `</div>`;
  }

  if (meta.indexes.length) {
    html += `<div class="meta-group"><div class="meta-group-title">索引 (${meta.indexes.length})</div>`;
    meta.indexes.forEach((idx) => {
      html += `<div class="meta-index-item">${escapeHtml(idx.name)}</div>`;
    });
    html += `</div>`;
  }

  metaTree.innerHTML = html || '<div class="sqlite-meta-empty">无用户对象</div>';

  metaTree.querySelectorAll(".meta-table-head").forEach((el) => {
    el.addEventListener("click", () => {
      const cols = document.getElementById(`meta-cols-${el.dataset.idx}`);
      if (cols) cols.classList.toggle("hidden");
    });
  });

  metaTree.querySelectorAll(".meta-preview-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const table = btn.dataset.table;
      const schema = btn.dataset.schema;
      sqlInput.value = `SELECT * FROM ${tableQueryName(table, schema)} LIMIT 100;`;
      runQuery();
    });
  });

  metaTree.querySelectorAll(".meta-drop-import-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const table = btn.dataset.table;
      if (!confirm(`确定删除临时表 ${table}？`)) return;
      try {
        await api(`/databases/${currentDbId}/import/${encodeURIComponent(table)}`, { method: "DELETE" });
        await loadMetadata();
        await loadDatabases(currentDbId);
        showMessage(`已删除临时表 ${table}`, "success");
      } catch (err) {
        showMessage(err.message, "error");
      }
    });
  });

  metaTree.querySelectorAll(".meta-view-item").forEach((el) => {
    el.addEventListener("click", () => {
      const view = meta.views[parseInt(el.dataset.viewIdx, 10)].name;
      sqlInput.value = `SELECT * FROM "${view.replace(/"/g, '""')}" LIMIT 100;`;
    });
  });
}

function renderResult(data) {
  resultMsg.textContent = `${data.message} · ${data.duration_ms} ms`;

  if (!data.columns || !data.columns.length) {
    resultWrap.innerHTML = `<div class="sqlite-result-empty">${escapeHtml(data.message)}</div>`;
    return;
  }

  let html = '<div class="sqlite-table-scroll"><table class="sqlite-result-table"><thead><tr>';
  data.columns.forEach((col) => {
    html += `<th>${escapeHtml(String(col))}</th>`;
  });
  html += "</tr></thead><tbody>";

  if (!data.rows.length) {
    html += `<tr><td colspan="${data.columns.length}" class="sqlite-no-rows">无数据</td></tr>`;
  } else {
    data.rows.forEach((row) => {
      html += "<tr>";
      row.forEach((cell) => {
        const val = cell === null ? "NULL" : String(cell);
        const cls = cell === null ? "cell-null" : "";
        html += `<td class="${cls}">${escapeHtml(val)}</td>`;
      });
      html += "</tr>";
    });
  }
  html += "</tbody></table></div>";
  if (data.truncated) {
    html += '<p class="sqlite-truncated-hint">结果已截断，最多显示 1000 行</p>';
  }
  resultWrap.innerHTML = html;
}

async function runQuery() {
  if (!currentDbId || !sqlInput.value.trim()) return;
  hideMessage();
  resultMsg.textContent = "执行中...";
  try {
    const data = await api(`/databases/${currentDbId}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sql: sqlInput.value }),
    });
    renderResult(data);
    await loadHistory();
    showMessage("执行成功", "success");
  } catch (e) {
    resultWrap.innerHTML = `<div class="sqlite-result-error">${escapeHtml(e.message)}</div>`;
    resultMsg.textContent = "";
    await loadHistory();
    showMessage(e.message, "error");
  }
}

async function loadHistory() {
  const path = currentDbId ? `/history?db_id=${currentDbId}&limit=50` : "/history?limit=50";
  try {
    const data = await api(path);
    if (!data.records.length) {
      historyList.innerHTML = '<div class="sqlite-meta-empty">暂无历史记录</div>';
      return;
    }
    historyList.innerHTML = "";
    data.records.forEach((r) => {
      const status = r.success ? "success" : "error";
      const info = r.success
        ? `${r.row_count || r.affected_rows} 行 · ${r.duration_ms}ms`
        : (r.error || "失败");
      const sqlPreview = r.sql.length > 80 ? r.sql.slice(0, 80) + "..." : r.sql;

      const item = document.createElement("div");
      item.className = `history-item history-${status}`;
      item.title = r.sql;
      item.innerHTML = `
        <div class="history-meta">${escapeHtml(r.executed_at)} · ${escapeHtml(String(info))}</div>
        <div class="history-sql">${escapeHtml(sqlPreview)}</div>`;
      item.addEventListener("click", () => { sqlInput.value = r.sql; });
      historyList.appendChild(item);
    });
  } catch (_) {}
}

async function linkDatabase() {
  const path = dbPathInput.value.trim();
  if (!path) {
    showMessage("请输入本地数据库文件路径", "error");
    return;
  }
  hideMessage();
  try {
    showMessage("正在链接...", "info");
    const data = await api("/link", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    await loadDatabases(data.db_id);
    await selectDatabase(data.db_id);
    showMessage(`已链接 ${data.path || data.filename}`, "success");
  } catch (err) {
    showMessage(err.message, "error");
  }
}

document.getElementById("linkDbBtn").addEventListener("click", linkDatabase);

document.getElementById("tempSessionBtn").addEventListener("click", async () => {
  hideMessage();
  try {
    showMessage("正在创建临时库...", "info");
    const data = await api("/temp-session", { method: "POST" });
    await loadDatabases(data.db_id);
    await selectDatabase(data.db_id);
    showMessage("已创建临时库，可导入 CSV/Excel 后查询", "success");
  } catch (err) {
    showMessage(err.message, "error");
  }
});

importFileInput.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file || !currentDbId) return;

  hideMessage();
  const form = new FormData();
  form.append("file", file);

  try {
    showMessage(`正在导入 ${file.name}...`, "info");
    const data = await api(`/databases/${currentDbId}/import`, {
      method: "POST",
      body: form,
    });
    await loadDatabases(currentDbId);
    await loadMetadata();
    sqlInput.value = `SELECT * FROM ${tableQueryName(data.table_name, data.schema)} LIMIT 100;`;
    showMessage(data.message, "success");
  } catch (err) {
    showMessage(err.message, "error");
  }
});

dbPathInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    linkDatabase();
  }
});

dbSelect.addEventListener("change", () => selectDatabase(dbSelect.value || null));

document.getElementById("refreshMetaBtn").addEventListener("click", loadMetadata);

document.getElementById("removeDbBtn").addEventListener("click", async () => {
  if (!currentDbId) return;
  const db = databasesCache.find((item) => item.db_id === currentDbId);
  const isLocal = db && db.source_type === "local";
  const tip = db && db.source_type === "temp"
    ? "确定移除此临时库？导入的数据将被删除。"
    : isLocal
    ? "确定移除此本地数据库连接？不会删除磁盘上的文件，但会清除已导入的临时表。"
    : "确定删除此数据库副本？";
  if (!confirm(tip)) return;
  try {
    await api(`/databases/${currentDbId}`, { method: "DELETE" });
    currentDbId = null;
    sqlInput.value = "";
    resultWrap.innerHTML = '<div class="sqlite-result-empty">执行 SQL 后在此显示结果</div>';
    await loadDatabases();
    await selectDatabase(null);
    showMessage(isLocal ? "已移除连接" : "已删除", "success");
  } catch (e) {
    showMessage(e.message, "error");
  }
});

document.getElementById("runBtn").addEventListener("click", runQuery);
document.getElementById("clearSqlBtn").addEventListener("click", () => { sqlInput.value = ""; });
resultFullscreenBtn.addEventListener("click", toggleResultFullscreen);

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && resultSection.classList.contains("is-fullscreen")) {
    setResultFullscreen(false);
  }
});

sqlInput.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    runQuery();
  }
});

document.getElementById("clearHistoryBtn").addEventListener("click", async () => {
  if (!confirm("确定清除历史记录？")) return;
  const q = currentDbId ? `?db_id=${currentDbId}` : "";
  await api(`/history${q}`, { method: "DELETE" });
  await loadHistory();
});

loadDatabases().then(() => loadHistory());
