const API = "/api/tools/rss-manager";

const feedList = document.getElementById("feedList");
const itemList = document.getElementById("itemList");
const contentTitle = document.getElementById("contentTitle");
const statusProgress = document.getElementById("statusProgress");
const editId = document.getElementById("editId");
const feedName = document.getElementById("feedName");
const feedUrl = document.getElementById("feedUrl");
const feedCategory = document.getElementById("feedCategory");
const presetCategory = document.getElementById("presetCategory");
const presetInfo = document.getElementById("presetInfo");
const saveBtn = document.getElementById("saveBtn");
const cancelBtn = document.getElementById("cancelBtn");
const message = document.getElementById("message");

let feedsCache = [];
let activeFeedId = null;
let presetsCache = null;
let statusCheckGen = 0;
let activeStatusStream = null;

const ICON_EDIT =
  '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>';
const ICON_DELETE =
  '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>';

function showMessage(text, type) {
  message.textContent = text;
  message.className = `message show ${type}`;
}

function hideMessage() {
  message.textContent = "";
  message.className = "message";
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function api(path, options = {}) {
  const res = await fetch(API + path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "请求失败");
  return data;
}

function resetForm() {
  editId.value = "";
  feedName.value = "";
  feedUrl.value = "";
  feedCategory.value = "默认";
  saveBtn.textContent = "添加";
  cancelBtn.classList.add("hidden");
}

function startEdit(feed) {
  editId.value = feed.id;
  feedName.value = feed.name;
  feedUrl.value = feed.url;
  feedCategory.value = feed.category || "默认";
  saveBtn.textContent = "保存";
  cancelBtn.classList.remove("hidden");
  feedName.focus();
}

function statusClass(feed) {
  if (feed.status === "ok") return "ok";
  if (feed.status === "error") return "error";
  if (feed.status === "checking") return "checking";
  return "unknown";
}

function statusTip(feed) {
  if (feed.status === "ok") return feed.status_message || "连接正常";
  if (feed.status === "error") return feed.status_message || "异常";
  if (feed.status === "checking") return "检测中...";
  return "未知状态";
}

function setStatusProgress(done, total) {
  if (!statusProgress) return;
  if (done == null || total == null) {
    statusProgress.textContent = "";
    statusProgress.classList.add("hidden");
    return;
  }
  statusProgress.textContent = `检测中 ${done}/${total}`;
  statusProgress.classList.remove("hidden");
}

function updateFeedStatusInDom(feed) {
  const btn = feedList.querySelector(`.rss-feed-main[data-id="${feed.id}"]`);
  if (!btn) return;
  const dot = btn.querySelector(".rss-dot");
  if (dot) dot.className = `rss-dot ${statusClass(feed)}`;
  btn.title = statusTip(feed);
}

function renderFeedList() {
  if (!feedsCache.length) {
    feedList.innerHTML = '<li class="rss-empty">暂无订阅源，可导入内置数据源或手动添加</li>';
    return;
  }

  feedList.innerHTML = "";
  feedsCache.forEach((feed) => {
    const li = document.createElement("li");
    li.className = "rss-feed-item" + (feed.id === activeFeedId ? " active" : "");
    const cat = feed.category || "默认";

    li.innerHTML = `
      <button type="button" class="rss-feed-main" data-id="${feed.id}" title="${escapeHtml(statusTip(feed))}">
        <i class="rss-dot ${statusClass(feed)}"></i>
        <span class="rss-feed-name">${escapeHtml(feed.name)}</span>
        <span class="rss-feed-cat">${escapeHtml(cat)}</span>
      </button>
      <div class="rss-feed-actions">
        <button type="button" class="rss-icon-btn rss-edit-btn" title="编辑">${ICON_EDIT}</button>
        <button type="button" class="rss-icon-btn rss-icon-btn-danger rss-del-btn" title="删除">${ICON_DELETE}</button>
      </div>`;

    li.querySelector(".rss-feed-main").addEventListener("click", () => openFeed(feed.id));
    li.querySelector(".rss-edit-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      startEdit(feed);
    });
    li.querySelector(".rss-del-btn").addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm(`确定删除「${feed.name}」？`)) return;
      await api(`/feeds/${feed.id}`, { method: "DELETE" });
      if (activeFeedId === feed.id) {
        activeFeedId = null;
        contentTitle.textContent = "选择左侧订阅源查看内容";
        itemList.innerHTML = '<div class="rss-empty">点击订阅源名称加载文章</div>';
      }
      await loadFeeds();
      showMessage("已删除", "success");
    });

    feedList.appendChild(li);
  });
}

function renderItems(data, feedNameText) {
  contentTitle.textContent = data.channel_title || feedNameText || "文章内容";
  if (!data.items || !data.items.length) {
    itemList.innerHTML = '<div class="rss-empty">暂无文章</div>';
    return;
  }

  itemList.innerHTML = "";
  data.items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "rss-item";
    const link = item.link
      ? `<a href="${escapeHtml(item.link)}" target="_blank" rel="noopener">原文</a>`
      : "";
    card.innerHTML = `
      <h3 class="rss-item-title">${escapeHtml(item.title)}</h3>
      <div class="rss-item-meta">${escapeHtml(item.published || "")} ${link}</div>
      <p class="rss-item-summary">${escapeHtml(item.summary || "")}</p>`;
    itemList.appendChild(card);
  });
}

function closeStatusStream() {
  if (activeStatusStream) {
    activeStatusStream.close();
    activeStatusStream = null;
  }
}

async function checkAllFeedStatuses() {
  const total = feedsCache.length;
  if (!total) {
    setStatusProgress(null);
    return;
  }

  const gen = ++statusCheckGen;
  closeStatusStream();
  feedsCache = feedsCache.map((f) => ({ ...f, status: "checking" }));
  renderFeedList();
  setStatusProgress(0, total);

  return new Promise((resolve, reject) => {
    const es = new EventSource(`${API}/feeds/status-stream`);
    activeStatusStream = es;

    es.onmessage = (event) => {
      if (gen !== statusCheckGen) return;
      let data;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }
      if (data.complete) {
        closeStatusStream();
        setStatusProgress(null);
        resolve();
        return;
      }
      if (data.feed) {
        const idx = feedsCache.findIndex((f) => f.id === data.feed.id);
        if (idx >= 0) {
          feedsCache[idx] = { ...feedsCache[idx], ...data.feed };
          updateFeedStatusInDom(feedsCache[idx]);
        }
        setStatusProgress(data.done, data.total);
      }
    };

    es.onerror = () => {
      if (gen !== statusCheckGen) return;
      closeStatusStream();
      setStatusProgress(null);
      reject(new Error("状态检测连接中断"));
    };
  });
}

async function loadFeeds({ checkStatus = true } = {}) {
  hideMessage();
  try {
    const data = await api("/feeds?with_status=false");
    feedsCache = (data.feeds || []).map((f) => ({
      ...f,
      status: checkStatus ? "checking" : f.status || "unknown",
    }));
    renderFeedList();
    if (checkStatus && feedsCache.length) {
      await checkAllFeedStatuses();
    } else {
      setStatusProgress(null);
    }
  } catch (err) {
    feedList.innerHTML = `<li class="rss-empty rss-error">${escapeHtml(err.message)}</li>`;
    showMessage(err.message, "error");
  }
}

async function loadPresets() {
  presetsCache = await api("/presets");
  presetCategory.innerHTML = '<option value="">全部分类</option>';
  (presetsCache.categories || []).forEach((cat) => {
    const opt = document.createElement("option");
    opt.value = cat;
    const count = (presetsCache.groups[cat] || []).length;
    opt.textContent = `${cat}（${count}）`;
    presetCategory.appendChild(opt);
  });
  presetInfo.textContent = `共 ${presetsCache.total || 0} 个预设源`;
}

async function importPresets(category) {
  const label = category || "全部";
  if (!confirm(`确定导入「${label}」预设订阅源？已存在的 URL 会自动跳过。`)) return;
  showMessage("正在导入...", "info");
  const data = await api("/presets/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category: category || null }),
  });
  await loadFeeds();
  showMessage(`导入完成：新增 ${data.added} 个，跳过 ${data.skipped} 个`, "success");
}

async function openFeed(feedId) {
  activeFeedId = feedId;
  renderFeedList();
  const feed = feedsCache.find((f) => f.id === feedId);
  contentTitle.textContent = "加载中...";
  itemList.innerHTML = '<div class="rss-empty">加载中...</div>';
  try {
    const data = await api(`/feeds/${feedId}/items`);
    renderItems(data, feed ? feed.name : "");
  } catch (err) {
    itemList.innerHTML = `<div class="rss-empty rss-error">${escapeHtml(err.message)}</div>`;
    showMessage(err.message, "error");
  }
}

saveBtn.addEventListener("click", async () => {
  hideMessage();
  const body = {
    name: feedName.value.trim(),
    url: feedUrl.value.trim(),
    category: feedCategory.value.trim() || "默认",
  };
  if (!body.name || !body.url) {
    showMessage("请填写名称和 RSS 地址", "error");
    return;
  }
  try {
    const id = editId.value;
    if (id) {
      await api(`/feeds/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      showMessage("已保存", "success");
    } else {
      await api("/feeds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      showMessage("已添加", "success");
    }
    resetForm();
    await loadFeeds();
  } catch (err) {
    showMessage(err.message, "error");
  }
});

cancelBtn.addEventListener("click", resetForm);

document.getElementById("refreshBtn").addEventListener("click", async () => {
  try {
    showMessage("正在检测所有订阅源状态...", "info");
    await checkAllFeedStatuses();
    showMessage("状态已刷新", "success");
  } catch (err) {
    showMessage(err.message, "error");
  }
});

document.getElementById("importPresetBtn").addEventListener("click", async () => {
  try {
    await importPresets(presetCategory.value || null);
  } catch (err) {
    showMessage(err.message, "error");
  }
});

document.getElementById("importAllPresetBtn").addEventListener("click", async () => {
  try {
    await importPresets(null);
  } catch (err) {
    showMessage(err.message, "error");
  }
});

feedCategory.value = "默认";
loadPresets();
loadFeeds();
