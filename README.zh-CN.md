# TG 频道扫描器

按需读取 Telegram 频道消息，按关键词/候选人 profile 过滤，生成 AI 摘要报告。

最初为求职者监控多个 Telegram 招聘频道设计，但适用于任何频道监控场景。

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

> `setup.sh` 会从 `requirements.txt` / `requirements-llm.txt` 安装锁定依赖，并验证 Telethon 可用。

### 配置

```bash
# 1. 编辑配置，填入 Telegram API 凭证
#    （setup.sh 已创建 ~/.config/tgcli/config.toml）
nano ~/.config/tgcli/config.toml

# 2. 运行扫描（首次运行如无 session 会自动引导登录）
source .venv/bin/activate
./scripts/scan.sh channel_lists/example.txt
```

### 运行扫描

```bash
# 扫描频道列表中所有频道，过去 24 小时
./scripts/scan.sh channel_lists/example.txt

# 扫描过去 7 天
./scripts/scan.sh channel_lists/example.txt 168

# 从精确 ISO-8601 时间点开始扫描
./scripts/scan.sh channel_lists/example.txt --since 2026-05-06T07:30:00Z

# 输出保存到 output/scan_YYYYMMDD_HHMMSS.jsonl
# 错误日志在 output/scan_YYYYMMDD_HHMMSS.errors.log
```

扫描器通过 Telethon（MTProto user client）读取消息，使用精确 UTC cutoff。若读取结果达到 limit 上限，脚本会自动扩大 limit；如果频道达到 `SCAN_MAX_LIMIT` 仍可能不完整，脚本会非零退出并在日志里标记 incomplete，不会静默漏消息。

常用环境变量：

```bash
SCAN_INITIAL_LIMIT=200   # 每个频道初始读取 limit
SCAN_MAX_LIMIT=5000      # 达到该上限仍饱和则报 incomplete
SCAN_DELAY=1             # 频道之间等待秒数
```

### AI 摘要

```bash
# 方式一：Python 脚本（兼容 OpenAI API）
export OPENAI_API_KEY=sk-your-key
python scripts/summarize.py --input output/scan_XXXX.jsonl --profile profiles/example.md

# 可选：发送给 LLM 前脱敏邮箱、手机号和 Telegram handle
python scripts/summarize.py --input output/scan_XXXX.jsonl --profile profiles/example.md \
  --redact-contact-info

# 兼容 DeepSeek、Ollama 等：
python scripts/summarize.py --input output/scan_XXXX.jsonl --profile profiles/example.md \
  --base-url https://api.deepseek.com/v1 --model deepseek-chat

# 方式二：直接把输出文件交给 Codex / Claude / 任何 AI agent
#   把以下两个文件路径给 agent：
#   - output/ 中的 JSONL 扫描文件
#   - profiles/ 中的 profile 文件
#   Codex 示例 prompt：
#     "Read output/scan_XXXX.jsonl and filter jobs matching profiles/my-profile.md"
```

`summarize.py` 会把选中的 JSONL 消息和 profile 发送到你配置的 OpenAI-compatible API。脚本会在 prompt 中把 Telegram 消息标记为不可信内容，但发送私密频道数据前仍应先确认 LLM 服务商的隐私和数据使用条款。

---

## 工作原理

```
Telegram 频道
  → Telethon 读取消息（MTProto，精确时间过滤，含 media 信息）
    → scanner 做饱和检测 + 完整性检查
    → 保存到 output/（JSONL，含 has_photo / media_type 字段）
      → AI 过滤 + 摘要
        → 结构化报告
```

1. **读取**：Telethon（MTProto user client）读取你已订阅频道的消息，包括图片等 media 元数据
2. **过滤**：`scripts/scan.py` 按精确时间过滤，并拒绝静默接受已打满的读取上限
3. **保存**：消息保存为 JSONL，包含日期、发送者、文本、频道信息、media 字段
4. **摘要**：你选择的 LLM 生成过滤后、去重的报告

## 目录结构

```
tg-channel-scanner/
├── config.example.toml      # 配置模板（实际配置在 ~/.config/tgcli/）
├── requirements.txt         # 锁定 scanner 依赖（telethon）
├── requirements-llm.txt     # 锁定可选摘要依赖
├── setup.sh / setup.bat     # 一键安装脚本
├── profiles/                # 候选人/筛选 profile
│   └── example.md           # 示例：前端工程师求职
├── channel_lists/           # 频道名称列表（每行一个）
│   └── example.txt          # 示例频道列表
├── scripts/
│   ├── scan.sh              # 批量频道读取（Mac/Linux）
│   ├── scan.bat             # 批量频道读取（Windows）
│   ├── scan.py              # 跨平台扫描核心（Telethon）
│   └── summarize.py         # 可选 LLM 摘要
├── output/                  # 扫描结果（已 gitignore）
└── docs/
    ├── tos-risk-analysis.md         # ToS 风险分析
    └── getting-api-credentials.md   # 获取 API 凭证指南（英文）
```

## 创建自己的 Profile

复制 `profiles/example.md` 并编辑筛选条件：

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

## 创建自己的频道列表

在 `channel_lists/` 下创建 `.txt` 文件。使用 **Telegram 频道用户名**（不是显示名），每行一个：

```
# 正确 — 这是 Telegram 用户名
remote_italic
dev_jobs_remote
react_jobs

# 错误 — 这是显示名，不会生效
React Job | JavaScript | Вакансии
```

> 如何获取频道用户名：在 Telegram 中打开频道 → 点击名称 → 查看 @username。

以 `#` 开头的行为注释。

## 安全与 Telegram ToS

本工具读取你已订阅频道的消息——等同于手动滚动浏览。

**要点：**
- 没有频道数量硬限制——50+ 个频道配合 1 秒间隔完全没问题
- 按需扫描：不限次数
- 自动化扫描：每天一次很安全，更频繁也可以
- 使用真实账号（非新建/虚拟手机号账号）

主要约束是 Telegram 的 **FloodWaitError**（速率限制），不是封号。详见 [docs/tos-risk-analysis.md](docs/tos-risk-analysis.md)。

## Windows

```bat
setup.bat
```

配置文件位于 `%USERPROFILE%\.config\tgcli\config.toml`——编辑填入 API 凭证后：

```bat
call .venv\Scripts\activate.bat
scripts\scan.bat channel_lists\example.txt
```

## 常见问题

| 问题 | 解决 |
|------|------|
| `ModuleNotFoundError: telethon` | 先激活 venv：`source .venv/bin/activate` |
| `.sh` 脚本 `Permission denied` | `chmod +x setup.sh scripts/scan.sh` |
| my.telegram.org 显示 ERROR | 见 [获取凭证指南](docs/getting-api-credentials.md) |
| 扫描到 0 条消息 | 检查 `output/*.errors.log` 中的错误 |
| 扫描提示 incomplete | 提高 `SCAN_MAX_LIMIT` 或缩小时间窗口 |
| Session 过期/未授权 | 删除 `~/.config/tgcli/session` 后重新运行，scan.py 会引导登录 |

## 许可证

MIT
