# Security policy

This repository is teaching code for *The Production AI Engineering
Handbook*. It is built to demonstrate production controls, and it is
tested, but it has not had an independent security audit. Review it as
you would any third-party code before using it in a system that holds
real data.

## Reporting a vulnerability

Please **do not** open a public issue for a security problem. Use
GitHub's private vulnerability reporting for this repository
(*Security* tab → *Report a vulnerability*). Include the affected file
and commit, the steps to reproduce, and the impact you expect.

You can expect an acknowledgement within seven days. Fixes are
released as commits to the default branch, with credit if you want it.

## Scope

In scope: the `atlas` package, the API, the Dockerfile and Compose
file, the labs, and anything that would mislead a reader into an
insecure production design.

Out of scope: the deliberately vulnerable fixtures (for example the
poisoned `wiki-vpn` document and the fake keys in tests), which exist
so the controls can be tested.

## Secure-use notes

- Development tokens (`/auth/dev-token`) are disabled when
  `ATLAS_ENV=prod`; never expose a development instance publicly.
- Production refuses to start without real secrets. Generate them with
  `python -c "import secrets; print(secrets.token_urlsafe(32))"` and
  store them in a secret manager, not in files.
- The development users in `atlas/core/identity.py` are fixtures.
  Replace identity with your organization's identity provider.
- Real model providers receive whatever context Atlas assembles.
  Restricted context is routed only to providers flagged in-region;
  confirm your provider contract before setting that flag (Chapter 5).
- Never point the integration tests at a database with real data: they
  drop and recreate the schema.
