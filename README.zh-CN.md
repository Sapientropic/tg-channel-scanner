# TG 频道扫描器

读取 Telegram 频道消息，按关键词/候选人 profile 过滤，生成 AI 摘要报告。

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
./setup.sh
```

### 配置

```bash
# 1. 复制配置模板，填入你的凭证
cp config.example.toml config.toml
# 编辑 config.toml，填入 api_id 和 api_hash

# 2. 登录 Telegram
tg auth login
```

### 运行扫描

```bash
# 扫描频道列表中所有频道，过去 24 小时
./scripts/scan.sh channel_lists/example.txt

# 扫描过去 7 天
./scripts/scan.sh channel_lists/example.txt 7

# 输出保存到 output/scan_YYYYMMDD_HHMM.jsonl
```

### AI 摘要

```bash
# 方式一：DeepSeek CLI
deepseek exec --auto "读取 output/scan_XXXX.jsonl，根据这个候选人 profile 做筛选汇总：$(cat profiles/example.md)"

# 方式二：直接把输出文件交给 Codex / Claude / 任何 AI agent
# 把 output/ 文件和 profile 文件路径给 agent 即可

# 方式三：Python 脚本（兼容 OpenAI API）
python scripts/summarize.py --input output/scan_XXXX.jsonl --profile profiles/example.md
```

---

## 工作原理

```
Telegram 频道
  → tgcli 读取消息（JSONL）
    → 保存到 output/
      → AI 过滤 + 摘要
        → 结构化报告
```

1. **读取**：`tgcli`（基于 Telethon 的命令行工具）读取你已订阅频道的消息
2. **过滤**：消息保存为 JSONL，包含日期、发送者、文本、频道信息
3. **摘要**：你选择的 LLM 生成过滤后、去重的报告

## 目录结构

```
tg-channel-scanner/
├── config.toml              # 你的凭证（已 gitignore）
├── config.example.toml      # 配置模板
├── setup.sh                 # 一键安装脚本
├── profiles/                # 候选人/筛选 profile
│   └── example.md           # 示例：前端工程师求职
├── channel_lists/           # 频道名称列表（每行一个）
│   └── example.txt          # 示例：俄语 IT 招聘频道
├── scripts/
│   ├── scan.sh              # 批量频道读取
│   └── summarize.py         # 可选 LLM 摘要
├── output/                  # 扫描结果（已 gitignore）
└── docs/
    ├── tos-risk-analysis.md         # ToS 风险分析
    └── getting-api-credentials.md   # 获取 API 凭证指南
```

## 创建自己的 Profile

复制 `profiles/example.md` 并编辑筛选条件。Profile 告诉 AI 要过滤什么：

```markdown
## 候选人
- 姓名：你的名字
- 目标岗位：前端工程师
- 技术栈：React, TypeScript, ...
- 级别：Middle/Senior
- 工作方式：远程优先

## 筛选规则
- 只包含过去 24 小时内的职位
- 去重（同公司 + 同岗位）
- 排除：纯后端、移动端、DevOps...
```

## 创建自己的频道列表

在 `channel_lists/` 下创建 `.txt` 文件，每行一个频道名：

```
React Job | JavaScript | Вакансии
Frontend | Удаленка
TypeScript Job Offers
```

以 `#` 开头的行为注释。

## 安全与 Telegram ToS

本工具读取你已订阅频道的消息——等同于手动滚动浏览。

**重要限制：**
- 自动化扫描频率：**最多每天一次**
- 手动/按需扫描：不限
- 单频道每次读取：**最多 100 条消息**
- 每次扫描总频道数：**最多 25 个**

完整分析见 [docs/tos-risk-analysis.md](docs/tos-risk-analysis.md)。

## Windows

```bat
setup.bat
scripts\scan.bat channel_lists\example.txt
```

## 许可证

MIT
