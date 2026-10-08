# Stepmeter for Atlassian

Find which Jira and Confluence automation rules will cost the most under Atlassian's per-step billing, and how to rewrite them to cost less.

**Status:** Phase 0, validating before building. Started 8 October 2026.

## Why this exists

From 3 December 2026, Atlassian bills automation per step. Every trigger, condition, action, branch and loop in a rule run counts, even when the trigger finds nothing to do. Steps come from a pooled monthly allowance, overage costs $0.50 per 1,000 steps and is switched on by default, and Enterprise plans lose unlimited automation.

Atlassian shows usage per meter and per app. It doesn't show which of your rules are expensive or how to fix them. One daily rule that branches over 500 work items can burn more steps than fifty simple rules together.

## What it will do

1. Read every automation rule on a site through Atlassian's Rule Management API.
2. Estimate each rule's monthly step cost.
3. Rank the most expensive rules in money terms.
4. Suggest specific, cheaper rewrites.

Secrets inside rules (webhook URLs, headers, tokens) are stripped, and rule data is never stored.

## Follow the build

- **Build journal:** the story so far, from problem discovery to results (`docs/index.html`, published with GitHub Pages)
- **Decision log:** every product decision with its reasoning and the alternatives considered (`docs/decisions.html`)
- **Phase 0 kit:** [`phase0/`](phase0/README.md), with test rules, the API spike script and the admin interview guide

## Plan

| Phase | What | Status |
|---|---|---|
| 0 | Validate: API access, what Atlassian already shows, admin interviews | In progress |
| 1 | Cost engine: parse rules, count steps, estimate run frequency, check accuracy | Next |
| 2 | Recommendations and report | Planned |
| 3 | Beta with 5 to 10 admins on real sites | Planned |
| 4 | Launch and write-up, before 3 December 2026 | Planned |

## Run the Phase 0 spike

```bash
cp .env.example .env      # add your site, email and API token
python3 phase0/fetch_rules.py
```

Python 3.8+, standard library only.

## About

Built by Vikash Kumar (IIM Bangalore MBA, product manager) as a public proof-of-work project. I use an AI assistant (Claude) for research and coding. Problem choice, product decisions and trade-offs are mine and are recorded in the decision log.
