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
const progressBand = document.getElementById("progressBand");
const progressTitle = document.getElementById("progressTitle");
const progressTime = document.getElementById("progressTime");
const progressBar = document.getElementById("progressBar");
const progressProcessed = document.getElementById("progressProcessed");
const progressRemaining = document.getElementById("progressRemaining");
const progressCandidates = document.getElementById("progressCandidates");
const progressFile = document.getElementById("progressFile");
const pauseAnalyzeBtn = document.getElementById("pauseAnalyzeBtn");
const stopAnalyzeBtn = document.getElementById("stopAnalyzeBtn");

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

function analysisPayload(folder) {
  return {
    folder,
    threshold_mb: Number(thresholdInput.value),
    use_size_filter: sizeFilterEnabled.checked,
    use_static_filter: staticFilterEnabled.checked,
    static_threshold: Number(staticThresholdInput.value),
  };
}

function folderValue() {
  return folderInput.value.trim();
}

function updateActionState() {
  const busy = state.busy;
  const hasFolder = Boolean(folderValue());
  const analyzing = Boolean(state.currentAnalyzeJob);
  const canPause = analyzing && !["stopping", "stopped", "done", "error"].includes(state.analyzeState);
  const canStop = analyzing && !["stopping", "stopped", "done", "error"].includes(state.analyzeState);
  browseBtn.disabled = busy;
  openFolderBtn.disabled = busy || !hasFolder;
  analyzeBtn.disabled = busy || !hasFolder;
  organizeBtn.disabled = busy || !hasFolder;
  deleteBtn.disabled = busy;
  pauseAnalyzeBtn.disabled = !canPause;
  stopAnalyzeBtn.disabled = !canStop;
  thresholdInput.disabled = busy || !sizeFilterEnabled.checked;
  staticThresholdInput.disabled = busy || !staticFilterEnabled.checked;
}

function setBusy(isBusy) {
  state.busy = isBusy;
  updateActionState();
}

function formatElapsed(seconds) {
  const total = Math.max(0, Math.floor(seconds || 0));
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  if (minutes > 0) {
    return `${minutes}分${rest}秒`;
  }
  return `${rest}秒`;
}

function renderProgress(status) {
  progressBand.hidden = false;
  const phaseText = {
    queued: "等待分析",
    collecting: "正在统计视频",
    analyzing: "正在分析视频",
    pausing: "正在暂停",
    paused: "已暂停",
    stopping: "正在停止",
    stopped: "已停止",
    done: "分析完成",
    error: "分析失败",
  }[status.phase] || "正在分析";
  const total = Number(status.total || 0);
  const processed = Number(status.processed || 0);
  const percent = total > 0 ? Math.min(100, Math.round((processed / total) * 100)) : 0;
  progressTitle.textContent = total > 0 ? `${phaseText} ${percent}%` : phaseText;
  progressTime.textContent = formatElapsed(status.elapsed_seconds);
  progressBar.style.width = `${percent}%`;
  progressProcessed.textContent = processed;
  progressRemaining.textContent = status.remaining ?? Math.max(total - processed, 0);
  progressCandidates.textContent = status.candidate_count || 0;
  const fallbackFileText = {
    done: "分析完成",
    stopped: "分析已停止",
    paused: "等待继续",
  }[status.state] || "等待文件";
  progressFile.textContent = status.current_path || fallbackFileText;
  state.analyzeState = status.state;
  pauseAnalyzeBtn.textContent = status.state === "paused" ? "继续" : "暂停";
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
  if (!folder) {
    addLog("请先输入要处理的视频目录", true);
    return;
  }

  if (state.analyzeTimer) {
    clearTimeout(state.analyzeTimer);
    state.analyzeTimer = null;
  }
  setBusy(true);
  try {
    renderCandidates([]);
    addLog("分析任务已启动");
    const status = await api("/api/analyze/start", analysisPayload(folder));
    state.folder = folder;
    state.currentAnalyzeJob = status.job_id;
    renderProgress(status);
    pollAnalyze(status.job_id);
  } catch (error) {
    addLog(error.message, true);
    state.currentAnalyzeJob = null;
    setBusy(false);
  }
}

async function pollAnalyze(jobId) {
  try {
    if (state.currentAnalyzeJob && jobId !== state.currentAnalyzeJob) {
      return;
    }
    const status = await api("/api/analyze/status", { job_id: jobId });
    if (state.currentAnalyzeJob && jobId !== state.currentAnalyzeJob) {
      return;
    }
    renderProgress(status);
    if (status.state === "done") {
      updateMetrics(status.result.summary);
      renderCandidates(status.result.candidates);
      addLog(`分析完成：共 ${status.result.summary.video_count} 个视频，命中 ${status.result.summary.candidate_count} 个候选项。`);
      state.currentAnalyzeJob = null;
      setBusy(false);
      return;
    }
    if (status.state === "error") {
      addLog(status.error || "分析失败", true);
      state.currentAnalyzeJob = null;
      setBusy(false);
      return;
    }
    if (status.state === "stopped") {
      updateMetrics(status.result.summary);
      renderCandidates(status.result.candidates);
      addLog(
        `分析已停止：已分析 ${status.processed}/${status.total} 个视频，当前命中 ${status.result.summary.candidate_count} 个候选项。`,
        true
      );
      state.currentAnalyzeJob = null;
      setBusy(false);
      return;
    }
    state.analyzeTimer = window.setTimeout(() => pollAnalyze(jobId), 700);
  } catch (error) {
    addLog(error.message, true);
    setBusy(false);
  }
}

async function controlAnalyze(action) {
  const jobId = state.currentAnalyzeJob;
  if (!jobId) {
    return;
  }
  try {
    const status = await api("/api/analyze/control", { job_id: jobId, action });
    renderProgress(status);
    if (action === "pause") {
      addLog("分析已请求暂停，当前视频处理完后会停住。");
    } else if (action === "resume") {
      addLog("分析已继续。");
    } else {
      addLog("分析已请求停止，当前视频处理完后结束。", true);
    }
  } catch (error) {
    addLog(error.message, true);
  }
}

async function organize() {
  const folder = folderValue();
  if (!folder) {
    addLog("请先输入要整理的视频目录", true);
    return;
  }

  setBusy(true);
  let shouldAnalyze = false;
  try {
    const result = await api("/api/organize", { folder });
    addLog(`整理完成：移动 ${result.moved_count} 个文件，跳过 ${result.skipped_count} 个已在目标目录的文件。`);
    shouldAnalyze = true;
  } catch (error) {
    addLog(error.message, true);
  } finally {
    setBusy(false);
  }
  if (shouldAnalyze) {
    await analyze();
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
  let shouldAnalyze = false;
  try {
    const result = await api("/api/delete", { folder, paths, mode });
    addLog(`处理完成：${modeText} ${result.deleted_count} 个，跳过 ${result.skipped_count} 个。`);
    shouldAnalyze = true;
  } catch (error) {
    addLog(error.message, true);
  } finally {
    setBusy(false);
  }
  if (shouldAnalyze) {
    await analyze();
  }
}

browseBtn.addEventListener("click", pickFolder);
openFolderBtn.addEventListener("click", openFolder);
folderInput.addEventListener("input", updateActionState);
analyzeBtn.addEventListener("click", analyze);
pauseAnalyzeBtn.addEventListener("click", () => {
  controlAnalyze(state.analyzeState === "paused" ? "resume" : "pause");
});
stopAnalyzeBtn.addEventListener("click", () => controlAnalyze("stop"));
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
