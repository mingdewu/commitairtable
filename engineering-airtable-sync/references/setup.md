# Airtable 自动配置参考

默认由 AI 运行 `auto.py discover` 查找授权范围内的 Base 和项目记录。确定目标后运行 `auto.py provision` 创建或补齐表结构并自动写入本地配置。不要使用浏览器配置向导作为默认入口。

PAT 凭据只能通过本机终端输入：`python3 <installed-skill-dir>/scripts/credentials.py`。禁止向用户索要聊天窗口或网页表单中的令牌，也禁止把令牌放入命令参数。缺少凭据时请用户在自己的终端运行该命令；不要代为输入或通过工具捕获令牌。

令牌需 data.records:read/write、schema.bases:read/write 和对应资源访问。创建新 Base 需要令牌持有人在目标工作区有创建权限。Airtable Web API 提供创建 Base、表和字段的接口；公开接口未提供创建 Workspace 的方法。遇到 API 错误应报告 HTTP 状态和 Airtable 返回的错误类型，不能声称创建成功。

Projects 表：Name、Project ID、Current Stage、Latest Progress、Blockers、Next Steps、Last Synced。Updates 表：Name、Update ID、Project 关联、Completed、In Progress、Blockers、Next Steps、Verification、Evidence、Source、Recorded At。

如果 API 无法访问某个 Base，不能推断它不存在。创建请求结果未知时，先检查远端，再决定是否重试。不要自动重复创建 Base。凭据不写入仓库、日志或聊天回复。
