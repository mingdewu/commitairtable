# Planning and creative collaboration

Be an active engineering partner. Offer useful possibilities, alternatives, tradeoffs and concrete recommendations. The user need not supply a finished specification. Use the project and conversation to decide which artifacts help: a project brief, problem framing, user journeys, architecture options, experiments, risks, key questions, milestones, task briefs, acceptance criteria, rollout or other relevant material. This is an open set, not a required template.

Read existing project evidence first. Separate user requirements, observed implementation, AI proposals and unresolved assumptions. Missing details do not prevent useful draft work: label assumptions and ask only questions that materially affect the next decision. Never turn an example into the actual project. Scale detail to the project; do not manufacture dates, owners, budgets or completed work. Offer architecture when useful, not as a prerequisite for every idea.

For project planning, return a meaningful draft in chat before Airtable setup. Explain the purpose, first useful outcome, suggested approach, executable next steps and pivotal questions in the user's language. Task briefs should explain the result, work scope and observable acceptance criteria. Suggested tasks start as proposed; confirmed tasks can be planned. Do not infer completion from a commit or from writing the plan itself. A request to merely capture an idea should stay lightweight.

Before saving, show the proposed destination, overview, tasks and changes. Confirmation can approve an entire batch, including an explicitly labelled draft; it does not imply that every suggestion is an adopted decision. Revise existing stable task IDs rather than duplicate tasks on every plan revision. Inspect existing tasks before choosing IDs. Use `Airtable.request(tasks_table)` with pagination to read tasks; only include tasks linked to this project. Preserve omitted fields and human edits. Do not replace the entire overview with a narrow update.

Task lifecycle is a default part of substantive planning and progress management. A new project plan should normally include a first task breakdown. Before a meaningful update to an existing project, inspect its linked tasks, map observed work to stable task IDs, and update matching tasks. If nothing matches, propose a task; if no task change is warranted, state why. Make the preview explicit about current/proposed status and evidence. Do not mark completion without checking acceptance criteria. For a saved plan, Proposed is a valid status; saving a proposal is not task completion.

## Storage v2

Run `auto.py upgrade --project <path>` for an existing bound tracker after explaining the additive schema change. New provisioning includes v2. This adds fields and Tasks, preserves existing records and links, and does not reorder existing Airtable views. Keep old pending sync plans on their saved configuration until recovered. API access to old data does not establish its meaning: inspect legacy records before migration.

New input fields: overview, goals, scope, plan, open_questions, planning_status (strings). `plan` can hold any useful planning document in Markdown, including task briefs and risks; the schema is not a limit on creativity. Types include plan, analysis and brief as well as idea, requirement, decision, progress and blocker. Non-progress records require content and record_status. Current stage may describe discovery/planning; it is not proof of completed development.

`tasks` is optional, a list of at most 200 objects. Required string fields: task_id (stable within the project), name, status, description, acceptance. Optional strings: phase, priority, dependencies (stable task IDs explained in text), evidence. No automatic dates, owners or percent complete. The CLI scopes task IDs by project and preserves them across plans. Each task is linked to its project. Changes are included in preview and checked for conflicts before applying. Partial failure resumes using the same plan ID.

Example structure (replace with actual user context, never create this example project):

```json
{
  "project_name": "Actual project",
  "title": "First planning draft",
  "record_type": "plan",
  "record_status": "AI proposal, pending decisions",
  "content": "The draft, alternatives and questions reviewed in chat.",
  "overview": "Problem, intended users and desired outcome.",
  "plan": "Proposed approach with assumptions clearly labelled.",
  "planning_status": "Draft",
  "current_stage": "Discovery",
  "open_questions": "Decisions that affect scope.",
  "next_steps": "The next concrete action.",
  "tasks": [{"task_id": "discovery-01", "name": "Validate the core need", "status": "Proposed", "description": "Specific work and expected deliverable.", "acceptance": "Observable evidence needed to accept this task."}]
}
```

## Presentation and legacy records

Projects should tell a reader what the project is and what happens next. Updates.Content contains the actual note; Type and Status are explicit. Tasks show the executable work. For existing views, arrange visible columns as Name, status, overview/content, next steps, and internal IDs last using the authenticated UI if available. Do not claim the CLI changes view layout.

Old notes remain in In Progress until reviewed; never erase them or infer all In Progress text is an idea. Use `migrate.py --project <path>` to preview strictly recognised old note prefixes and `--apply` only after the user confirms that preview. It only fills empty Content/Type/Status fields and keeps the source text. Unknown formats are skipped. Generate missing project overviews from actual evidence and confirm them through normal sync, not invented migration defaults.

After saving, read back the affected records, verify substantive content and links, then return the real project/update/task links, changes made, and any partial failure. A structure-only setup is not a saved project plan.
