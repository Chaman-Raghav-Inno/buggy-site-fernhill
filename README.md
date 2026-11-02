# buggy-site-fernhill: Fernhill Academy

Fernhill Academy is an online-learning site (course catalog, lesson player with notes, timed quizzes, file and
written assignments, a gradebook, certificates, a discussion forum and an instructor's grading page) with **40
functional bugs planted on purpose**, to measure how many the AI QA Scanner finds. It is the fourth benchmark site,
after [buggy-site](https://github.com/Chaman-Raghav-Inno/buggy-site) (Lumen Goods),
[buggy-site-taskline](https://github.com/Chaman-Raghav-Inno/buggy-site-taskline) (Taskline) and
[buggy-site-driftwood](https://github.com/Chaman-Raghav-Inno/buggy-site-driftwood) (Driftwood Stays). Its bugs live
in rules rather than broken buttons: quiz marking, attempt limits, late penalties, grade weights, dropped scores,
certificate eligibility and the instructor's grading, so finding them takes the published rules, arithmetic, a second
page or a second account.

[BUGS.md](BUGS.md) is the answer key: for each bug, the steps to reproduce, what should happen, what happens, its
severity, how hard it is to notice and where it is in the code. The site never serves that file, and nothing it
serves names or hints at a bug. The rules each bug breaks are published on the site (`/help`).

## Run it

```sh
python -m fernhill          # http://localhost:8083 (PORT changes the port)
```

Standard library only (Python 3.11+); no install step.

- Accounts (password `Fernhill@2026`, shown on the login page): `sara@fernhill.test` (student, halfway through
  Python Basics), `ian@fernhill.test` (instructor).
- Every visitor (cookie) gets a private copy of the demo world, dated around today, so parallel scans never see each
  other's changes. Both accounts share that copy within one browser, so grading as Ian shows up for Sara. A restart
  or redeploy resets everything.

## Deploy on Railway

New service → GitHub repo → this repository, then **Generate domain** under Networking. `railway.json` sets the
start command and health check (`/healthz`); no variables or volume are needed. Avoid redeploying while a scan runs.

## Development

```sh
pip install ruff pytest
ruff check . && ruff format --check .
pytest -q
```

`tests/test_fernhill.py` keeps the server-side bugs in place and checks that nothing served gives a bug away.
Server-side code marks each bug with a `BUG-nn` comment; the served files must not.
