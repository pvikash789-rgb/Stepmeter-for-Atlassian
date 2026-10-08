# Phase 0: Validate before building

Goal: in three days, find out whether this product can work, before writing the real thing.

We answer three questions:

1. **Can we read the rules?** Does the Automation Rule Management API give us each rule's full structure (trigger, conditions, branches, actions)?
2. **What does Atlassian already show?** How much per-rule cost detail is in the product today?
3. **Do admins care?** Do Jira admins already know which of their rules will cost the most from 3 December 2026?

**Kill criteria:** if the API can't give us rule structure, or most admins say they already know their expensive rules, we stop and switch to the backup idea.

---

## Day 1: Set up a test site

1. Create a free Atlassian Cloud site with Jira at atlassian.com (any name, e.g. `stepcost-lab`). Use an email you can keep long term.
2. Create one Scrum project (e.g. `LAB`) and add about 30 work items. The quickest way is to import [`lab-work-items.csv`](lab-work-items.csv), which has 30 items with mixed work types and labels (6 labelled `vip`). Team-managed spaces may not accept the Priority column; skip it, the rules use labels instead. Give some of them sub-tasks, a few labels and mixed priorities so rules have something to act on.
3. Create the test rules in the next section (Project settings, then Automation, or the global Automation page).
4. Create an API token for your Atlassian account (Account settings, then Security, then API tokens). Treat it like a password.

### The test rules

Each rule is chosen to exercise one pattern that affects step cost. Keep the names as written so results are easy to read.

| # | Name | Build it like this | What it tests |
|---|------|--------------------|---------------|
| 1 | `01 simple event` | Work item created, then Assign to reporter | Cheapest pattern: 2 steps |
| 2 | `02 condition first` | Work item transitioned to Done, then If labels contain `vip`, then Add comment | Condition placed early |
| 3 | `03 noisy trigger` | Work item updated (any change), then If label = `vip`, then Add comment | Broad trigger that mostly finds nothing but still counts |
| 4 | `04 field change narrow` | Field value changed: Labels only, then Add comment | Same intent as #3 with a narrow trigger |
| 5 | `05 daily jql` | Scheduled daily with JQL `project = LAB AND status = "In Progress" AND updated < -7d`, then Add comment | Scheduled rule running per matching item |
| 6 | `06 hourly no jql` | Scheduled every hour, no JQL, then Log action | Runs whether or not there is work |
| 7 | `07 subtask branch` | Work item transitioned to Done, then For sub-tasks: Transition to Done | Branch that multiplies by sub-task count |
| 8 | `08 jql branch` | Work item created, then For JQL `project = LAB AND labels = vip`: Edit field | Branch over a search result |
| 9 | `09 if else` | Work item created, then If/else: labels contain `backend` adds label `team-a`, else adds label `team-b` | If/else blocks |
| 10 | `10 many actions` | Work item created, then Lookup work items, Create variable, Add comment, Edit field, Send email | Many actions in one run |
| 11 | `11 webhook secret` | Work item created, then Send web request to `https://example.com/hook/test-secret-path` with header `Authorization: Bearer test-secret-123` | Secret redaction. The URL is fake and won't receive anything. |
| 12 | `12 manual` | Manual trigger, then Add comment | Runs only when a person triggers it |
| 13 | `13 incoming webhook` | Incoming webhook trigger, then Add comment | External trigger |
| 14 | `14 weekly create` | Scheduled weekly on Monday, no JQL, then Create work item | Recurring work creation |
| 15 | `15 condition last` | Work item updated, then Edit field (for example set Description), then If labels contain `vip`, then Add comment | Anti-pattern: work done before the check |
| 16 | `16 disabled` | Any simple rule, then disable it | Disabled rules should cost nothing |
| 17 | `17 rovo action` | Work item created, then Use Rovo agent (only if offered on your plan) | Agent actions bill Rovo credits, not steps |

Skip #17 if your site doesn't offer it. Note that in the journal.

## Day 2: Run the spike

You need Python 3.8 or newer. No packages to install.

```bash
cp .env.example .env        # then fill in your site, email and token
python3 phase0/fetch_rules.py
```

The script looks up your site, lists every rule, fetches each one, strips secrets, and prints a table like this:

```
Rule                             State     Trigger                            Comp Cond  Br Steps/run*
01 simple event                  ENABLED   jira.issue.event.trigger:created      1    0   0          2
```

Redacted copies of each rule are saved in `phase0/output/`. That folder is git-ignored and must never be committed.

**Record in the journal:**
- Did listing and fetching work? Paste any error messages.
- Does the JSON show nested components inside branches and if/else blocks?
- Did rule 11's URL and header come out as `[REDACTED]`? Open its file and check.
- Any components the script couldn't read (it prints a warning).

## Day 2: Look at what Atlassian shows

1. Open the automation usage view for your site, and the organisation's Platform usage page (Atlassian Administration, then Insights).
2. Note exactly what you can see per rule: runs, steps, both or neither. Take screenshots.
3. Let the rules run for a day or two by editing and moving work items. Compare Atlassian's step count with the script's floor estimate. This is the first accuracy data point for Phase 1.

## Days 2 to 3: Talk to Jira admins

Aim for 3 to 5 people who manage Jira automation at work: ex-colleagues, IIMB alumni, people in the Atlassian Community. 15 minutes each.

Questions:

1. Roughly how many automation rules does your company have? Who creates them?
2. Have you heard about the move to per-step billing from 3 December? What's the plan?
3. Do you know which of your rules use the most automation? How would you find out today?
4. If a tool showed your 20 most expensive rules and how to make each one cheaper, would you use it? What would stop you? (Listen for: API token concerns, security review, "we'll just turn overage on.")
5. Who would care most about the bill: the Jira admin, IT finance, or someone else?

**Record in the journal:** one line per interview with the key quote, plus a tally for question 3: knows / partly knows / doesn't know.

## Decision at the end of Phase 0

| Result | Decision |
|---|---|
| API gives structure, admins mostly don't know their costly rules | Go to Phase 1 |
| API gives structure, admins already know | Rethink the angle or switch to backup |
| API doesn't give structure | Switch to backup: "I'm affected too" for the JSM portal |
