# Airtable 首次配置

## 一次性设置 Airtable

在 Airtable 创建一个专用 Base，建立以下两张**普通表**（不是 Airtable 外部同步表）。字段名大小写必须完全一致。建议用英文表名、中文内容；名称可不同，但配置必须对应。

**Projects 表**：

| 字段 | 类型 |
| --- | --- |
| Name | 单行文本（主字段） |
| Project ID | 单行文本 |
| Current Stage | 长文本 |
| Latest Progress | 长文本 |
| Blockers | 长文本 |
| Next Steps | 长文本 |
| Last Synced | 日期和时间（含时间） |

**Updates 表**：

| 字段 | 类型 |
| --- | --- |
| Name | 单行文本（主字段） |
| Update ID | 单行文本 |
| Project | 链接到 Projects 的记录 |
| Completed | 长文本 |
| In Progress | 长文本 |
| Blockers | 长文本 |
| Next Steps | 长文本 |
| Verification | 长文本 |
| Evidence | 长文本 |
| Source | 单行文本 |
| Recorded At | 日期和时间（含时间） |

在 Airtable 开发者页面创建个人访问令牌（PAT），为这个 Base 授予 `data.records:read` 和 `data.records:write`。令牌的创建者也必须具有 Base 的相应权限。不要把令牌粘贴进对话或存进仓库。

在 macOS 中，可通过「钥匙串访问」App 新建通用密码，服务名为 `engineering-airtable-sync`，密码填写 PAT。也可在本机终端使用交互输入：

```bash
security add-generic-password -s engineering-airtable-sync -a "$USER" -w
```

此命令会交互式请求输入密码。如果你的 macOS 版本没有进入交互输入，请使用「钥匙串访问」App 手动创建通用密码。也可临时通过环境变量 `AIRTABLE_TOKEN` 提供令牌；环境变量不要写进仓库。

创建 `~/.config/engineering-airtable-sync/config.json`：

```json
{
  "base_id": "app你的BaseID",
  "projects_table": "tbl项目表ID",
  "updates_table": "tbl工作记录表ID",
  "keychain_service": "engineering-airtable-sync"
}
```

建议填写 Airtable 的 Base ID 和表 ID，而非表名；ID 可以在 Airtable API 文档中查看。脚本的结果链接也按表 ID 生成。配置仅含非秘密信息。

