# 首次连接流程

默认由 AI 启动 `python3 <skill-dir>/scripts/setup.py` 并保持进程运行，向用户提供本机浏览器链接。不要要求用户手动建表、运行终端命令或写配置文件。完成后运行 `sync.py status` 检查，再结束向导进程。

用户在本机页面输入 PAT，并提供目标工作区或已有 Base 链接。AI 可通过已获授权的浏览器帮助找到链接；凭据不进入聊天。向导创建并检查表结构、保存凭据、生成配置。

## 授权

PAT 创建页：https://airtable.com/create/tokens

初始化需要 `data.records:read`、`data.records:write`、`schema.bases:read`、`schema.bases:write`。创建新 Base：用户须拥有 Workspace Creator 权限，PAT 资源覆盖目标工作区的当前及未来 Base。连接已有 Base：须拥有 Base Creator 权限，PAT 只需授权该 Base。用户必须自行完成账户授权；当前尚未实现 OAuth。

若用户只授予记录读写，程序不能自动建表。解释缺少结构权限，帮助用户修改目标令牌权限；不要退回默认手工建表流程。初始化后可撤销结构写入权限，日常同步只需记录读写。

## 自动生成内容

Projects：Name（主字段，单行文本）、Project ID（单行文本）、Current Stage / Latest Progress / Blockers / Next Steps（长文本）、Last Synced（日期时间）。

Updates：Name（主字段，单行文本）、Update ID / Source（单行文本）、Completed / In Progress / Blockers / Next Steps / Verification / Evidence（长文本）、Recorded At（日期时间）、Project（关联 Projects）。

配置自动写到 `~/.config/engineering-airtable-sync/config.json`，包含 base_id、projects_table、updates_table、keychain_service。macOS 令牌存钥匙串；Linux / WSL 使用 `~/.config/engineering-airtable-sync/token`，权限 600，未加密。不要将该目录上传 GitHub。

## 故障恢复

初始化会保留 `setup-state.json` 中的 Base 创建结果。创建 Base 请求结果未知时停止自动重试，先检查 Airtable；如已创建，改用该 Base 链接连接。不要在未知状态下清空检查点并重复创建。已知 Base 内的表和字段可重新检查并补齐；不改变已有字段类型和错误的表关联。

若本机已有配置，先运行 `sync.py status`。切换目的地前检查并备份配置，由用户指定新的目标；不覆盖原配置。权限报错时检查 PAT scopes、资源范围和用户 Creator 权限，管理员也可能限制 API。

接口依据：https://airtable.com/developers/web/api/create-base 、https://airtable.com/developers/web/api/create-table 、https://airtable.com/developers/web/api/create-field 。
