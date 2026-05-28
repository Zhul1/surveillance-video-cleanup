# Surveillance Video Cleanup

用于整理 NAS 监控视频的小工具仓库，包含两条处理路线：

- 低资源方案：按文件大小把小视频移动到回收站，再按年月整理目录。
- 高精度方案：抽帧 + OpenCV + Apple Vision 做“无人视频”筛选。

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
2. 把散落的小时目录整理到 `YYYYMM/` 月目录下。
3. 在有需要时，用视觉扫描进一步筛掉“没人”的视频。

## 快速开始

### 图形界面

如果你想直接用界面操作，而不是手敲命令：

```bash
python3 app/server.py
```

然后打开：

[http://127.0.0.1:8765](http://127.0.0.1:8765)

界面支持：

- 输入要处理的视频目录
- 点击选择本机视频目录
- 在访达中打开当前视频目录
- 按年月日整理视频
- 可选按文件大小阈值筛出候选视频
- 可选检测首尾帧一致的静态视频
- 分析时显示已处理、剩余、耗时和当前文件
- 列出所有候选视频
- 勾选后移动到回收目录或永久删除

说明：

- 默认阈值是 `1.0 MB`
- 首尾帧一致检测依赖本机 `ffmpeg` 和 `ffprobe`
- 默认删除模式是“移动到回收目录”
- 回收目录会建在目标目录下的 `.nas-video-cleanup-trash/`

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
env "$(grep -v '^#' .env | xargs)" ./scripts/move_by_size.sh
```

说明：

- 只处理 `.mp4`
- 自动跳过 `@eaDir` 和 `#recycle`
- 只做移动，不做永久删除
- 会在移动前再次核对文件大小，降低误判风险

### 2. 按月整理目录

```bash
SOURCE_BASE="/volume3/TV_Shows/监控视频/卧室" ./scripts/sort_into_months.sh
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

确认后再移动被判为 `empty_candidate` 的视频：

```bash
python3 scripts/scan_videos.py \
  --out /path/to/scan-results.csv \
  --move-empty \
  --move-via local \
  --remote-prefix /volume3/TV_Shows \
  --local-prefix /private/tmp/codex_nas_tvshows \
  --trash-prefix /volume3/TV_Shows/#recycle/codex_no_person
```

## 配置建议

### 尺寸阈值建议

实战里，`<= 0.7MB` 往往是比较温和的低资源筛选阈值，`<= 1MB` 风险更高，建议只移动到回收站，不要直接永久删除。

### 安全建议

- 永远优先移动到回收站，不要直接 `rm`
- 先跑小目录做抽样验证
- 先做 `dry run` 或输出日志
- 用视觉扫描时降低 `workers`，避免电脑温度过高

## 脚本说明

### `scripts/move_by_size.sh`

通用版的按大小移动脚本。通过环境变量控制源目录、回收站目录和阈值。

### `scripts/sort_into_months.sh`

把 `YYYYMMDDHH` 形式的小时目录整理到月目录 `YYYYMM/` 下。

### `scripts/scan_videos.py`

扫描视频，基于：

- Haar Cascade
- HOG People Detector
- 帧间运动量
- 可选的 Apple Vision 二次确认

输出 CSV，可继续驱动“移动无人视频”的步骤。

### `scripts/run_monthly_cleanup.sh`

批量按月份扫描并移动“空视频”的驱动脚本，适合已经有 SMB 挂载的场景。

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
python3 -m unittest discover -s tests
```

测试覆盖：

- 按大小移动时包含刚好等于阈值的文件
- UI 后端按年月日归档和回收目录移动
- 视觉扫描结果移动时的远程路径安全校验

## 后续可扩展

- 增加 `dry-run` 到 shell 脚本
- 增加按扩展名白名单
- 增加 JSON/YAML 配置文件
- 增加 NAS SSH/SMB 自动探测
- 增加单元测试和示例数据
