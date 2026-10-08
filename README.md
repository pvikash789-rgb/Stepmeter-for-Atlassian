# Stepmeter for Jira

Find which Jira and Confluence automation rules will cost the most under Atlassian's per-step billing, and how to rewrite them to cost less.

**Status:** Phase 0, validating before building. Started 8 October 2026.

**Build journal:** https://pvikash789-rgb.github.io/stepmeter-for-jira/

## Why this exists

From 3 December 2026, Atlassian Cloud measures automation usage in steps. Each trigger, condition, action, branch and loop that runs counts as one step, including a trigger that finds nothing to act on. Steps come from a monthly allowance pooled across the organisation, extra usage is billed at $0.50 per 1,000 steps and is on by default, and Enterprise plans move from unlimited automation to an allowance.

Cost now depends on how each rule is built. A daily scheduled rule that loops over 500 work items and edits each one uses at least 15,000 steps a month on its own. Atlassian Administration shows usage by meter and app. From the public documentation I couldn't find a view that ranks individual rules by step cost, and Phase 0 checks this in the product.

## What it will do

1. Read every automation rule on a site through the Automation Rule Management API.
2. Estimate each rule's monthly step cost.
3. Rank the most expensive rules in money terms.
4. Suggest specific rewrites that use fewer steps.

Secrets inside rules (webhook URLs, headers, tokens) are stripped before processing, and rule data isn't kept.

## Plan

| Phase | What | Status |
|---|---|---|
| 0 | Validate: API access, what the product already shows, admin interviews | In progress |
| 1 | Cost engine: parse rules, count steps, estimate run frequency, check accuracy | Next |
| 2 | Recommendations and report | Planned |
| 3 | Beta with 5 to 10 admins on their own sites | Planned |
| 4 | Public release, before 3 December 2026 | Planned |

## Repository

- [`docs/`](docs/): the build journal and decision log, published with GitHub Pages
- [`phase0/`](phase0/README.md): test rules, the API spike script and the admin interview guide

## Run the Phase 0 spike

```bash
cp .env.example .env      # add your site, email and API token
python3 phase0/fetch_rules.py
```

Python 3.8 or newer, standard library only. Output goes to `phase0/output/`, which is git-ignored.

## About

Built by Vikash Kumar. I use an AI assistant (Claude) for research and coding. Problem choice, product decisions and trade-offs are mine and are recorded in the [decision log](https://pvikash789-rgb.github.io/stepmeter-for-jira/decisions.html).

Not affiliated with or endorsed by Atlassian. Jira and Confluence are trademarks of Atlassian.
