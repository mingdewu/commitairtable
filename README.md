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

安装脚本复制 Skill 到用户目录，不依赖本仓库的绝对路径。Codex 目标为 `~/.codex/skills/engineering-airtable-sync`；Antigravity 目标为 `~/.gemini/config/skills/engineering-airtable-sync`。已有同名安装时默认停止。更新时运行 `python3 scripts/install.py --agent codex --update`（Antigravity 替换 agent 名；也支持 both），会自动备份旧 Skill 后更新，保留 Airtable 配置和工作记录。安装后开启新会话，确认 Skill 已被发现。不同工具版本的发现目录可能有差异，请以实际产品为准。

### 方式三：不用 Git

在 GitHub 仓库页面选择 **Code → Download ZIP**，解压后进入 `commitairtable-main` 文件夹，在终端执行上面的安装命令。

## 首次连接：由 AI 启动浏览器向导

安装后对 AI 说：

> 帮我连接 Airtable，启动这个 Skill 的浏览器配置向导。

AI 会运行 `engineering-airtable-sync/scripts/setup.py`，打开只在本机监听的配置页面。你只需要：

1. 在 Airtable 登录并创建 PAT，授权所选目标。将令牌输入本机页面的密码框，不发到 AI 对话。
2. 选择创建新 Base 或连接已有 Base，粘贴目标工作区或 Base 的链接。AI 可以协助查找目标链接。
3. 点击“创建 / 连接并保存配置”。

向导自动创建 Base（新建模式）、Projects 和 Updates 表、字段及关联，自动取得 ID，保存令牌并生成本地配置。已有同名表会检查兼容性，补齐缺失字段；不兼容时停止，不删除现有数据。无需手工建表、输入终端命令或编辑 JSON。

首次自动建表需要 `data.records:read`、`data.records:write`、`schema.bases:read`、`schema.bases:write`。创建 Base 还需要目标工作区的 Creator 权限，PAT 需覆盖该工作区的当前及未来 Base。仅连接已有 Base 时，可将 PAT 资源限制为该 Base。初始化后可撤掉 `schema.bases:write`，日常同步只使用记录读写。

macOS 令牌保存在钥匙串；Linux / WSL 保存在本机权限 600 的令牌文件（未加密）。配置文件由向导自动生成，内容仅含非秘密 ID。每位使用者都需要自己的授权；当前采用 PAT，尚未实现 OAuth 一键授权。向导验证表结构和记录读取，实际记录写入由首次真实同步验证。

如果已有配置，AI 应先检查连接，不覆盖现有目标。遇到创建请求中断，先检查 Airtable 是否已创建 Base，再通过已有 Base 链接恢复，避免重复创建。详细权限和手工排查见 [首次配置说明](engineering-airtable-sync/references/setup.md)。

## 已安装旧版？

在原下载目录中，让 AI 执行：

```bash
git pull --ff-only
python3 scripts/install.py --agent codex --update
```

使用 Antigravity 时将 `codex` 替换为 `antigravity`。然后开启新会话，要求启动浏览器向导；仅更新仓库不会自动更新已复制安装的 Skill。

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
