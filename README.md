# Engineering Airtable Sync｜工程进度同步 Skill

在任意本地项目中，使用 Codex 或 Antigravity 整理有证据的开发进展，写入 Airtable。首次同步创建项目，之后更新项目概览并保留工作记录。适用于任意工程和业务领域；说明中的示例不是用户实际项目，不会被自动建立为项目。

## 从 GitHub 下载和安装

需要 Python 3.9 或更新版本。当前同步脚本支持 macOS、Linux；Windows 请通过 WSL 运行，同步工具和 AI 工具需运行在同一 WSL 环境中。Windows 原生运行暂未支持。

仓库地址：[mingdewu/commitairtable](https://github.com/mingdewu/commitairtable)。

### 方式一：把 GitHub 链接交给 AI

在另一台电脑的 Codex 或 Antigravity 中输入：

> 从 https://github.com/mingdewu/commitairtable 下载工程进度同步 Skill。先阅读 README.md，再运行安装脚本，为当前工具安装 engineering-airtable-sync。随后引导我配置 Airtable，令牌只保存在本机。

### 方式二：通过 Git 下载

```bash
git clone https://github.com/mingdewu/commitairtable.git
cd commitairtable
python3 scripts/install.py --agent codex
```

安装到 Antigravity，使用：

```bash
python3 scripts/install.py --agent antigravity
```

两者都安装，使用 `python3 scripts/install.py --agent both`。

安装脚本复制 Skill 到用户目录，不依赖本仓库的绝对路径。Codex 目标为 `~/.codex/skills/engineering-airtable-sync`；Antigravity 目标为 `~/.gemini/config/skills/engineering-airtable-sync`。已有同名安装时默认停止。更新时运行 `python3 scripts/install.py --agent codex --update`（Antigravity 替换 agent 名；也支持 both），会自动备份旧 Skill 后更新，保留 Airtable 配置和工作记录。安装后开启新会话，确认 Skill 已被发现。不同工具版本的发现目录可能有差异，请以实际产品为准。

### 方式三：不用 Git

在 GitHub 仓库页面选择 **Code → Download ZIP**，解压后进入 `commitairtable-main` 文件夹，在终端执行上面的安装命令。

## 自动发现和配置 Airtable

在实际项目中告诉 AI 项目的目的和要记录的内容。AI 使用已授权的 PAT 查找可见 Base、查看相关项目及字段，判断归属。匹配不确定时先问你；有合适 Base 就在其中建立项目记录；确实没有合适 Base 时，在你选定的现有工作区创建 Base，并自动建立 Projects、Updates 表和关联字段。随后自动保存本地路由。没有配置页面，也不要求手工建表或编辑 JSON。

PAT 需授予 `data.records:read`、`data.records:write`、`schema.bases:read`、`schema.bases:write` 和相关资源访问；新建 Base 需要目标工作区的 Creator 权限。你可以在对话中提供 PAT，但聊天记录会留存该秘密，测试后建议轮换。AI 不应在回复或日志里复述令牌。若使用安全的本地凭据存储，AI 可直接调用。

Airtable 的 Web API 支持在现有工作区创建 Base。公开 API 文档没有创建 Workspace 的接口；确需新工作区时，AI 可以在已登录的 Airtable 网页中操作，并按你的实际项目范围命名。若未登录或权限不足，需要你完成登录/授权。不能把看不到的 Base 当作不存在。

```bash
python3 engineering-airtable-sync/scripts/auto.py discover --project /path/to/project --name '实际项目名'
python3 engineering-airtable-sync/scripts/auto.py provision --project /path/to/project --mode existing-base --target app已确认的BaseID
# 或：在已确认的工作区创建新 Base
python3 engineering-airtable-sync/scripts/auto.py provision --project /path/to/project --mode new-base --target wsp已确认的WorkspaceID --name '已确认的Base名'
```

这些命令由 AI 执行。实际项目和保存内容确认后，再预览并同步记录。配置会自动写入本机，不需要用户手工填写。当前支持 PAT；OAuth 一键连接尚未实现。

## 已安装旧版？

在原下载目录中，让 AI 执行：

```bash
git pull --ff-only
python3 scripts/install.py --agent codex --update
```

使用 Antigravity 时将 `codex` 替换为 `antigravity`。然后开启新会话，要求自动发现 Airtable 目标；仅更新仓库不会自动更新已复制安装的 Skill。

## 在项目中使用

打开要管理的项目，在 Codex 或 Antigravity 中输入：

> 使用 engineering-airtable-sync，把这次项目进展同步到 Airtable。

新项目示例（项目名和内容由你实际指定，任何行业均可）：

> 这是一个新项目。先和我确认要解决的问题、目标用户及第一阶段范围，再预览拟保存的需求，得到我的确认后再保存。

只预览：

> 使用 engineering-airtable-sync，预览这次项目进度，不要写入 Airtable。

Skill 根据当前对话、Git 和可见项目文档整理事实，区分已实现、已测试和已部署。没有确认的新进展时不应创建空记录。不会天然读取其他 AI 工具的历史会话。

## 通用管理流程

接收想法或重要进展 → 检查理解是否充分 → 必要时提问 → 确定 Base 和项目 → 展示拟保存内容 → 用户确认 → 保存 → 聊天返回变化及链接。

支持想法、已确认需求、决定、工作进展和阻塞。想法不会写成已完成开发。信息含糊时先澄清；用户明确要求保留初步想法时，可标为待澄清并保留问题。每次写入前必须确认具体内容和目标。

启用提醒：

> 为当前项目启用工程进度管理，重要需求、决定或修改完成后，提醒我是否记录到 Airtable。

AI 会向项目 AGENTS.md 追加提醒约定。提醒依赖当前工具读取并遵循项目指令；不是后台监控，不能保证所有工具自动触发。不读取 AGENTS.md 的工具需由 AI 配置其支持的项目规则。Git 提交、推送和 Airtable 保存分别处理。零碎修改合并提醒，拒绝后不反复追问。

未绑定的项目可以查找已授权 Base 和现有项目，由用户确认归属后绑定。有合适 Base 时在其中建项目；只有用户确认没有合适归属并选择工作区后才新建 Base。权限不足不视为不存在。多个项目可绑定不同 Base；PAT 必须有相应访问权限。

历史内容修改采用新增更正记录并引用原记录，保留历史；当前概览可更新。本版尚不提供历史记录原地编辑命令。具体命令和数据格式见 [工作流说明](engineering-airtable-sync/references/workflow.md)。

## 手工同步与故障恢复

创建 JSON 输入文件，所有字段均为字符串。例如：

```json
{
  "project_name": "用户指定的项目",
  "title": "完成已确认的功能",
  "completed": "已实现约定功能，尚未部署",
  "verification": "本地构建通过，尚未进行线上验证",
  "evidence": "实际变更文件及提交证据",
  "source": "Codex"
}
```

必填字段为 `project_name`、`title`、`completed`；其他支持的字段见 [Skill 指令](engineering-airtable-sync/SKILL.md)。省略选填字段表示保留项目对应字段；显式传空字符串表示清空该 AI 管理字段。

```bash
python3 engineering-airtable-sync/scripts/sync.py preview --project /path/to/project --input /path/to/progress.json
python3 engineering-airtable-sync/scripts/sync.py apply upd_预览返回的ID
```

预览保存本地计划，不写入 Airtable。同一项目的相同输入复用同一计划，重复 apply 不新增记录。两张表的写入不是事务；部分失败或请求结果未知时，修复故障后使用**同一计划 ID**重试。项目字段在预览后被修改会停止；检查远端内容后，使用修正后的输入和 `preview --refresh` 生成新预览。已开始写入的计划优先使用原计划恢复。

## 多项目、多路径与同步基线

Codex 和 Antigravity 可安装同一份 Skill。项目绑定与同步状态保存在当前电脑的用户配置目录，两个工具共享。一个项目可有多个本地路径：同一仓库的 worktree 自动共用项目身份；另外一次 clone、移动仓库或重命名无 Git 目录时，先用 `project.py info` 找到原项目 key，再让 AI 运行 `project.py link-path --source-key <原项目key> --project <新路径>`。这一步会复用原 Project ID、Airtable 目标和基线，不按项目名称猜测。不同项目可绑定不同 Base。

每次 Airtable 项目概览和工作记录都确认写入后，记录当前 Git 分支的 HEAD 为同步基线。预览会显示分支、HEAD、未提交变更及旧基线是否仍属于当前历史。新分支、变基或历史改写后，AI 要核实比较范围，不能把全部差异直接当成新增进展。无 Git 项目可以用明确的对话与文档事实同步，但没有 Git 基线。

发生冲突或部分失败时，运行 `sync.py plan <计划ID>` 检查目标和已确认步骤；恢复使用同一计划 ID。预览后的人工修改会阻止覆盖。只在两张表都确认成功、且分支与 HEAD 未变化时推进 Git 基线。

跨电脑时先查找原 Airtable 项目并绑定其 Project ID；本机状态不会自动在设备间同步。多个设备同时写入同一项目仍有竞争风险，需检查远端冲突。

## 开发验证

无第三方 Python 运行依赖。在仓库目录运行：

```bash
python3 -m unittest discover -s tests -v
```
