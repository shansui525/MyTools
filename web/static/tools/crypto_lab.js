const API_BASE = "/api/tools/crypto-lab";

let catalog = null;
let currentCategory = "encoding";
let currentAlgoId = null;
let currentAction = null;
let activeCodeTab = "python";

const FIELD_LABELS = {
  key: "密钥 (Key)",
  iv: "初始向量 (IV)",
  aad: "附加认证数据 (AAD)",
  public_key: "公钥",
  private_key: "私钥",
};

const ACTION_LABELS = {
  encode: "编码",
  decode: "解码",
  hash: "计算哈希",
  encrypt: "加密",
  decrypt: "解密",
};

const EXAMPLES = {
  base64: { text: "Hello, 加解密实验室!" },
  "base64url": { text: "JWT.payload.data" },
  hex: { text: "48656c6c6f", input_format: "hex", action: "decode" },
  url: { text: "name=张三&city=北京" },
  md5: { text: "hello" },
  sha256: { text: "hello" },
  sm3: { text: "hello" },
  "hmac-sha256": { text: "message", key: "secret-key" },
  "aes-256-cbc": {
    text: "hello world",
    key: "12345678901234567890123456789012",
    iv: "1234567890123456",
  },
  "aes-128-cbc": {
    text: "hello world",
    key: "1234567890123456",
    iv: "1234567890123456",
  },
  "aes-256-ecb": { text: "hello world", key: "12345678901234567890123456789012" },
  "sm4-ecb": { text: "hello", key: "0123456789abcdef" },
  "sm4-cbc": { text: "hello", key: "0123456789abcdef", iv: "0123456789abcdef" },
};

const $ = (id) => document.getElementById(id);

function showMessage(text, type) {
  const el = $("message");
  el.textContent = text;
  el.className = `message show ${type}`;
}

function hideMessage() {
  $("message").textContent = "";
  $("message").className = "message";
}

function getCurrentAlgo() {
  if (!catalog || !currentAlgoId) return null;
  return catalog.algorithms.find((a) => a.id === currentAlgoId);
}

function filteredAlgorithms() {
  if (!catalog) return [];
  return catalog.algorithms.filter((a) => a.category === currentCategory);
}

function renderCategories() {
  const container = $("categoryList");
  container.innerHTML = "";
  catalog.categories.forEach((cat) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `crypto-cat-btn${cat.id === currentCategory ? " active" : ""}`;
    btn.textContent = `${cat.icon} ${cat.name}`;
    btn.addEventListener("click", () => {
      currentCategory = cat.id;
      renderCategories();
      renderAlgoList();
      const list = filteredAlgorithms();
      if (list.length) selectAlgorithm(list[0].id);
    });
    container.appendChild(btn);
  });
}

function renderAlgoList() {
  const container = $("algoList");
  container.innerHTML = "";
  filteredAlgorithms().forEach((algo) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `crypto-algo-btn${algo.id === currentAlgoId ? " active" : ""}`;
    btn.textContent = algo.name;
    if (algo.requires && !catalog.gmssl_available) {
      btn.classList.add("disabled");
      btn.title = "需要安装 gmssl";
    }
    btn.addEventListener("click", () => selectAlgorithm(algo.id));
    container.appendChild(btn);
  });
}

function renderAlgoInfo(algo) {
  const info = $("algoInfo");
  if (!algo) {
    info.innerHTML = '<div class="crypto-info-empty">请从左侧选择算法</div>';
    return;
  }
  const note = algo.note ? `<p class="crypto-note">⚠️ ${escapeHtml(algo.note)}</p>` : "";
  info.innerHTML = `
    <h3 class="crypto-info-name">${escapeHtml(algo.name)}</h3>
    <p class="crypto-info-intro">${escapeHtml(algo.intro)}</p>
    <div class="crypto-pkg-row">
      <span class="crypto-pkg-label">Python</span>
      <code>${escapeHtml(algo.python_pkg)}</code>
    </div>
    <div class="crypto-pkg-row">
      <span class="crypto-pkg-label">JavaScript</span>
      <code>${escapeHtml(algo.js_pkg)}</code>
    </div>
    ${note}
  `;
}

function renderActions(algo) {
  const bar = $("actionBar");
  if (!algo) {
    bar.classList.add("hidden");
    bar.innerHTML = "";
    return;
  }
  bar.classList.remove("hidden");
  bar.innerHTML = "";
  algo.actions.forEach((action) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `crypto-action-btn${action === currentAction ? " active" : ""}`;
    btn.textContent = ACTION_LABELS[action] || action;
    btn.addEventListener("click", () => {
      currentAction = action;
      renderActions(algo);
      updateInputLabel();
    });
    bar.appendChild(btn);
  });
}

function renderParamForm(algo) {
  const form = $("paramForm");
  if (!algo || !algo.fields || !algo.fields.length) {
    form.classList.add("hidden");
    form.innerHTML = "";
    return;
  }
  form.classList.remove("hidden");
  form.innerHTML = algo.fields
    .map((field) => {
      const lenHint =
        field === "key" && algo.key_len
          ? ` (${algo.key_len} 字节)`
          : field === "iv" && algo.iv_len
            ? ` (${algo.iv_len} 字节)`
            : "";
      const isKey = field === "public_key" || field === "private_key";
      return `
        <label class="crypto-field">
          <span class="crypto-field-label">${FIELD_LABELS[field] || field}${lenHint}</span>
          <textarea id="field_${field}" class="crypto-field-input${isKey ? " crypto-key-input" : ""}" rows="${isKey ? 3 : 1}" placeholder="输入 ${FIELD_LABELS[field] || field}"></textarea>
        </label>
      `;
    })
    .join("");
}

function updateInputLabel() {
  const algo = getCurrentAlgo();
  if (!algo) {
    $("inputLabel").textContent = "输入";
    return;
  }
  if (currentAction === "hash") {
    $("inputLabel").textContent = "待哈希文本";
  } else if (currentAction === "encode" || currentAction === "encrypt") {
    $("inputLabel").textContent = "明文 / 原始数据";
  } else {
    $("inputLabel").textContent = "密文 / 编码数据";
  }
  const defaultFmt = algo.output_format || "hex";
  const outSel = $("outputFormat");
  if (currentAction === "decode" || currentAction === "decrypt") {
    $("inputFormat").value = defaultFmt === "text" ? "base64" : defaultFmt;
    outSel.value = "text";
  } else if (currentAction === "encode" || currentAction === "encrypt" || currentAction === "hash") {
    $("inputFormat").value = "text";
    outSel.value = defaultFmt;
  }
}

function updateGenKeysBtn(algo) {
  const btn = $("genKeysBtn");
  if (algo && (algo.id === "rsa-oaep" || algo.id === "sm2")) {
    btn.classList.remove("hidden");
  } else {
    btn.classList.add("hidden");
  }
}

function selectAlgorithm(algoId) {
  const algo = catalog.algorithms.find((a) => a.id === algoId);
  if (!algo) return;
  if (algo.requires && !catalog.gmssl_available) {
    showMessage("该算法需要后端安装 gmssl 包", "error");
    return;
  }
  currentAlgoId = algoId;
  currentAction = algo.actions[0];
  renderAlgoList();
  renderAlgoInfo(algo);
  renderActions(algo);
  renderParamForm(algo);
  updateInputLabel();
  updateGenKeysBtn(algo);
  hideMessage();
}

function collectParams() {
  const algo = getCurrentAlgo();
  const params = {
    algorithm_id: currentAlgoId,
    action: currentAction,
    text: $("textInput").value,
    input_format: $("inputFormat").value,
    output_format: $("outputFormat").value || undefined,
  };
  if (algo && algo.fields) {
    algo.fields.forEach((field) => {
      const el = document.getElementById(`field_${field}`);
      if (el) params[field] = el.value;
    });
  }
  return params;
}

function setFieldValues(values) {
  Object.entries(values).forEach(([key, val]) => {
    if (key === "text") {
      $("textInput").value = val;
      return;
    }
    if (key === "input_format") {
      $("inputFormat").value = val;
      return;
    }
    if (key === "action") {
      currentAction = val;
      const algo = getCurrentAlgo();
      if (algo) renderActions(algo);
      updateInputLabel();
      return;
    }
    const el = document.getElementById(`field_${key}`);
    if (el) el.value = val;
  });
}

function updateCodeOutput(data) {
  const code = activeCodeTab === "python" ? data.python_code : data.javascript_code;
  $("codeOutput").value = code || "";
}

async function runProcess() {
  hideMessage();
  if (!currentAlgoId) {
    showMessage("请先选择算法", "error");
    return;
  }
  const body = collectParams();
  try {
    const res = await fetch(`${API_BASE}/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "执行失败");
    $("resultOutput").value = data.result;
    updateCodeOutput(data);
    $("codeOutput").dataset.lastResponse = JSON.stringify(data);
    showMessage("执行成功", "success");
  } catch (e) {
    $("resultOutput").value = "";
    $("codeOutput").value = "";
    showMessage(e.message, "error");
  }
}

async function generateKeys() {
  hideMessage();
  const algo = getCurrentAlgo();
  if (!algo) return;
  try {
    const res = await fetch(`${API_BASE}/generate-keys?algorithm_id=${encodeURIComponent(algo.id)}`, {
      method: "POST",
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "生成失败");
    const pub = document.getElementById("field_public_key");
    const priv = document.getElementById("field_private_key");
    if (pub) pub.value = data.public_key;
    if (priv) priv.value = data.private_key;
    showMessage("密钥对已生成", "success");
  } catch (e) {
    showMessage(e.message, "error");
  }
}

function swapDirection() {
  const algo = getCurrentAlgo();
  if (!algo) return;
  const pairs = [
    ["encode", "decode"],
    ["encrypt", "decrypt"],
  ];
  for (const [a, b] of pairs) {
    if (currentAction === a && algo.actions.includes(b)) {
      currentAction = b;
      renderActions(algo);
      updateInputLabel();
      const tmp = $("textInput").value;
      $("textInput").value = $("resultOutput").value;
      $("resultOutput").value = tmp;
      return;
    }
    if (currentAction === b && algo.actions.includes(a)) {
      currentAction = a;
      renderActions(algo);
      updateInputLabel();
      const tmp = $("textInput").value;
      $("textInput").value = $("resultOutput").value;
      $("resultOutput").value = tmp;
      return;
    }
  }
  showMessage("当前算法不支持切换方向", "error");
}

function fillExample() {
  const algo = getCurrentAlgo();
  if (!algo) return;
  const ex = EXAMPLES[algo.id] || { text: "hello" };
  $("textInput").value = "";
  $("resultOutput").value = "";
  $("codeOutput").value = "";
  algo.fields?.forEach((f) => {
    const el = document.getElementById(`field_${f}`);
    if (el) el.value = "";
  });
  setFieldValues(ex);
  if (!ex.action) currentAction = algo.actions[0];
  renderActions(algo);
  updateInputLabel();
  hideMessage();
}

function clearAll() {
  $("textInput").value = "";
  $("resultOutput").value = "";
  $("codeOutput").value = "";
  $("inputFormat").value = "text";
  $("outputFormat").value = "";
  const algo = getCurrentAlgo();
  algo?.fields?.forEach((f) => {
    const el = document.getElementById(`field_${f}`);
    if (el) el.value = "";
  });
  hideMessage();
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function init() {
  try {
    const res = await fetch(`${API_BASE}/catalog`);
    catalog = await res.json();
    if (!catalog.gmssl_available) {
      $("gmsslWarn").classList.remove("hidden");
    }
    renderCategories();
    renderAlgoList();
    if (catalog.algorithms.length) {
      currentCategory = catalog.categories[0].id;
      renderCategories();
      selectAlgorithm(filteredAlgorithms()[0]?.id || catalog.algorithms[0].id);
    }
  } catch (e) {
    showMessage("加载算法目录失败: " + e.message, "error");
  }
}

document.querySelectorAll(".crypto-code-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".crypto-code-tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    activeCodeTab = tab.dataset.tab;
    const last = $("codeOutput").dataset.lastResponse;
    if (last) {
      try {
        updateCodeOutput(JSON.parse(last));
      } catch (_) { /* ignore */ }
    }
  });
});

$("runBtn").addEventListener("click", runProcess);
$("swapBtn").addEventListener("click", swapDirection);
$("exampleBtn").addEventListener("click", fillExample);
$("clearBtn").addEventListener("click", clearAll);
$("genKeysBtn").addEventListener("click", generateKeys);
$("copyResultBtn").addEventListener("click", () => {
  if (!$("resultOutput").value) return;
  navigator.clipboard.writeText($("resultOutput").value).then(
    () => showMessage("结果已复制", "success"),
    () => showMessage("复制失败", "error")
  );
});
$("copyCodeBtn").addEventListener("click", () => {
  if (!$("codeOutput").value) return;
  navigator.clipboard.writeText($("codeOutput").value).then(
    () => showMessage("代码已复制", "success"),
    () => showMessage("复制失败", "error")
  );
});

$("textInput").addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
    e.preventDefault();
    runProcess();
  }
});

init();
