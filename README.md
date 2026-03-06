# 40-aws-reliability-security-databricks

A portfolio-grade **Databricks reliability and security** toolkit:
deterministic offline demos, operational guardrails, and production-safe validation paths.

## The top pains this repo addresses
1) Making data-platform delivery predictable: repeatable checks, clear preflight validation, and measurable outcomes.
2) Reducing operational risk: drills and guardrails instead of “run it and hope”.
3) Enforcing security and governance without blocking delivery: explicit validation modes and clean documentation.

## Quick demo (local)
```bash
make demo-offline
make test-demo
```

What you get:
- offline demo dataset in JSONL format (Databricks-friendly)
- deterministic guardrails report (`artifacts/databricks_guardrails.json`)
- explicit `TEST_MODE=demo|production` tests with safe production gating

## Tests (two explicit modes)

- `TEST_MODE=demo` (default): offline-only checks, deterministic artifacts
- `TEST_MODE=production`: real integrations (requires explicit opt-in + configuration)

Run production mode:

```bash
make test-production
```

Production integration options:
- Set `DATABRICKS_HOST` and `DATABRICKS_TOKEN` to run Databricks REST API checks (workspace reachable + token valid).
- Or set `TERRAFORM_VALIDATE=1` to validate the included Terraform example (requires `terraform`).

## Sponsorship and contact

Sponsored by:
CloudForgeLabs  
https://cloudforgelabs.ainextstudios.com/  
support@ainextstudios.com

Built by:
Freddy D. Alvarez  
https://www.linkedin.com/in/freddy-daniel-alvarez/

For job opportunities, contact:
it.freddy.alvarez@gmail.com

## License

Personal, educational, and non-commercial use is free. Commercial use requires paid permission.
See `LICENSE` and `COMMERCIAL_LICENSE.md`.
