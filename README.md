# ACME Salary Management

A web app for ACME's HR manager to manage pay for **10,000 employees in 10 countries**.

It keeps every salary in its own country's currency. It shows pay insights in local currency and
in US dollars, and flags people and teams paid below their salary band. Viewers see totals but
never anyone's salary.

Built for the Incubyte take-home with FastAPI, Next.js and SQLite (Turso in production), **test first**.

|                 |                                                                                                            |
| --------------- | ---------------------------------------------------------------------------------------------------------- |
| **Live app**    | https://salary-management-seven.vercel.app                                                                 |
| **Video demo**  | _link coming soon_                                                                                         |
| **Demo logins** | `admin@acme.example`, `hr@acme.example`, `viewer@acme.example`. The passwords are in the submission email. |

## A 5-minute tour

1. **Sign in as the HR manager** (`hr@acme.example`). You land on **Insights**: headcount and
   payroll per country, in local currency and in USD, with the exchange-rate date shown.
2. **Pay equity:** pick Germany. The Customer Success team sits at about **0.93 of its salary
   band** while other teams are near 1.00. This underpaid team is planted in the seed data on purpose.
3. **Employees:** search a name, filter by country or department, and open someone. You see their
   salary history. Click **Record salary change** to add a raise; history is never overwritten.
4. **Import:** upload a CSV or Excel file. You get a check of every row first, then it saves all
   rows or none.
5. **Ask about pay:** type a question like _"Are we underpaying anyone in Germany?"_. The answer
   uses the same numbers as the dashboard and shows how it got them.
6. **Sign in as the viewer** (`viewer@acme.example`). Salaries are gone from every screen, and
   groups smaller than 5 people are hidden, so no one's pay can be worked out.

## What it does

- **Employees:** add, edit, terminate and reactivate; search, filter, sort and page through 10,000 people.
- **Salary history:** every change adds a new record. Nothing is edited or deleted.
- **Money done right:** amounts are whole numbers of cents (never floats), each with its currency.
  US dollar totals use a dated exchange rate.
- **Insights:** headcount, payroll, median and average pay by country, department and job role.
- **Pay equity:** each person's pay compared to the band for their role, level and country.
- **Roles:** Admin, HR manager and Viewer. The backend enforces what each role sees; the screen only hides buttons.
- **Import and export:** CSV and Excel.
- **Ask about pay:** questions in plain English, answered by read-only tools (Google Gemini).
- **Audit log:** every change records who did what, in the same database transaction.
- **Works on phones:** every screen works from 360 px wide.

## How it is built

```
Browser → Next.js (frontend/) → FastAPI (backend/) → SQLite locally, Turso in production
```

- **One Vercel project, one address.** `/api/*` goes to FastAPI, everything else goes to Next.js.
  The login cookie can't be read by JavaScript, and it works in Safari and Firefox.
- **The backend is the only authority.** Permissions, hiding salaries and every figure are decided
  in FastAPI. Next.js only displays what it gets.
- **Clear layers in the backend:** router → service → repository → database. The money and
  statistics code is plain Python with no database access, so it is easy to test.
- **Seed data:** `make seed` creates the same 10,000 employees every time (fixed random seed). 3% of
  them have left the company, so 9,700 show as active.

More: [architecture](docs/05-architecture.md), [data model](docs/06-data-model.md),
[decisions (ADRs)](docs/adr/).

## How I worked

- **Test first:** each behaviour has a `test:` commit before its `feat:` or `fix:` commit. The
  history has 384 `test:` and 264 `feat:` commits (`git log --oneline`).
- **Tests:** 1,391 backend tests (including a check of every endpoint for every role) and 453
  frontend tests, plus an end-to-end browser test on desktop and phone sizes. Backend coverage is 99%.
- **Planning before code:** a [one-page requirements doc](docs/02-requirements-one-pager.md) was
  the first commit, and every decision has a short record in [docs/adr/](docs/adr/).
- **AI use:** built with Claude Code. The [prompt log](docs/ai/prompt-log.md) shows the real
  prompts, including where the AI was wrong.

## Run it locally

You need [uv](https://docs.astral.sh/uv/), Node 22 (`corepack enable`), Make and git.

```bash
make setup   # install everything
make seed    # create the 10,000 employees (about 4 seconds)
make dev     # API on :8000, app on http://localhost:3000
```

Local logins use the same emails, with the passwords `change-me-admin`, `change-me-hr` and
`change-me-viewer`. These only work locally; production refuses them.

| Command       | What it does                                             |
| ------------- | -------------------------------------------------------- |
| `make verify` | Lint, type checks and all tests (run before every merge) |
| `make test`   | Backend and frontend tests                               |
| `make e2e`    | End-to-end browser test                                  |
| `make help`   | Every command                                            |

## What I left out

To ship in 1–2 days, I cut these (full list in [docs/README.md](docs/README.md)):

- An admin screen for users, exchange rates and the audit log. The data and the API exist; there is no screen yet.
- A salary histogram and a raises report.
- More end-to-end tests. There is one main flow; API and component tests cover the rest.
- Import only adds new employees; it doesn't update existing ones.
- The pay-equity "all groups" view returns about 1,200 groups at once and is slower than its
  target. Paging would fix it ([performance notes](docs/19-performance.md)).

Trade-offs are explained in [docs/20-trade-offs.md](docs/20-trade-offs.md).

## Documentation

| Doc                                                        | What's in it                                     |
| ---------------------------------------------------------- | ------------------------------------------------ |
| [docs/README.md](docs/README.md)                           | Index of all docs and the v1 scope               |
| [docs/00-assessment-brief.md](docs/00-assessment-brief.md) | The brief, and where each requirement is covered |
| [docs/glossary.md](docs/glossary.md)                       | Names, roles, numbers and error codes            |
| [docs/adr/](docs/adr/)                                     | Architecture decisions                           |
| [docs/17-deployment.md](docs/17-deployment.md)             | How it is deployed (Vercel + Turso, Mumbai)      |
| [docs/ai/prompt-log.md](docs/ai/prompt-log.md)             | How AI was used                                  |
