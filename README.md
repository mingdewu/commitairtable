# Engineering Airtable Sync｜工程进度同步 Skill

在任意本地项目中，使用 Codex 或 Antigravity 整理有证据的开发进展，写入 Airtable。首次同步创建项目，之后更新项目概览并保留工作记录。外贸系统、电商、网站和内部工具等新项目均可使用，无需已有类似项目。

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

安装脚本复制 Skill 到用户目录，不依赖本仓库的绝对路径。Codex 目标为 `~/.codex/skills/engineering-airtable-sync`；Antigravity 目标为 `~/.gemini/config/skills/engineering-airtable-sync`。已有同名安装时会停止，请先备份并移走旧安装，再安装新版本。安装后开启新会话，确认 Skill 已被发现。不同工具版本的发现目录可能有差异，请以实际产品为准。

### 方式三：不用 Git

在 GitHub 仓库页面选择 **Code → Download ZIP**，解压后进入 `commitairtable-main` 文件夹，在终端执行上面的安装命令。

## 配置 Airtable

每位使用者需要配置自己的 Airtable 访问权限；下载 Skill 不会获得作者的账户或令牌。

1. 在 Airtable 创建一个 Base，以及 `Projects` 和 `Updates` 两张普通表。完整字段名称和类型见 [Airtable 配置说明](engineering-airtable-sync/references/setup.md)。
2. 创建 PAT，为目标 Base 授予 `data.records:read`、`data.records:write`。在 macOS 使用钥匙串保存，或通过环境变量 `AIRTABLE_TOKEN` 提供。不要将令牌发给 AI 或提交到 GitHub。
3. 创建 `~/.config/engineering-airtable-sync/config.json`，填写真实的 Base 和表 ID：

```json
{
  "base_id": "app你的BaseID",
  "projects_table": "tbl项目表ID",
  "updates_table": "tbl工作记录表ID",
  "keychain_service": "engineering-airtable-sync"
}
```

在下载的仓库目录中检查连接：

```bash
python3 engineering-airtable-sync/scripts/sync.py status
```

`connected` 表示可以读取两张表；实际字段格式和写入权限须通过首次同步验证。

## 在项目中使用

打开要管理的项目，在 Codex 或 Antigravity 中输入：

> 使用 engineering-airtable-sync，把这次项目进展同步到 Airtable。

新项目示例：

> 使用 engineering-airtable-sync。这个新项目叫“外贸客户管理系统”，用于管理海外客户、询盘和报价。把这次已确认的开发进展同步到 Airtable。

只预览：

> 使用 engineering-airtable-sync，预览这次项目进度，不要写入 Airtable。

Skill 根据当前对话、Git 和可见项目文档整理事实，区分已实现、已测试和已部署。没有确认的新进展时不应创建空记录。不会天然读取其他 AI 工具的历史会话。

## 手工同步与故障恢复

创建 JSON 输入文件，所有字段均为字符串。例如：

```json
{
  "project_name": "外贸客户管理系统",
  "title": "实现客户列表页面",
  "completed": "已实现客户列表，尚未部署",
  "verification": "本地构建通过，尚未进行线上验证",
  "evidence": "src/customers/ 下的页面变更",
  "source": "Codex"
}
```

必填字段为 `project_name`、`title`、`completed`；其他支持的字段见 [Skill 指令](engineering-airtable-sync/SKILL.md)。省略选填字段表示保留项目对应字段；显式传空字符串表示清空该 AI 管理字段。

```bash
python3 engineering-airtable-sync/scripts/sync.py preview --project /path/to/project --input /path/to/progress.json
python3 engineering-airtable-sync/scripts/sync.py apply upd_预览返回的ID
```

预览保存本地计划，不写入 Airtable。同一项目的相同输入复用同一计划，重复 apply 不新增记录。两张表的写入不是事务；部分失败或请求结果未知时，修复故障后使用**同一计划 ID**重试。项目字段在预览后被修改会停止；检查远端内容后，使用修正后的输入和 `preview --refresh` 生成新预览。已开始写入的计划优先使用原计划恢复。

## 换电脑与限制

- Skill 可以重新下载；在新电脑上重新配置令牌和相同的 Base、表 ID，即可继续使用同一个 Airtable。
- **同一项目换电脑或重新 clone，当前版本会识别为新项目，可能创建另一条项目记录。** 本版还没有跨电脑项目重新绑定功能；已有项目迁移需要人工调整本地绑定。新电脑上的全新项目不受此限制。
- 本机的 `~/.config/engineering-airtable-sync/state.json` 保存项目绑定、同步计划和摘要。请勿上传至公开仓库。
- 项目按本机 Git common directory 或非 Git 文件夹识别。同一仓库的 worktree 共用身份；不按项目名称自动合并。
- 同步只修改列出的 AI 管理字段。负责人、优先级、截止日期等应另建人工字段。不保证跨电脑并发写入安全。
- 当前本地测试已通过；真实 Airtable 的首次连接和同步仍需完成。

## 开发验证

无第三方 Python 运行依赖。在仓库目录运行：

```bash
python3 -m unittest discover -s tests -v
```
