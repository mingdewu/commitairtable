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

## Resolve destination

Read [references/workflow.md](references/workflow.md) for commands and payload format. Start with `project.py info --project <path>` and use a confirmed existing binding. Otherwise discover authorized Bases and candidate Projects records. Search results are candidates: similar names alone are not enough to bind. Ask the user to choose when multiple destinations fit. Permission errors or incomplete visibility do not mean a Base does not exist.

Prefer a compatible existing Base, creating a new project record inside it when needed. A new project does not automatically require a new Base. Only propose creating a Base if no appropriate authorized destination is found and the user agrees to the concrete new name and workspace. For an existing project on a new machine, bind its stable Project ID; never merge by name silently.

If initialization is needed, read [references/setup.md](references/setup.md) and launch `python3 <skill-dir>/scripts/setup.py --project <path>` as a persistent process. Give the local browser URL to the user. The wizard creates the confirmed schema and saves credentials/configuration; the user authorizes access and enters the token locally. Do not ask the user to manually build tables, run commands, edit JSON or paste a token into chat. Stop the wizard after setup or cancellation. A broad PAT may see multiple Bases; never widen permissions automatically.

## Preview, confirm, save

Create minimal JSON in a private temporary location using the workflow reference. Run `sync.py preview --project <path> --input <file>`. This reads remote data but does not write it. Present the actual Base/project, record type/status, exact substantive content, and proposed project-field changes. Explain whether a project will be created or updated. Wait for the user's confirmation of this concrete proposal before `sync.py apply <plan-id>`. General permission to remind or manage a project does not approve a specific record. If the user changes the content, preview the revision before confirmation. A user's confirmation in the current conversation applies only to that plan and its retries.

For corrections, preserve history by appending a clearly identified correction/decision referencing the prior record, and update current overview only if justified. Do not silently rewrite previous historical notes. If requested to edit a specific historical record in place, explain that this CLI currently appends corrections and obtain the user's choice rather than claiming an edit occurred.

Keep code, secrets, personal data and full transcripts out of records. Protect human-owned fields. On partial failure or uncertain network outcomes, report confirmed steps and retry the same plan ID after resolving the cause. On conflict inspect the remote change before using `preview --refresh`; don't overwrite human edits blindly.

Return in the chat: destination Base/project, records added, project fields changed, what progress or understanding was recorded, unresolved questions/verification limits, and real record links. Never call an idea completed work. If nothing was saved or only part succeeded, say so. Remove private temporary input after use.
