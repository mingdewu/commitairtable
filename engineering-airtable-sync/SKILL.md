---
name: engineering-airtable-sync
description: Clarify and record engineering ideas, requirements, decisions, progress and blockers in Airtable across any project. Use when asked to manage project progress, enable milestone reminders, choose an Airtable project destination, or preview and save a project update.
---

# Universal engineering recorder

Domain-neutral: illustrations, hypothetical examples and suggested features are not facts about the user's actual project. Never instantiate an example project or infer an industry from documentation. Use the user's chosen language.

## Understand before preparing records

1. Identify the actual project, requested outcome, record type (`idea`, `requirement`, `decision`, `progress`, `blocker`) and status. Use available current conversation, relevant project documents and Git evidence; do not claim access to other conversations. Distinguish a plan from implementation, tests and deployment.
2. If purpose, scope, destination or status is materially uncertain, ask one to three focused questions, then restate the understanding. Do not invent features, owners, deadlines, percentages, decisions or verification. A one-sentence request can be sufficient if unambiguous; length is not a confidence measure.
3. Do not save an ambiguous requirement as settled. If the user explicitly wants a rough idea preserved, quote/paraphrase only what was supplied, label it tentative / pending clarification, and include unanswered questions. Collect only details necessary for the intended record; do not force a full specification to preserve a simple note.
4. With no substantive new information, do not create a new record. Compare recent context and existing project information to avoid paraphrasing an old update as new progress.

## Optional ongoing reminders

Only when the user asks to enable ongoing project management, run `python3 <skill-dir>/scripts/project.py enable-reminders --project <path>`. This appends a bounded section to the project's AGENTS.md, preserving existing instructions. Read that section in the current session. If the host does not read AGENTS.md, integrate the same instruction through its supported project rules when available, otherwise explain the limitation. Do not promise a background watcher or guaranteed cross-host execution.

Offer a brief reminder after a meaningful requirement, decision, feature, fix, verification, release or blocker; group small edits, avoid interrupting ongoing implementation, and don't repeat a declined reminder without new progress. A reminder is not permission to write. Git commit, Git push and Airtable recording are separate operations; clarify ambiguous “Git/Airtable” requests. This skill does not automatically commit or push code.

## Resolve destination and create structure

No configuration form. Use the user-provided Airtable PAT only from a secure local credential source. If a PAT has already been provided in this conversation, do not ask for it again; store it locally without printing it and rotate it after testing because chat history contains the secret. If no credential is available, obtain authorization once through the available trusted browser/account flow. Never require the user to build tables, type shell commands, or edit JSON.

Read [references/workflow.md](references/workflow.md). Use `project.py info` for an existing project route. For another clone, worktree or moved directory, use `project.py link-path --source-key <confirmed-project-key> --project <new-path>` only after checking it is the same project. Never merge solely by name. Otherwise run `auto.py discover --project <path> --name <actual-project-name>` to list authorized Bases and their project records. Compare purpose and project identity using the current conversation, repository, and existing records. Similar names are candidates, never proof. A missing or inaccessible Base is not evidence that it does not exist. If a unique appropriate Base and project are clear, bind them. If the Base fits but the project is new, select that Base and create its project record in the confirmed sync. If no appropriate Base is visible, first identify an existing authorized workspace. Ask only about material ambiguity or a missing destination; do not send the user to a setup page.

For a confirmed destination, run `auto.py provision --project <path> --mode existing-base --target <app-ID>` or `--mode new-base --target <wsp-ID> --name <confirmed-base-name>`. The CLI creates or repairs Projects/Updates, links them, and writes local routing. The PAT needs schema read/write and record read/write scopes, plus Airtable Creator permissions. A new Base can be made through Airtable's API in an existing workspace. Airtable's public Web API does not document a create-workspace endpoint; if a new workspace is actually needed, use Airtable's authenticated UI when available, with the user's concrete choice. Do not claim the PAT alone can create a workspace. Only create a Base after the user has seen the proposed destination and record and confirmed it. Avoid creating duplicate Bases when visibility is incomplete.

## Preview, confirm, save

Before summarizing Git progress, inspect the current branch and saved baseline in the preview. If the baseline is missing, the branch switched, or the old commit is no longer an ancestor, do not describe the full Git diff as new work; ask for the intended comparison range or rely on explicitly verified current-session facts. For a non-Git directory use those facts and project documents. Create minimal JSON in a private temporary location using the workflow reference. Run `sync.py preview --project <path> --input <file>`. This reads remote data but does not write it. Present the actual Base/project, record type/status, exact substantive content, and proposed project-field changes. Explain whether a project will be created or updated. Wait for the user's confirmation of this concrete proposal before `sync.py apply <plan-id>`. General permission to remind or manage a project does not approve a specific record. If the user changes the content, preview the revision before confirmation. A user's confirmation in the current conversation applies only to that plan and its retries.

For corrections, preserve history by appending a clearly identified correction/decision referencing the prior record, and update current overview only if justified. Do not silently rewrite previous historical notes. If requested to edit a specific historical record in place, explain that this CLI currently appends corrections and obtain the user's choice rather than claiming an edit occurred.

Keep code, secrets, personal data and full transcripts out of records. Protect human-owned fields. On partial failure or uncertain network outcomes, inspect `sync.py plan <plan-id>`, report confirmed steps and retry the same plan ID after resolving the cause. Do not advance a Git baseline until both Airtable writes are confirmed; if HEAD or branch changed during synchronization, leave the baseline unchanged. On conflict inspect the remote change before using `preview --refresh`; don't overwrite human edits blindly.

Return in the chat: destination Base/project, records added, project fields changed, what progress or understanding was recorded, unresolved questions/verification limits, and real record links. Never call an idea completed work. If nothing was saved or only part succeeded, say so. Remove private temporary input after use.
