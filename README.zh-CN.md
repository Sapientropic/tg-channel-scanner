```
 _____ ____    ____ _   _    _    _   _ _   _ _____ _
|_   _/ ___|  / ___| | | |  / \  | \ | | \ | | ____| |
  | || |  _  | |   | |_| | / _ \ |  \| |  \| |  _| | |
  | || |_| | | |___|  _  |/ ___ \| |\  | |\  | |___| |___
  |_| \____|  \____|_| |_/_/   \_\_| \_|_| \_|_____|_____|
 ____   ____    _    _   _ _   _ _____ ____
/ ___| / ___|  / \  | \ | | \ | | ____|  _ \
\___ \| |     / _ \ |  \| |  \| |  _| | |_) |
 ___) | |___ / ___ \| |\  | |\  | |___|  _ <
|____/ \____/_/   \_\_| \_|_| \_|_____|_| \_\
```

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Telegram MTProto](https://img.shields.io/badge/Telegram-MTProto-26A5E4?logo=telegram&logoColor=white)](https://core.telegram.org/mtproto)
[![LLM Powered](https://img.shields.io/badge/powered%20by-LLM-22C55E?logo=openai&logoColor=white)](https://github.com/Sapientropic/tg-channel-scanner)

**读取 Telegram 频道 → AI 语义过滤 → 自包含 HTML 报告。**

一条命令扫描数十个频道，通过 LLM 过滤并生成排名摘要。求职、空投监控、新闻追踪——全部由纯文本 Profile 驱动。

<p align="center"><a href="https://github.com/Sapientropic/tg-channel-scanner/releases/download/v1.0-demo/demo.mp4"><img src="docs/demo.gif" alt="产品演示" width="100%"></a></p>

<p align="center"><em>点击播放完整演示（56s）</em></p>

[**English**](README.md)

---

## 快速开始

### 前置条件

- Python 3.12+
- Telegram 账号（手机号）
- Telegram API 凭证（`api_id` + `api_hash`，[获取方法](docs/getting-api-credentials.md)）

### 安装

```bash
git clone https://github.com/Sapientropic/tg-channel-scanner.git
cd tg-channel-scanner
chmod +x setup.sh scripts/scan.sh
./setup.sh
```

### 配置 & 运行

```bash
# 1. 编辑配置，填入 Telegram API 凭证
#    （setup.sh 已创建在 ~/.config/tgcli/config.toml）
nano ~/.config/tgcli/config.toml

# 2. 扫描频道（首次运行引导登录）
source .venv/bin/activate
./scripts/scan.sh channel_lists/example.txt

# 3. 生成 HTML 报告
python scripts/daily_report.py channel_lists/example.txt \
  --profile profiles/example.md --html
```

### 扫描选项

```bash
# 过去 24 小时（默认）
./scripts/scan.sh channel_lists/example.txt

# 过去 7 天
./scripts/scan.sh channel_lists/example.txt 168

# 从精确 ISO-8601 时间点
./scripts/scan.sh channel_lists/example.txt --since 2026-05-06T07:30:00Z
```

扫描器使用 Telethon（MTProto）+ `iter_messages` 流式读取，遇到超过 cutoff 的消息立刻停止，不会过度拉取。

<details>
<summary>环境变量</summary>

```bash
SCAN_INITIAL_LIMIT=200   # 每个频道初始读取 limit
SCAN_MAX_LIMIT=5000      # 硬上限
SCAN_DELAY=1             # 频道间等待秒数
SCAN_MAX_FLOOD_WAIT_SECONDS=300
TG_SCANNER_CONFIG_DIR=~/.config/tgcli
```

</details>

### 从 Telegram 导出频道

```bash
python scripts/export_folder.py --list
python scripts/export_folder.py --folder "Jobs" --output channel_lists/jobs.txt
```

### 生成报告

```bash
# Markdown + HTML 报告
python scripts/daily_report.py channel_lists/example.txt \
  --profile profiles/example.md --html

# 自定义 LLM 端点（DeepSeek、Ollama 等）
python scripts/report.py --input output/scan_XXXX.jsonl \
  --profile profiles/example.md \
  --base-url https://api.deepseek.com/v1 --model deepseek-chat

# 脱敏后再发给 LLM
python scripts/report.py --input output/scan_XXXX.jsonl \
  --profile profiles/example.md --redact-contact-info

# 预览 prompt 不调用 LLM
python scripts/report.py --input output/scan_XXXX.jsonl \
  --profile profiles/example.md --dry-run-prompt output/prompt-preview.md
```

<p align="center"><img src="docs/screenshots/report-header.png" alt="报告头部与统计栏" width="700"></p>

<p align="center"><img src="docs/screenshots/report-cards.png" alt="语义色标排序卡片" width="700"></p>

HTML 报告为单文件自包含格式：OKLCH 色标（绿=申请、琥珀=调查、灰=跳过）、卡片入场动画、可展开原文、Telegram 深链接。

<details>
<summary>定时任务示例</summary>

```bash
# cron：每天 09:00
0 9 * * * cd /path/to/tg-channel-scanner && .venv/bin/python scripts/daily_report.py channel_lists/example.txt --profile profiles/example.md
```

```bat
REM Windows Task Scheduler
cmd /c "cd /d C:\path\to\tg-channel-scanner && .venv\Scripts\python.exe scripts\daily_report.py channel_lists\example.txt --profile profiles\example.md"
```

</details>

<details>
<summary>自由格式 AI 摘要 & Media OCR</summary>

**自由格式摘要**（无固定排版，纯摘要）：

```bash
python scripts/summarize.py --input output/scan_XXXX.jsonl --profile profiles/example.md
```

**Media OCR/STT**（默认关闭）：

```bash
# xAI vision
export XAI_API_KEY=your-key
./scripts/scan.sh channel_lists/example.txt --ocr --ocr-provider xai

# OpenAI vision
export OPENAI_API_KEY=sk-your-key
./scripts/scan.sh channel_lists/example.txt --ocr --ocr-provider openai

# 自定义端点
./scripts/scan.sh channel_lists/example.txt --ocr --ocr-provider custom \
  --ocr-base-url http://localhost:11434/v1 --ocr-model your-vision-model
```

使用 `--ocr-full-video` 提取完整视频帧（需要 `ffmpeg`）。

</details>

---

## 工作原理

```mermaid
graph LR
    A["📱 Telegram<br>频道"] -->|MTProto| B["🔍 扫描器<br>scan.py"]
    B -->|"JSONL + meta"| C["🤖 LLM<br>语义过滤"]
    C -->|"结构化 JSON"| D["📊 报告<br>report.py"]
    D --> E["📝 Markdown"]
    D --> F["🎨 HTML 报告"]

    style A fill:#26A5E4,color:#fff
    style B fill:#3776AB,color:#fff
    style C fill:#14B8A6,color:#fff
    style D fill:#22C55E,color:#fff
    style E fill:#64748B,color:#fff
    style F fill:#F59E0B,color:#fff
```

1. **读取** — Telethon 读取已订阅频道消息
2. **过滤** — 精确时间截断 + 提前终止
3. **保存** — JSONL + `.meta.json`
4. **报告** — LLM 语义匹配 → Python 渲染统计 + Markdown/HTML

## Profile 与频道列表

### Profile

复制 `profiles/example.md` 并编辑：

```markdown
## 候选人
- 目标岗位：前端工程师
- 技术栈：React, TypeScript, Next.js
- 级别：Middle/Senior
- 工作方式：远程优先

## 筛选规则
- 只包含过去 24 小时内的职位
- 去重（同公司 + 同岗位）
- 排除：纯后端、移动端、DevOps...
```

自定义模式（空投、新闻、活动）添加 `## Extraction Schema`、`## Extraction Prompt`、`## Report Labels` 即可。见 `profiles/example-airdrop.md`。

### 频道列表

在 `channel_lists/` 下创建 `.txt`，使用 **Telegram 用户名**（不是显示名），每行一个：

```
remote_italic
dev_jobs_remote
react_jobs
```

> 获取用户名：Telegram 打开频道 → 点击名称 → 查看 @username。

或直接导出：`python scripts/export_folder.py --folder "Jobs" --output channel_lists/jobs.txt`

## 目录结构

```
tg-channel-scanner/
├── config.example.toml      # 配置模板（实际配置在 ~/.config/tgcli/）
├── requirements.txt         # telethon
├── requirements-llm.txt     # 可选摘要依赖
├── setup.sh / setup.bat     # 一键安装
├── profiles/                # 筛选 profile
├── channel_lists/           # 频道名称列表
├── scripts/
│   ├── scan.py              # 扫描核心（Telethon）
│   ├── export_folder.py     # 从 Telegram 文件夹导出
│   ├── report.py            # 报告生成器（Markdown + HTML）
│   ├── daily_report.py      # 扫描 + 报告流水线
│   └── summarize.py         # 自由格式摘要
├── templates/
│   ├── report-job.html      # OKLCH 色板模板
│   └── report-generic.html  # 自定义模式模板
├── output/                  # 已 gitignore
└── docs/
    └── screenshots/         # 报告截图
```

## 安全与 Telegram ToS

- 只读取你已订阅的频道
- 尊重 `FloodWaitError`，不滥用 API
- 使用真实账号，非新建/虚拟号
- 不要将 Telegram 数据用于 AI 训练、转售或批量采集

详见 [docs/tos-risk-analysis.md](docs/tos-risk-analysis.md)。

## 常见问题

| 问题 | 解决 |
|------|------|
| `ModuleNotFoundError: telethon` | `source .venv/bin/activate` |
| `.sh` 脚本 `Permission denied` | `chmod +x setup.sh scripts/scan.sh` |
| my.telegram.org 显示 ERROR | [获取凭证指南](docs/getting-api-credentials.md) |
| 扫描到 0 条消息 | 检查 `output/*.errors.log` |
| Session 过期 | 删除 `~/.config/tgcli/session`，重新运行 |

## 许可证

MIT
