async function loadAppInfo() {
  try {
    const res = await fetch("/api/app");
    if (!res.ok) return;
    const info = await res.json();
    document.getElementById("appTitle").textContent = info.title_zh || "我的工具箱";
    document.getElementById("appTitleEn").textContent = info.title_en || "MyTools";
    document.getElementById("appDesc").textContent = info.description || "";
    document.title = `${info.title_zh || "我的工具箱"} - ${info.title_en || "MyTools"}`;
  } catch (_) {
    /* 静默失败，使用默认标题 */
  }
}

function renderToolCard(tool) {
  return `
    <a class="tool-card" href="${tool.route}">
      <div class="icon">${tool.icon || "🔧"}</div>
      <h3>${escapeHtml(tool.name_zh)}</h3>
      <div class="name-en">${escapeHtml(tool.name_en || "")}</div>
      <p>${escapeHtml(tool.description || "")}</p>
    </a>
  `;
}

async function loadTools() {
  const grid = document.getElementById("toolsGrid");
  try {
    const res = await fetch("/api/tools");
    if (!res.ok) throw new Error("加载失败");
    const data = await res.json();
    const tools = data.tools || [];
    const groups = data.groups || [];

    if (tools.length === 0) {
      grid.innerHTML = '<div class="empty-state">暂无可用工具</div>';
      return;
    }

    const toolsByGroup = {};
    tools.forEach((tool) => {
      const gid = tool.group || "other";
      if (!toolsByGroup[gid]) toolsByGroup[gid] = [];
      toolsByGroup[gid].push(tool);
    });

    const orderedGroups = groups.length
      ? groups.filter((g) => toolsByGroup[g.id]?.length)
      : [{ id: "other", name_zh: "工具列表", icon: "🔧" }];

    if (!groups.length && toolsByGroup.other) {
      grid.innerHTML = tools.map(renderToolCard).join("");
      return;
    }

    grid.innerHTML = orderedGroups
      .map((group) => {
        const items = toolsByGroup[group.id] || [];
        if (!items.length) return "";
        return `
          <section class="tool-group">
            <h3 class="tool-group-title">${group.icon || ""} ${escapeHtml(group.name_zh || group.id)}</h3>
            <div class="tools-grid">${items.map(renderToolCard).join("")}</div>
          </section>
        `;
      })
      .join("");

    const ungrouped = toolsByGroup.other;
    if (ungrouped?.length && groups.length) {
      grid.innerHTML += `
        <section class="tool-group">
          <h3 class="tool-group-title">🔧 其他</h3>
          <div class="tools-grid">${ungrouped.map(renderToolCard).join("")}</div>
        </section>
      `;
    }
  } catch (e) {
    grid.innerHTML = `<div class="empty-state">加载工具列表失败: ${escapeHtml(e.message)}</div>`;
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

loadAppInfo();
loadTools();
