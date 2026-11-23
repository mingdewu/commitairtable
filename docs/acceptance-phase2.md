# 第二阶段验收记录

日期：2026-11-23。

| 范围 | 结果 |
| --- | --- |
| Codex 全局 Skill | 已安装在用户级目录，当前 Codex 会话已识别该 Skill。 |
| Antigravity 全局 Skill | 已安装在用户级目录；在 Antigravity 的 Installed → Skills & Rules 中可见 `/engineering-airtable-sync`。尚未在 Antigravity 对话里执行真实同步。 |
| 多仓库和多路径 | 每个项目保留独立路由；同一 Git 仓库的 worktree 共用身份。另一次 clone、迁移目录和无 Git 目录重命名使用显式 `link-path` 关联，避免仅凭名称误合并。 |
| Git 同步基线 | 两张 Airtable 记录均确认成功、且分支与 HEAD 保持不变时，按 Project ID 和分支保存 HEAD。预览显示基线是否为当前 HEAD 的祖先及最多 100 个新增提交 ID。 |
| 分支切换、改写历史、无 Git | 新分支无基线；旧基线不是祖先时标记 `diverged_or_missing`；无 Git 目录标记 `not_applicable`。Skill 需基于明确证据总结，不能把全部 diff 直接视为新进展。 |
| 冲突和恢复 | 项目字段在预览后改变会停止覆盖。部分失败保留确认状态；`sync.py plan` 可查看计划，同一 ID 重试。旧计划保留原目的地快照。 |

本地自动测试 28 项通过，Skill 格式验证通过。Git 临时仓库测试覆盖 worktree、分支、历史改写、无 Git、clone 路径关联和成功后基线推进。未创建真实 Airtable 项目或验收记录，因为本轮没有指定实际要归档的工程和目标 Base。跨电脑并发写入同一项目仍需更强的远端协调；当前检测的是写前冲突，不提供跨设备事务锁。
