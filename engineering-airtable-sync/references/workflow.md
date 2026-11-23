# Workflow commands

Commands are run by the agent; users provide intent and authorization. Paths are relative to the installed skill. Python 3.9+, macOS/Linux/WSL.

## Routing and reminders

```bash
python3 scripts/project.py info --project /path/to/project
python3 scripts/project.py enable-reminders --project /path/to/project
python3 scripts/project.py discover --project /path/to/project
python3 scripts/project.py discover --project /path/to/project --base-id appSelected
python3 scripts/project.py bind --project /path/to/project --base-id appSelected
python3 scripts/project.py bind --project /path/to/project --base-id appSelected --project-id proj_existing
```

Discover lists only authorized Bases (schema.bases:read required); a selected Base's Projects records are read with data.records:read. Don't exhaustively read unrelated Bases. Use user intent to narrow candidates, then inspect only relevant schemas/projects. Bind is local only and validates the selected schema; it does not create a remote project. Without --project-id, the next confirmed sync uses the local project identity, creating a remote project if absent. With --project-id, the ID must exist in the selected Base. Inspect pending plans before rebinding: old plans retain their original destination and must not be applied under a new confirmation.

Per-project destination configurations live under ~/.config/engineering-airtable-sync/destinations; project-routes.json stores bindings and reminder preference. Projects without a route fall back to the original global configuration. setup.py --project <path> creates a project-specific configuration via the browser wizard. The same PAT is shared locally and must authorize each chosen destination. No credential value is stored in plans/configuration.

## Input format

All values are strings. Every record needs project_name and title. Record types:

- progress (default for backward compatibility): requires completed; may include verification, evidence, in_progress, blockers, next_steps, source, current_stage, latest_progress.
- idea / requirement / decision / blocker: requires content and record_status; may include verification, evidence, blockers, next_steps, source. Do not provide completed, latest_progress, current_stage or in_progress for these notes.

Example, only after the user actually confirms this generic idea:

```json
{
  "project_name": "用户指定的项目名称",
  "title": "用户提出的想法标题",
  "record_type": "idea",
  "record_status": "待澄清",
  "content": "只整理用户实际表达的内容，并列出尚未确定的问题。",
  "source": "当前对话"
}
```

Non-progress notes are compatible with the existing schema: Updates.Name is prefixed with type/status, content goes into In Progress, and Completed remains empty. They do not change Latest Progress or Current Stage. The project may be created with its name/ID and Last Synced, but no fabricated completion. Optional blockers/next_steps change their project fields only when explicitly provided and confirmed. No new columns or schema migrations are required for record types.

```bash
python3 scripts/sync.py preview --project /path/to/project --input /private/path/record.json
# Only after confirming the concrete preview in chat:
python3 scripts/sync.py apply upd_plan_id
python3 scripts/sync.py status --project /path/to/project
```

Preview stores the destination/config snapshot. Apply follows that snapshot, never a newly selected global destination. Metadata contains only IDs and the keychain service name. Identical content uses the existing plan; completed plans need no repeat write. A confirmation is enforced by the Skill's interaction workflow, not a cryptographic identity or CLI authentication system.

## Behavioral checks for the agent

- “For example a travel app…”: don't create a travel project; clarify the actual project.
- “Build something to help my work”: ask what work/problem and intended users before a requirement record.
- “Just save this rough thought”: preserve supplied text as an idea with unresolved questions after preview confirmation.
- Two similar Base names: show candidates and ask; do not choose by similarity.
- API 403 during search: explain missing access; do not create a replacement Base.
- User declines a milestone reminder: continue engineering without a write or repeated nagging.
- A code change without tests: report implemented/unverified, never tested or deployed.
