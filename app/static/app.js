const state = {
  folder: "",
  candidates: [],
};

const folderInput = document.getElementById("folderInput");
const browseBtn = document.getElementById("browseBtn");
const openFolderBtn = document.getElementById("openFolderBtn");
const sizeFilterEnabled = document.getElementById("sizeFilterEnabled");
const thresholdInput = document.getElementById("thresholdInput");
const staticFilterEnabled = document.getElementById("staticFilterEnabled");
const staticThresholdInput = document.getElementById("staticThresholdInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const organizeBtn = document.getElementById("organizeBtn");
const deleteBtn = document.getElementById("deleteBtn");
const selectAll = document.getElementById("selectAll");
const deleteMode = document.getElementById("deleteMode");
const candidateTable = document.getElementById("candidateTable");
const logList = document.getElementById("logList");
const healthDot = document.getElementById("healthDot");
const healthText = document.getElementById("healthText");

const metrics = {
  videos: document.getElementById("metricVideos"),
  candidates: document.getElementById("metricCandidates"),
  organize: document.getElementById("metricOrganize"),
  candidateSize: document.getElementById("metricCandidateSize"),
};

async function api(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "请求失败");
  }
  return data;
}

function addLog(text, muted = false) {
  if (logList.firstElementChild?.classList.contains("muted")) {
    logList.innerHTML = "";
  }
  const item = document.createElement("div");
  item.className = `log-item${muted ? " muted" : ""}`;
  item.textContent = text;
  logList.prepend(item);
}

function formatSize(sizeMb) {
  return `${sizeMb.toFixed(3)} MB`;
}

function formatReasons(item) {
  const labels = {
    size: "小文件",
    static: "静态",
  };
  const reasons = item.candidate_reasons || [];
  const tags = reasons
    .map((reason) => `<span class="tag">${labels[reason] || escapeHtml(reason)}</span>`)
    .join("");
  const staticScore = item.static_score == null ? "" : `<span class="subtle">diff ${item.static_score.toFixed(3)}</span>`;
  return `<div class="reason-stack">${tags}${staticScore}</div>`;
}

function updateMetrics(summary) {
  metrics.videos.textContent = summary.video_count;
  metrics.candidates.textContent = summary.candidate_count;
  metrics.organize.textContent = summary.organize_count;
  metrics.candidateSize.textContent = `${summary.candidate_size_gb} GB`;
}

function folderValue() {
  return folderInput.value.trim();
}

function updateActionState() {
  const busy = state.busy;
  const hasFolder = Boolean(folderValue());
  browseBtn.disabled = busy;
  openFolderBtn.disabled = busy || !hasFolder;
  analyzeBtn.disabled = busy || !hasFolder;
  organizeBtn.disabled = busy || !hasFolder;
  deleteBtn.disabled = busy;
  thresholdInput.disabled = busy || !sizeFilterEnabled.checked;
  staticThresholdInput.disabled = busy || !staticFilterEnabled.checked;
}

function setBusy(isBusy) {
  state.busy = isBusy;
  updateActionState();
}

function selectedPaths() {
  return [...document.querySelectorAll(".candidate-check:checked")].map((input) => input.value);
}

function renderCandidates(items) {
  state.candidates = items;
  if (!items.length) {
    candidateTable.innerHTML = `
      <tr class="empty-row">
        <td colspan="6">没有命中筛选规则的视频</td>
      </tr>
    `;
    return;
  }

  candidateTable.innerHTML = items
    .map(
      (item) => `
        <tr>
          <td><input class="candidate-check" type="checkbox" value="${escapeHtml(item.path)}" /></td>
          <td>
            <div class="file-main">
              <div class="file-path">${escapeHtml(item.path)}</div>
              <div class="file-meta">${escapeHtml(item.modified_at)}</div>
            </div>
          </td>
          <td><span class="tag">${formatSize(item.size_mb)}</span></td>
          <td>${formatReasons(item)}</td>
          <td>${escapeHtml(item.inferred_date)}</td>
          <td><span class="mono">${escapeHtml(item.suggested_folder)}</span></td>
        </tr>
      `
    )
    .join("");
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      throw new Error();
    }
    healthDot.className = "status-dot ok";
    healthText.textContent = "本地服务已连接";
  } catch {
    healthDot.className = "status-dot bad";
    healthText.textContent = "本地服务不可用";
  }
}

async function analyze() {
  const folder = folderValue();
  const threshold = Number(thresholdInput.value);
  const staticThreshold = Number(staticThresholdInput.value);
  if (!folder) {
    addLog("请先输入要处理的视频目录", true);
    return;
  }

  setBusy(true);
  try {
    const result = await api("/api/analyze", {
      folder,
      threshold_mb: threshold,
      use_size_filter: sizeFilterEnabled.checked,
      use_static_filter: staticFilterEnabled.checked,
      static_threshold: staticThreshold,
    });
    state.folder = folder;
    updateMetrics(result.summary);
    renderCandidates(result.candidates);
    addLog(`分析完成：共 ${result.summary.video_count} 个视频，命中 ${result.summary.candidate_count} 个候选项。`);
  } catch (error) {
    addLog(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function organize() {
  const folder = folderValue();
  if (!folder) {
    addLog("请先输入要整理的视频目录", true);
    return;
  }

  setBusy(true);
  try {
    const result = await api("/api/organize", { folder });
    addLog(`整理完成：移动 ${result.moved_count} 个文件，跳过 ${result.skipped_count} 个已在目标目录的文件。`);
    await analyze();
  } catch (error) {
    addLog(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function pickFolder() {
  setBusy(true);
  try {
    const result = await api("/api/pick-folder", {});
    folderInput.value = result.folder;
    state.folder = result.folder;
    addLog(`已选择目录：${result.folder}`);
  } catch (error) {
    addLog(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function openFolder() {
  const folder = folderValue();
  if (!folder) {
    addLog("请先输入或选择视频目录", true);
    return;
  }
  setBusy(true);
  try {
    const result = await api("/api/open-folder", { folder });
    addLog(`已打开目录：${result.opened}`);
  } catch (error) {
    addLog(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function deleteSelected() {
  const folder = folderValue();
  const paths = selectedPaths();
  const mode = deleteMode.value;

  if (!folder) {
    addLog("请先输入目录并完成分析", true);
    return;
  }
  if (!paths.length) {
    addLog("请先勾选要处理的视频", true);
    return;
  }

  const modeText = mode === "delete" ? "永久删除" : "移动到回收目录";
  const confirmed = window.confirm(`确定要${modeText}这 ${paths.length} 个视频吗？`);
  if (!confirmed) {
    return;
  }

  setBusy(true);
  try {
    const result = await api("/api/delete", { folder, paths, mode });
    addLog(`处理完成：${modeText} ${result.deleted_count} 个，跳过 ${result.skipped_count} 个。`);
    await analyze();
  } catch (error) {
    addLog(error.message, true);
  } finally {
    setBusy(false);
  }
}

browseBtn.addEventListener("click", pickFolder);
openFolderBtn.addEventListener("click", openFolder);
folderInput.addEventListener("input", updateActionState);
analyzeBtn.addEventListener("click", analyze);
organizeBtn.addEventListener("click", organize);
deleteBtn.addEventListener("click", deleteSelected);
selectAll.addEventListener("change", (event) => {
  document.querySelectorAll(".candidate-check").forEach((input) => {
    input.checked = event.target.checked;
  });
});
sizeFilterEnabled.addEventListener("change", () => {
  updateActionState();
});
staticFilterEnabled.addEventListener("change", () => {
  updateActionState();
});

checkHealth();
updateActionState();
