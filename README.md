# Surveillance Video Cleanup

用于整理 NAS、本机硬盘或移动硬盘中的监控视频。它适合家庭摄像头、小店铺、办公室、物业公共区域等常见场景，目标是先盘点、再筛选、再回收，尽量避免误删重要片段。

仓库包含三条处理路线：

- 图形界面：适合大多数人，支持策略预设、候选列表、暂停/继续/停止、回收或永久删除。
- 低资源方案：按文件大小把异常小视频移动到回收站，再按年月整理目录。
- 高精度方案：抽帧 + OpenCV + Apple Vision 做“无人/低运动视频”筛选。

这个仓库是从一次实际清理任务中整理出来的工程化版本，默认不会内置你的 NAS 地址、账号或密码。

## 目录结构

```text
surveillance-video-cleanup/
├── README.md
├── .gitignore
├── app/
│   ├── server.py
│   └── static/
│       ├── app.js
│       ├── index.html
│       └── styles.css
├── examples/
│   └── config.env.example
├── scripts/
│   ├── move_by_size.sh
│   ├── run_monthly_cleanup.sh
│   ├── scan_videos.py
│   └── sort_into_months.sh
└── vision/
    └── person_detect.swift
```

## 适用场景

典型目录结构示例：

```text
/volume3/TV_Shows/监控视频/卧室/
├── 2023/
│   ├── 2023030900/
│   ├── 2023030901/
│   └── ...
├── 2024/
└── 2025/
```

目标：

1. 将体积很小的视频移动到回收站，而不是直接永久删除。
2. 识别空文件、过旧录像、静态画面、疑似录制失败片段。
3. 保护文件名或目录中带有 `alarm`、`event`、`报警`、`人形`、`重要` 等关键词的片段。
4. 把散落的视频按 `YYYY/YYYYMM/YYYYMMDD/` 或 `YYYY/YYYYMM/` 归档。
5. 在有需要时，用视觉扫描进一步筛掉“没人/低运动”的视频。

## 推荐流程

1. 先挂载或接入视频目录，确认能在 Finder / 文件管理器中看到原始视频。
2. 打开图形界面，选择目录。
3. 选择策略：第一次使用建议选“家庭谨慎”或“均衡清理”。
4. 点击“分析目录”，先看候选数量、候选体积、受保护数量和命中规则。
5. 抽样打开几条候选视频，确认规则符合你的摄像头录制习惯。
6. 先使用“移动到回收目录”，确认几天后没有问题，再清空回收目录。
7. 最后再执行“按年月日整理”或“按月归档”，让目录结构稳定下来。

不建议第一次就选择“永久删除”。监控录像的误删成本通常高于多占几 GB 空间。

## 快速开始

### 图形界面

如果你想直接用界面操作，而不是手敲命令：

```bash
python3 app/server.py
```

然后打开：

[http://127.0.0.1:8765](http://127.0.0.1:8765)

界面支持：

- 中文 / English 界面切换，并会记住上次选择
- 输入要处理的视频目录
- 点击选择本机视频目录
- 在访达中打开当前视频目录
- 按日或按月整理视频
- 常见清理策略预设：家庭谨慎、均衡清理、空间优先、只归档整理
- 自定义视频扩展名列表
- 可选按文件大小阈值筛出候选视频
- 可选识别空文件或录制失败文件
- 可选按保留天数筛选旧录像
- 可选检测首尾帧一致的静态视频
- 可配置保护关键词，命中后不列入删除候选
- 分析时显示已处理、剩余、耗时和当前文件，并可暂停、继续或停止
- 列出所有候选视频
- 勾选后移动到回收目录或永久删除

说明：

- 默认阈值是 `1.0 MB`
- 默认识别常见监控视频格式：`.3g2`, `.3gp`, `.264`, `.asf`, `.avi`, `.dav`, `.flv`, `.h264`, `.h265`, `.hevc`, `.m2ts`, `.m4v`, `.mjpeg`, `.mjpg`, `.mkv`, `.mp4`, `.mpeg`, `.mpg`, `.mts`, `.mov`, `.ts`, `.vob`, `.webm`
- 首尾帧一致检测依赖本机 `ffmpeg` 和 `ffprobe`
- 默认删除模式是“移动到回收目录”
- 回收目录会建在目标目录下的 `.nas-video-cleanup-trash/`

### 策略预设

| 策略 | 适合人群 | 默认行为 |
| --- | --- | --- |
| 家庭谨慎 | 家里、老人小孩、门口/客厅等敏感摄像头 | 只筛非常小的文件和空文件，不启用过期清理 |
| 均衡清理 | 大多数 NAS 用户 | 筛小文件和空文件，保留按日归档 |
| 空间优先 | 磁盘快满、录像量很大 | 提高小文件阈值，启用保留期和静态画面检测，按月归档 |
| 只归档整理 | 只想先整理目录，不想删除候选 | 关闭候选筛选规则，只做格式识别和归档建议 |

### 格式和命名兼容

服务端会识别市面上常见摄像头和 NVR 导出的格式，包括海康/大华/宇视/Reolink/萤石/Tapo/Eufy/米家/Ring/Wyze 等常见命名风格。支持从这些日期格式中推断归档目录：

- `2024010112`
- `20240101123000`
- `2024-01-01_12-30-00`
- `2024_01_01_123000`
- `2024/01/01`
- 文件名或上级目录中包含上述日期

### 1. 低资源方式：按大小移动

先复制配置模板：

```bash
cp examples/config.env.example .env
```

编辑 `.env`，至少设置：

```bash
SOURCE_BASE="/volume3/TV_Shows/监控视频/卧室"
TRASH_BASE="/volume3/TV_Shows/#recycle/codex_size_based_1MB/监控视频/卧室"
SIZE_THRESHOLD_BYTES=1048576
```

执行：

```bash
set -a
. ./.env
set +a
./scripts/move_by_size.sh
```

第一次建议先预演，确认输出符合预期后再真正移动：

```bash
set -a
. ./.env
set +a
DRY_RUN=1 ./scripts/move_by_size.sh
```

说明：

- 处理常见监控视频格式，包括 `.3g2`, `.3gp`, `.264`, `.asf`, `.avi`, `.dav`, `.flv`, `.h264`, `.h265`, `.hevc`, `.m2ts`, `.m4v`, `.mjpeg`, `.mjpg`, `.mkv`, `.mp4`, `.mpeg`, `.mpg`, `.mts`, `.mov`, `.ts`, `.vob`, `.webm`
- 自动跳过 `@eaDir` 和 `#recycle`
- 只做移动，不做永久删除
- 设置 `DRY_RUN=1` 时只输出将要移动的记录，不创建目录、不移动文件
- 会在移动前再次核对文件大小，降低误判风险

### 2. 按月整理目录

```bash
SOURCE_BASE="/volume3/TV_Shows/监控视频/卧室" ./scripts/sort_into_months.sh
```

预演模式：

```bash
SOURCE_BASE="/volume3/TV_Shows/监控视频/卧室" DRY_RUN=1 ./scripts/sort_into_months.sh
```

它会把像 `2025031416` 这样的小时目录移动到：

```text
/volume3/TV_Shows/监控视频/卧室/2025/202503/2025031416
```

### 3. 视觉扫描方式

这个方案更耗 CPU，但比单纯按大小更准确。

依赖：

- Python 3
- OpenCV (`cv2`)
- NumPy
- macOS（如果要使用 `vision/person_detect.swift`）

说明：只执行 `--move-empty` 移动已有扫描结果时，不需要 OpenCV。

编译 Apple Vision 辅助检测器：

```bash
swiftc vision/person_detect.swift -o vision/person_detect
```

准备一个远程视频清单文件，每行一个 NAS 路径，例如：

```text
/volume3/TV_Shows/监控视频/卧室/2023/202303/2023030900/00M08S_1683572408.mp4
/volume3/TV_Shows/监控视频/卧室/2023/202303/2023030900/01M09S_1683572469.mp4
```

然后执行扫描：

```bash
python3 scripts/scan_videos.py \
  --list /path/to/video-list.remote.txt \
  --out /path/to/scan-results.csv \
  --remote-prefix /volume3/TV_Shows \
  --local-prefix /private/tmp/codex_nas_tvshows \
  --trash-prefix /volume3/TV_Shows/#recycle/codex_no_person \
  --workers 4 \
  --samples 6 \
  --vision-confirm \
  --vision-detector ./vision/person_detect
```

如果只是先看结果，不移动文件，到这里就够了。

确认后先预演移动被判为 `empty_candidate` 的视频：

```bash
python3 scripts/scan_videos.py \
  --out /path/to/scan-results.csv \
  --move-empty \
  --dry-run \
  --move-via local \
  --remote-prefix /volume3/TV_Shows \
  --local-prefix /private/tmp/codex_nas_tvshows \
  --trash-prefix /volume3/TV_Shows/#recycle/codex_no_person
```

确认输出后去掉 `--dry-run` 才会真正移动。若必须通过 SSH 在 NAS 上移动，需要显式传入地址和账号，仓库不会内置这些信息：

```bash
python3 scripts/scan_videos.py \
  --out /path/to/scan-results.csv \
  --move-empty \
  --move-via ssh \
  --ssh-host nas.example.local \
  --ssh-user admin \
  --ssh-port 22 \
  --remote-prefix /volume3/TV_Shows \
  --local-prefix /private/tmp/codex_nas_tvshows \
  --trash-prefix /volume3/TV_Shows/#recycle/codex_no_person
```

## 配置建议

### 尺寸阈值建议

实战里，`<= 0.5MB` 往往是比较温和的低资源筛选阈值，`<= 1MB` 适合大多数家庭摄像头，`>= 3MB` 更偏“空间优先”。阈值越大，越应该先移动到回收目录并抽样确认。

### 保留期建议

- 家庭门口、客厅、儿童房：不建议自动按保留期删除，除非已经有备份。
- 店铺、仓库、办公室：常见保留期是 `90-180` 天。
- 只做合规留存：按你的地区和行业要求设置，工具不会替你判断法律要求。

### 安全建议

- 永远优先移动到回收站，不要直接 `rm`
- 先跑小目录做抽样验证
- 先做 `dry run` 或输出日志
- 用视觉扫描时降低 `workers`，避免电脑温度过高

## 脚本说明

### `scripts/move_by_size.sh`

通用版的按大小移动脚本。通过环境变量控制源目录、回收站目录和阈值；设置 `DRY_RUN=1` 时只打印将要移动的文件。

### `scripts/sort_into_months.sh`

把 `YYYYMMDDHH` 形式的小时目录整理到月目录 `YYYYMM/` 下；设置 `DRY_RUN=1` 时只打印将要移动的目录。

### `scripts/scan_videos.py`

扫描视频，基于：

- Haar Cascade
- HOG People Detector
- 帧间运动量
- 可选的 Apple Vision 二次确认

输出 CSV，可继续驱动“移动无人视频”的步骤。

### `scripts/run_monthly_cleanup.sh`

批量按月份扫描并移动“空视频”的驱动脚本，适合已经有 SMB 挂载的场景。必须显式设置月份和路径；移动阶段默认 `MOVE_DRY_RUN=1`，确认后设置 `MOVE_DRY_RUN=0` 才会真正移动。

示例：

```bash
MONTHS="202401 202402" \
SCANNER="$PWD/scripts/scan_videos.py" \
VIDEO_LIST="/path/to/video-list.remote.txt" \
OUTPUT_DIR="/path/to/output" \
REMOTE_PREFIX="/volume3/TV_Shows" \
LOCAL_PREFIX="/private/tmp/codex_nas_tvshows" \
TRASH_PREFIX="/volume3/TV_Shows/#recycle/codex_no_person" \
./scripts/run_monthly_cleanup.sh
```

## 不包含的内容

仓库里不应该提交这些东西：

- NAS 账号密码
- DSM 登录态文件
- 扫描日志
- 视频样本图
- 本地下载的 wheel 包

`.gitignore` 已经把这类文件排除了。

## 测试

运行内置回归测试：

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q
```

测试覆盖：

- 按大小移动时包含刚好等于阈值的文件
- UI 后端按年月日归档和回收目录移动
- shell 脚本 dry-run、按大小移动、按月整理
- 常见监控格式识别
- 常见摄像头日期格式推断
- 保护关键词、过期规则和按月归档
- 扫描结果 dry-run、本地/SSH 移动参数构造
- 视觉扫描结果移动时的远程路径安全校验

## 后续可扩展

- 增加 JSON/YAML 配置文件
- 增加 NAS SSH/SMB 自动探测
- 增加候选视频缩略图预览
