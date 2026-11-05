# Contributing

Thank you for helping improve the companion code for *The Production
AI Engineering Handbook*. Corrections, clearer explanations, new tests,
and bug reports are all welcome.

## Before you start

- **Errors in the book's code** are the most valuable reports. Open an
  issue with the listing number, what you ran, what you expected, and
  what you got.
- **Listings must match the book.** The files under `listings/` are
  printed verbatim in the book. A change to one is a change to the
  printed text, so open an issue first and describe the fix; the
  author applies listing changes together with the next printing.
- **Everything else** (the `atlas` package, tests, labs, docs) can be
  changed by pull request.

## Ground rules

1. **No paid services in tests or labs.** Every test and lab must run
   offline on the mock provider. Code that needs a real provider is
   optional and is never called by `make verify`.
2. **No secrets.** Never commit a key, token, password, or `.env`
   file. Use `.env.example` with placeholders only.
3. **No CI configuration.** This repository deliberately has no GitHub
   Actions or other CI (see [docs/DECISIONS.md](docs/DECISIONS.md),
   D1). Pull requests that add workflows will not be merged.
4. **Tests with behavior changes.** A fix comes with a test that fails
   without it. Security controls are tested by their effect.
5. **Printed-code width.** Listing code stays within 72 characters a
   line.

## Workflow

```bash
make venv
# make your change and add a test
make verify                          # must pass
make verify-db                       # if you touched storage or SQL
make verify-docker                   # if you touched Docker or Compose
```

In the pull request, paste the last lines of `make verify` and say
which optional checks you ran. Do not claim a check you did not run.

## Style

flake8 with the settings in `setup.cfg`; standard library first; type
hints on public functions; docstrings that name the chapter a control
comes from.

## Conduct

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).
