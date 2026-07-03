const state = {
  folder: "",
  candidates: [],
};

const folderInput = document.getElementById("folderInput");
const browseBtn = document.getElementById("browseBtn");
const openFolderBtn = document.getElementById("openFolderBtn");
const languageSelect = document.getElementById("languageSelect");
const policyPreset = document.getElementById("policyPreset");
const sizeFilterEnabled = document.getElementById("sizeFilterEnabled");
const thresholdInput = document.getElementById("thresholdInput");
const emptyFilterEnabled = document.getElementById("emptyFilterEnabled");
const retentionFilterEnabled = document.getElementById("retentionFilterEnabled");
const retentionDaysInput = document.getElementById("retentionDaysInput");
const staticFilterEnabled = document.getElementById("staticFilterEnabled");
const staticThresholdInput = document.getElementById("staticThresholdInput");
const organizeGranularity = document.getElementById("organizeGranularity");
const extensionInput = document.getElementById("extensionInput");
const protectedKeywordsInput = document.getElementById("protectedKeywordsInput");
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
  protected: document.getElementById("metricProtected"),
  formats: document.getElementById("metricFormats"),
};

const translations = {
  zh: {
    "app.title": "监控视频整理台",
    "health.checking": "本地服务检测中",
    "health.connected": "本地服务已连接",
    "health.unavailable": "本地服务不可用",
    "nav.subtitle": "本地整理工具",
    "nav.source": "目录与规则",
    "nav.results": "候选审核",
    "nav.activity": "操作记录",
    "nav.modeLabel": "默认模式",
    "nav.safeMode": "先回收后删除",
    "field.folder": "视频目录",
    "field.folderPlaceholder": "/Volumes/NAS/监控视频/卧室",
    "field.policy": "清理策略",
    "field.granularity": "整理粒度",
    "field.extensions": "视频格式",
    "field.protectedKeywords": "保护关键词",
    "button.browse": "选择目录",
    "button.openFolder": "打开目录",
    "button.analyze": "分析目录",
    "button.organize": "按年月日整理",
    "button.pause": "暂停",
    "button.resume": "继续",
    "button.stop": "停止",
    "button.processSelected": "处理选中项",
    "preset.balanced": "均衡清理",
    "preset.careful": "家庭谨慎",
    "preset.storage": "空间优先",
    "preset.archive": "只归档整理",
    "preset.custom": "自定义",
    "rule.size": "按大小筛选",
    "rule.empty": "空文件",
    "rule.emptyHint": "0 B / 录制失败",
    "rule.retention": "超过保留期",
    "rule.static": "首尾帧一致",
    "ruleReason.empty": "空文件",
    "ruleReason.old": "过期",
    "ruleReason.size": "小文件",
    "ruleReason.static": "静态",
    "unit.days": "天",
    "granularity.day": "按日归档",
    "granularity.month": "按月归档",
    "progress.ready": "准备分析",
    "progress.processed": "已分析",
    "progress.remaining": "剩余",
    "progress.candidates": "候选",
    "progress.waitingStart": "等待开始",
    "phase.queued": "等待分析",
    "phase.collecting": "正在统计视频",
    "phase.analyzing": "正在分析视频",
    "phase.pausing": "正在暂停",
    "phase.paused": "已暂停",
    "phase.stopping": "正在停止",
    "phase.stopped": "已停止",
    "phase.done": "分析完成",
    "phase.error": "分析失败",
    "file.done": "分析完成",
    "file.stopped": "分析已停止",
    "file.paused": "等待继续",
    "file.waiting": "等待文件",
    "metric.videos": "视频总数",
    "metric.candidates": "候选删除",
    "metric.organize": "待整理文件",
    "metric.candidateSize": "候选体积",
    "metric.protected": "受保护",
    "metric.formats": "格式种类",
    "panel.candidatesTitle": "候选视频",
    "panel.candidatesDesc": "命中筛选规则的视频会先列在这里，由你决定后续处理。",
    "panel.logTitle": "操作记录",
    "panel.logDesc": "每次整理、分析、删除都会留下简要回执。",
    "action.selectAll": "全选当前列表",
    "deleteMode.recycle": "移动到回收目录",
    "deleteMode.delete": "永久删除",
    "table.file": "文件",
    "table.formatDevice": "格式/设备",
    "table.size": "大小",
    "table.rule": "规则",
    "table.date": "推断日期",
    "table.suggestedFolder": "建议归档目录",
    "table.initial": "还没有分析结果",
    "table.empty": "没有命中筛选规则的视频",
    "table.analyzing": "正在分析目录",
    "log.waiting": "等待操作",
    "log.needAnalyzeFolder": "请先输入要处理的视频目录",
    "log.analyzeStarted": "分析任务已启动",
    "log.analyzeDone": "分析完成：共 {video_count} 个视频，命中 {candidate_count} 个候选项。",
    "log.analyzeFailed": "分析失败",
    "log.analyzeStopped": "分析已停止：已分析 {processed}/{total} 个视频，当前命中 {candidate_count} 个候选项。",
    "log.pauseRequested": "分析已请求暂停，当前视频处理完后会停住。",
    "log.resumed": "分析已继续。",
    "log.stopRequested": "分析已请求停止，当前视频处理完后结束。",
    "log.needOrganizeFolder": "请先输入要整理的视频目录",
    "log.organizeDone": "整理完成：移动 {moved_count} 个文件，跳过 {skipped_count} 个已在目标目录的文件。",
    "log.folderPicked": "已选择目录：{folder}",
    "log.needFolderToOpen": "请先输入或选择视频目录",
    "log.folderOpened": "已打开目录：{folder}",
    "log.needFolderAndAnalysis": "请先输入目录并完成分析",
    "log.needSelectedVideos": "请先勾选要处理的视频",
    "log.processDone": "处理完成：{mode} {deleted_count} 个，跳过 {skipped_count} 个。",
    "confirm.organize": "整理会把视频移动到当前设置的归档目录。确定要继续吗？",
    "confirm.delete": "确定要{mode}这 {count} 个视频吗？",
    "mode.delete": "永久删除",
    "mode.recycle": "移动到回收目录",
    "device.generic": "通用",
    "error.requestFailed": "请求失败",
  },
  en: {
    "app.title": "Surveillance Video Cleanup",
    "health.checking": "Checking local service",
    "health.connected": "Local service connected",
    "health.unavailable": "Local service unavailable",
    "nav.subtitle": "Local cleanup tool",
    "nav.source": "Source & Rules",
    "nav.results": "Review Queue",
    "nav.activity": "Activity",
    "nav.modeLabel": "Default mode",
    "nav.safeMode": "Recycle before delete",
    "field.folder": "Video Folder",
    "field.folderPlaceholder": "/Volumes/NAS/Surveillance/Bedroom",
    "field.policy": "Cleanup Policy",
    "field.granularity": "Archive By",
    "field.extensions": "Video Formats",
    "field.protectedKeywords": "Protected Keywords",
    "button.browse": "Choose Folder",
    "button.openFolder": "Open Folder",
    "button.analyze": "Analyze Folder",
    "button.organize": "Archive Videos",
    "button.pause": "Pause",
    "button.resume": "Resume",
    "button.stop": "Stop",
    "button.processSelected": "Process Selected",
    "preset.balanced": "Balanced",
    "preset.careful": "Careful Home",
    "preset.storage": "Storage First",
    "preset.archive": "Archive Only",
    "preset.custom": "Custom",
    "rule.size": "Size Filter",
    "rule.empty": "Empty Files",
    "rule.emptyHint": "0 B / failed recording",
    "rule.retention": "Older Than",
    "rule.static": "First/Last Frame Match",
    "ruleReason.empty": "Empty",
    "ruleReason.old": "Expired",
    "ruleReason.size": "Small",
    "ruleReason.static": "Static",
    "unit.days": "days",
    "granularity.day": "By Day",
    "granularity.month": "By Month",
    "progress.ready": "Ready to analyze",
    "progress.processed": "Processed",
    "progress.remaining": "Remaining",
    "progress.candidates": "Candidates",
    "progress.waitingStart": "Waiting to start",
    "phase.queued": "Queued",
    "phase.collecting": "Counting videos",
    "phase.analyzing": "Analyzing videos",
    "phase.pausing": "Pausing",
    "phase.paused": "Paused",
    "phase.stopping": "Stopping",
    "phase.stopped": "Stopped",
    "phase.done": "Analysis complete",
    "phase.error": "Analysis failed",
    "file.done": "Analysis complete",
    "file.stopped": "Analysis stopped",
    "file.paused": "Waiting to resume",
    "file.waiting": "Waiting for file",
    "metric.videos": "Total Videos",
    "metric.candidates": "Candidates",
    "metric.organize": "Need Archive",
    "metric.candidateSize": "Candidate Size",
    "metric.protected": "Protected",
    "metric.formats": "Formats",
    "panel.candidatesTitle": "Candidate Videos",
    "panel.candidatesDesc": "Videos that match cleanup rules appear here for review before action.",
    "panel.logTitle": "Activity Log",
    "panel.logDesc": "Analysis, archive, and cleanup actions leave a short receipt here.",
    "action.selectAll": "Select Current List",
    "deleteMode.recycle": "Move to Recycle Folder",
    "deleteMode.delete": "Delete Permanently",
    "table.file": "File",
    "table.formatDevice": "Format / Device",
    "table.size": "Size",
    "table.rule": "Rule",
    "table.date": "Inferred Date",
    "table.suggestedFolder": "Suggested Archive Folder",
    "table.initial": "No analysis results yet",
    "table.empty": "No videos matched the cleanup rules",
    "table.analyzing": "Analyzing folder",
    "log.waiting": "Waiting for action",
    "log.needAnalyzeFolder": "Enter a video folder first",
    "log.analyzeStarted": "Analysis started",
    "log.analyzeDone": "Analysis complete: {video_count} videos, {candidate_count} candidates.",
    "log.analyzeFailed": "Analysis failed",
    "log.analyzeStopped": "Analysis stopped: processed {processed}/{total} videos, {candidate_count} candidates so far.",
    "log.pauseRequested": "Pause requested; analysis will pause after the current video.",
    "log.resumed": "Analysis resumed.",
    "log.stopRequested": "Stop requested; analysis will finish the current video and stop.",
    "log.needOrganizeFolder": "Enter a video folder to archive",
    "log.organizeDone": "Archive complete: moved {moved_count} files, skipped {skipped_count} already in place.",
    "log.folderPicked": "Selected folder: {folder}",
    "log.needFolderToOpen": "Enter or choose a video folder first",
    "log.folderOpened": "Opened folder: {folder}",
    "log.needFolderAndAnalysis": "Enter a folder and finish analysis first",
    "log.needSelectedVideos": "Select videos to process first",
    "log.processDone": "Done: {mode} {deleted_count}, skipped {skipped_count}.",
    "confirm.organize": "Archiving will move videos into the currently selected archive folders. Continue?",
    "confirm.delete": "Are you sure you want to {mode} {count} videos?",
    "mode.delete": "permanently delete",
    "mode.recycle": "move to the recycle folder",
    "device.generic": "Generic",
    "error.requestFailed": "Request failed",
  },
};

const serverErrorTranslations = {
  "请输入文件夹路径": "Enter a folder path",
  "文件夹不存在": "Folder does not exist",
  "输入路径不是文件夹": "The path is not a folder",
  "当前只支持在 macOS 上选择目录": "Folder picking is currently supported only on macOS",
  "找不到 osascript，无法打开目录选择器": "osascript was not found, so the folder picker cannot open",
  "已取消选择目录": "Folder selection was canceled",
  "当前系统不支持打开目录": "This system cannot open folders from the app",
  "视频格式列表无效": "Invalid video format list",
  "至少保留一种视频格式": "Keep at least one video format",
  "保护关键词格式无效": "Invalid protected keyword list",
  "整理粒度无效": "Invalid archive grouping",
  "首尾帧检测需要安装 ffmpeg 和 ffprobe": "First/last frame detection requires ffmpeg and ffprobe",
  "分析任务不存在": "Analysis job does not exist",
  "分析控制命令无效": "Invalid analysis control command",
  "阈值必须大于 0": "Threshold must be greater than 0",
  "保留天数必须大于 0": "Retention days must be greater than 0",
  "静态差异阈值不能小于 0": "Static difference threshold cannot be negative",
  "请求数据不是合法 JSON": "Request body is not valid JSON",
  "分析任务 ID 无效": "Invalid analysis job ID",
  "删除列表格式不正确": "Invalid delete list",
  "删除模式无效": "Invalid delete mode",
  "未找到接口": "API endpoint not found",
};

const commonExtensions = [
  ".3g2",
  ".3gp",
  ".264",
  ".asf",
  ".avi",
  ".dav",
  ".flv",
  ".h264",
  ".h265",
  ".hevc",
  ".m2ts",
  ".m4v",
  ".mjpeg",
  ".mjpg",
  ".mkv",
  ".mp4",
  ".mpeg",
  ".mpg",
  ".mts",
  ".mov",
  ".ts",
  ".vob",
  ".webm",
].join(", ");

const defaultProtectedKeywords = [
  "alarm",
  "event",
  "favorite",
  "human",
  "lock",
  "motion",
  "people",
  "person",
  "保留",
  "报警",
  "告警",
  "人形",
  "事件",
  "移动侦测",
  "重要",
].join(", ");

const presets = {
  careful: {
    size: true,
    threshold: 0.5,
    empty: true,
    retention: false,
    retentionDays: 365,
    static: false,
    staticThreshold: 1.2,
    granularity: "day",
  },
  balanced: {
    size: true,
    threshold: 1.0,
    empty: true,
    retention: false,
    retentionDays: 180,
    static: false,
    staticThreshold: 2.0,
    granularity: "day",
  },
  storage: {
    size: true,
    threshold: 3.0,
    empty: true,
    retention: true,
    retentionDays: 180,
    static: true,
    staticThreshold: 2.0,
    granularity: "month",
  },
  archive: {
    size: false,
    threshold: 1.0,
    empty: false,
    retention: false,
    retentionDays: 365,
    static: false,
    staticThreshold: 2.0,
    granularity: "day",
  },
};

function currentLanguage() {
  return normalizeLanguage(state.language);
}

function normalizeLanguage(language) {
  return translations[language] ? language : "zh";
}

function t(key, values = {}) {
  const catalog = translations[currentLanguage()] || translations.zh;
  let text = catalog[key] ?? translations.zh[key] ?? key;
  Object.entries(values).forEach(([name, value]) => {
    text = text.replaceAll(`{${name}}`, String(value));
  });
  return text;
}

function localizeServerError(message) {
  if (currentLanguage() === "zh") {
    return message;
  }
  if (serverErrorTranslations[message]) {
    return serverErrorTranslations[message];
  }
  const invalidFormat = message.match(/^视频格式无效: (.+)$/);
  if (invalidFormat) {
    return `Invalid video format: ${invalidFormat[1]}`;
  }
  const openerMissing = message.match(/^找不到 (.+)，无法打开目录$/);
  if (openerMissing) {
    return `${openerMissing[1]} was not found, so the folder cannot be opened`;
  }
  const internalError = message.match(/^处理失败: (.+)$/);
  if (internalError) {
    return `Processing failed: ${internalError[1]}`;
  }
  return message;
}

function applyLanguage(language) {
  state.language = normalizeLanguage(language);
  document.documentElement.lang = state.language === "en" ? "en" : "zh-CN";
  document.title = t("app.title");
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.setAttribute("placeholder", t(node.dataset.i18nPlaceholder));
  });
  if (state.healthStatus) {
    healthText.textContent = t(`health.${state.healthStatus}`);
  }
  if (state.lastProgress) {
    renderProgress(state.lastProgress);
  } else {
    progressTime.textContent = formatElapsed(0);
  }
  if (state.hasAnalysis || state.candidates.length) {
    renderCandidates(state.candidates);
  } else {
    setCandidateEmpty(state.candidateEmptyKey || "table.initial");
  }
  if (!state.currentAnalyzeJob && !state.lastProgress) {
    pauseAnalyzeBtn.textContent = t("button.pause");
  }
}

function changeLanguage(language) {
  const nextLanguage = normalizeLanguage(language);
  localStorage.setItem("videoCleanupLanguage", nextLanguage);
  applyLanguage(nextLanguage);
}

async function api(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(localizeServerError(data.error || t("error.requestFailed")));
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
    empty: t("ruleReason.empty"),
    old: t("ruleReason.old"),
    size: t("ruleReason.size"),
    static: t("ruleReason.static"),
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
  metrics.protected.textContent = summary.protected_count ?? 0;
  metrics.formats.textContent = Object.keys(summary.extension_counts || {}).length;
}

function analysisPayload(folder) {
  return {
    folder,
    threshold_mb: Number(thresholdInput.value),
    use_size_filter: sizeFilterEnabled.checked,
    use_empty_filter: emptyFilterEnabled.checked,
    use_retention_filter: retentionFilterEnabled.checked,
    retention_days: Number(retentionDaysInput.value),
    use_static_filter: staticFilterEnabled.checked,
    static_threshold: Number(staticThresholdInput.value),
    organize_granularity: organizeGranularity.value,
    extensions: extensionInput.value,
    protected_keywords: protectedKeywordsInput.value,
  };
}

function organizePayload(folder) {
  return {
    folder,
    organize_granularity: organizeGranularity.value,
    extensions: extensionInput.value,
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
  retentionDaysInput.disabled = busy || !retentionFilterEnabled.checked;
  staticThresholdInput.disabled = busy || !staticFilterEnabled.checked;
  extensionInput.disabled = busy;
  protectedKeywordsInput.disabled = busy;
  organizeGranularity.disabled = busy;
  policyPreset.disabled = busy;
}

function setBusy(isBusy) {
  state.busy = isBusy;
  updateActionState();
}

function formatElapsed(seconds) {
  const total = Math.max(0, Math.floor(seconds || 0));
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  if (currentLanguage() === "en") {
    return minutes > 0 ? `${minutes}m ${rest}s` : `${rest}s`;
  }
  if (minutes > 0) {
    return `${minutes}分${rest}秒`;
  }
  return `${rest}秒`;
}

function renderProgress(status) {
  state.lastProgress = status;
  progressBand.hidden = false;
  const phaseText = t(`phase.${status.phase}`) || t("phase.analyzing");
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
    done: t("file.done"),
    stopped: t("file.stopped"),
    paused: t("file.paused"),
  }[status.state] || t("file.waiting");
  progressFile.textContent = status.current_path || fallbackFileText;
  state.analyzeState = status.state;
  pauseAnalyzeBtn.textContent = status.state === "paused" ? t("button.resume") : t("button.pause");
  updateActionState();
}

function selectedPaths() {
  return [...document.querySelectorAll(".candidate-check:checked")].map((input) => input.value);
}

function setCandidateEmpty(messageKey) {
  state.candidates = [];
  state.candidateEmptyKey = messageKey;
  candidateTable.innerHTML = `
    <tr class="empty-row">
      <td colspan="7">${escapeHtml(t(messageKey))}</td>
    </tr>
  `;
}

function renderCandidates(items) {
  state.candidates = items;
  if (!items.length) {
    setCandidateEmpty(state.hasAnalysis ? "table.empty" : state.candidateEmptyKey || "table.initial");
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
          <td>
            <div class="reason-stack">
              <span class="tag">${escapeHtml(item.extension || "")}</span>
              <span class="subtle">${escapeHtml(item.device_hint || t("device.generic"))}</span>
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

function applyPreset(name) {
  const preset = presets[name];
  if (!preset) {
    return;
  }
  state.applyingPreset = true;
  sizeFilterEnabled.checked = preset.size;
  thresholdInput.value = preset.threshold.toFixed(1);
  emptyFilterEnabled.checked = preset.empty;
  retentionFilterEnabled.checked = preset.retention;
  retentionDaysInput.value = preset.retentionDays;
  staticFilterEnabled.checked = preset.static;
  staticThresholdInput.value = preset.staticThreshold.toFixed(1);
  organizeGranularity.value = preset.granularity;
  state.applyingPreset = false;
  updateActionState();
}

function markCustom() {
  if (!state.applyingPreset) {
    policyPreset.value = "custom";
  }
  updateActionState();
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
    state.healthStatus = "connected";
    healthText.textContent = t("health.connected");
  } catch {
    healthDot.className = "status-dot bad";
    state.healthStatus = "unavailable";
    healthText.textContent = t("health.unavailable");
  }
}

async function analyze() {
  const folder = folderValue();
  if (!folder) {
    addLog(t("log.needAnalyzeFolder"), true);
    return;
  }

  if (state.analyzeTimer) {
    clearTimeout(state.analyzeTimer);
    state.analyzeTimer = null;
  }
  setBusy(true);
  try {
    state.hasAnalysis = false;
    state.candidates = [];
    setCandidateEmpty("table.analyzing");
    addLog(t("log.analyzeStarted"));
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
      state.hasAnalysis = true;
      updateMetrics(status.result.summary);
      renderCandidates(status.result.candidates);
      addLog(t("log.analyzeDone", status.result.summary));
      state.currentAnalyzeJob = null;
      setBusy(false);
      return;
    }
    if (status.state === "error") {
      addLog(status.error ? localizeServerError(status.error) : t("log.analyzeFailed"), true);
      state.currentAnalyzeJob = null;
      setBusy(false);
      return;
    }
    if (status.state === "stopped") {
      state.hasAnalysis = true;
      updateMetrics(status.result.summary);
      renderCandidates(status.result.candidates);
      addLog(
        t("log.analyzeStopped", {
          processed: status.processed,
          total: status.total,
          candidate_count: status.result.summary.candidate_count,
        }),
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
      addLog(t("log.pauseRequested"));
    } else if (action === "resume") {
      addLog(t("log.resumed"));
    } else {
      addLog(t("log.stopRequested"), true);
    }
  } catch (error) {
    addLog(error.message, true);
  }
}

async function organize() {
  const folder = folderValue();
  if (!folder) {
    addLog(t("log.needOrganizeFolder"), true);
    return;
  }
  if (!window.confirm(t("confirm.organize"))) {
    return;
  }

  setBusy(true);
  let shouldAnalyze = false;
  try {
    const result = await api("/api/organize", organizePayload(folder));
    addLog(t("log.organizeDone", result));
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
    addLog(t("log.folderPicked", { folder: result.folder }));
  } catch (error) {
    addLog(error.message, true);
  } finally {
    setBusy(false);
  }
}

async function openFolder() {
  const folder = folderValue();
  if (!folder) {
    addLog(t("log.needFolderToOpen"), true);
    return;
  }
  setBusy(true);
  try {
    const result = await api("/api/open-folder", { folder });
    addLog(t("log.folderOpened", { folder: result.opened }));
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
    addLog(t("log.needFolderAndAnalysis"), true);
    return;
  }
  if (!paths.length) {
    addLog(t("log.needSelectedVideos"), true);
    return;
  }

  const modeText = mode === "delete" ? t("mode.delete") : t("mode.recycle");
  const confirmed = window.confirm(t("confirm.delete", { mode: modeText, count: paths.length }));
  if (!confirmed) {
    return;
  }

  setBusy(true);
  let shouldAnalyze = false;
  try {
    const result = await api("/api/delete", { folder, paths, mode });
    addLog(t("log.processDone", { ...result, mode: modeText }));
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
languageSelect.addEventListener("change", (event) => changeLanguage(event.target.value));
policyPreset.addEventListener("change", () => applyPreset(policyPreset.value));
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
  markCustom();
});
staticFilterEnabled.addEventListener("change", () => {
  markCustom();
});
emptyFilterEnabled.addEventListener("change", markCustom);
retentionFilterEnabled.addEventListener("change", markCustom);
thresholdInput.addEventListener("input", markCustom);
retentionDaysInput.addEventListener("input", markCustom);
staticThresholdInput.addEventListener("input", markCustom);
organizeGranularity.addEventListener("change", markCustom);
extensionInput.addEventListener("input", markCustom);
protectedKeywordsInput.addEventListener("input", markCustom);

extensionInput.value = commonExtensions;
protectedKeywordsInput.value = defaultProtectedKeywords;
const savedLanguage = normalizeLanguage(localStorage.getItem("videoCleanupLanguage") || "zh");
languageSelect.value = savedLanguage;
applyLanguage(savedLanguage);
applyPreset("balanced");
checkHealth();
updateActionState();
