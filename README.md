# Engineering Airtable Sync

一个通用的 Codex / Antigravity Skill：帮你分析项目想法、提出方案和任务，并把你确认的项目规划与进展保存到 Airtable。

## 安装

需要 Python 3.9+。macOS、Linux 和 WSL 可用。

```bash
git clone https://github.com/mingdewu/commitairtable.git
cd commitairtable
python3 scripts/install.py --agent codex
```

Antigravity 使用：

```bash
python3 scripts/install.py --agent antigravity
```

安装完成后，在 Codex 或 Antigravity 开启新会话。

## 配置 Airtable PAT

**PAT 只在本机终端输入，不要发到聊天窗口。**

1. 在 [Airtable 创建 Personal Access Token](https://airtable.com/create/tokens)。
2. 添加权限：`data.records:read`、`data.records:write`、`schema.bases:read`、`schema.bases:write`。
3. 授权令牌访问你要管理的 Workspace。创建 Base 还要求你的 Airtable 账号有相应权限。
4. 在终端运行安装位置对应的命令：

Codex：

```bash
python3 ~/.codex/skills/engineering-airtable-sync/scripts/credentials.py
```

Antigravity：

```bash
python3 ~/.gemini/config/skills/engineering-airtable-sync/scripts/credentials.py
```

在终端提示中输入 PAT。输入内容不会显示；macOS 保存到 Keychain，Linux/WSL 保存到仅当前用户可读的配置文件。若令牌曾发到聊天里，请先在 Airtable 撤销并创建新令牌。

## 使用

在要管理的项目里打开 Skill，直接描述你的想法或进展。例如：

> 帮我把这个想法发展成项目方案，提出可选做法、关键问题和任务拆解。先给我草案，确认后再保存到 Airtable。

Skill 会查看当前项目资料，提出方案与任务；不确定的地方会标注并向你提问。它会区分 AI 建议、你确认的决定和已完成的工作。每次有实质性项目想法或进展，回复末尾都会问你是否要预览并保存到 Airtable；你确认具体预览后才会写入。同一事项如果你拒绝，不会重复追问。

新项目会使用 `Projects`、`Tasks`、`Updates` 三张表。若目标 Workspace 中没有合适的 Base，Skill 可以在确认后创建 Base 和表结构。现有项目可以追加规划字段和 Tasks 表；请让 Skill 执行结构升级。升级会保留已有记录，不会自动改变 Airtable 视图的列顺序。

## 更新

在仓库目录运行：

```bash
git pull --ff-only
python3 scripts/install.py --agent codex --update
```

Antigravity 将 `codex` 换成 `antigravity`。更新后开启新会话。

更多细节见 [规划说明](engineering-airtable-sync/references/planning.md) 和 [工作流说明](engineering-airtable-sync/references/workflow.md)。
