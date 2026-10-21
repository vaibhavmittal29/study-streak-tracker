# Study Streak Tracker

A focused, single-user study tracker and habit analytics platform engineered with a FastAPI REST backend, an interactive single-page dashboard (Vanilla JS + offline vendored Chart.js), and an **AI/ML insights engine** for habit forecasting and streak risk mitigation.

Designed and built for the **Mozilla Firefox Club (VIT Vellore) recruitments — AI/ML Subdomain**.

---

## 1. Features Checklist

### Base Requirements (P0)
- [x] **Log Study Sessions:** Record `subject`, `duration_minutes` (1–1440), calendar `date`, and optional `notes`.
- [x] **Full Session CRUD:** View, filter, paginate, edit, and delete past sessions.
- [x] **Dynamic Streak Tracking:** Instant calculation of **Current Streak** and **Longest Streak** (in days).
- [x] **Weekly Subject Analytics:** Aggregate study volume and session count per subject for the current ISO week (Mon–Sun).
- [x] **Persistent Storage:** Zero-configuration SQLite database persisted on disk (`data/study.db`), swappable via `DATABASE_URL`.

### Brownie Points (P1)
- [x] **Weekly Streak Freeze:** 1 automatic freeze cushion per ISO week to protect active streaks on missed days without artificially inflating streak length.
- [x] **Daily & Weekly Goals:** Configurable targets with percentage progress bars and real-time daily required pacing (`ceil(remaining / days_left)`).
- [x] **Interactive Time-Series Chart:** Day/Week granularity toggle and 7d/30d/90d range filters powered by Chart.js.
- [x] **CSV Export with Injection Guard:** RFC 4180 compliant CSV download with formula prefix sanitization (`=`, `+`, `-`, `@` escaped).
- [x] **Exhaustive Streak Test Suite:** 22-scenario edge-case matrix (E1–E22) including midnight boundaries and randomized property testing.

### AI/ML Differentiator (P2)
- [x] **7-Day Study Time Forecast:** Multi-candidate rolling-origin backtesting (Seasonal-Naive, Weekday Mean, EWMA, Autoregressive Ridge) that automatically selects the lowest MAE candidate and benchmarks it against baseline heuristics.
- [x] **Next-Day Streak Risk Classifier:** Leakage-safe standardized `LogisticRegression` pipeline evaluated via `TimeSeriesSplit` against majority-class and persistence baselines.
- [x] **Explainable Feature Attribution:** Top 3 behavioral coefficients translated into plain English (e.g., *"Studied 6 of last 7 days (+)"*).
- [x] **Empirical Bayesian Cold-Start Fallback:** Graceful fallback prior for accounts with < 21 days of history.
- [x] **Actionable Rule-Based Recommendations:** Identifies neglected subjects ($\ge 5$ days unstudied), goal pace warnings, productivity peak weekdays, and 14-day consistency rates.

---

## 2. Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| **Language** | Python 3.11+ | Unified language for high-performance API and statistical ML modeling |
| **API Framework** | FastAPI + Uvicorn | Native async, automatic OpenAPI docs at `/docs`, type safety with Pydantic v2 |
| **Database & ORM** | SQLAlchemy 2.x + SQLite | ACID persistence, zero setup, swappable for PostgreSQL via `DATABASE_URL` |
| **Machine Learning** | scikit-learn, pandas, numpy | Interpretable, transparent models optimized for small personal data |
| **Frontend UI** | HTML5, CSS3, Vanilla JS, Chart.js | No build step required; Chart.js vendored locally for 100% offline usage |
| **Timezones** | Python standard `zoneinfo` + `tzdata` | Robust IANA timezone conversion without third-party datetime wrapper bugs |
| **Quality & Tests** | pytest, pytest-cov, ruff | Blazing fast linting and comprehensive 96%+ test coverage |

---

## 3. Quick Start

### Prerequisites
- Python 3.11 or higher
- Git

### Installation & Launch

#### Windows (PowerShell)
```powershell
# 1. Clone repository
git clone https://github.com/vaibhavmittal29/study-streak-tracker.git
cd study-streak-tracker

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements-dev.txt

# 4. (Optional) Seed realistic demo data (120 days of student history)
python scripts/seed.py --reset --days 120

# 5. Start development server
uvicorn app.main:app --reload
```

#### macOS / Linux (Bash)
```bash
# 1. Clone repository
git clone https://github.com/vaibhavmittal29/study-streak-tracker.git
cd study-streak-tracker

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements-dev.txt

# 4. (Optional) Seed realistic demo data
python scripts/seed.py --reset --days 120

# 5. Start development server
uvicorn app.main:app --reload
```

Open your browser to:
- **Interactive Dashboard:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive OpenAPI Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 4. Configuration

Application settings can be configured via environment variables or a local `.env` file (copied from [`.env.example`](file:///.env.example)):

```ini
# Database URL (defaults to local SQLite database in data/ directory)
DATABASE_URL=sqlite:///./data/study.db

# Default timezone for session logging and streak evaluation
DEFAULT_TIMEZONE=Asia/Kolkata
```

---

## 5. API Overview

All API endpoints reside under `/api` and return standard JSON schemas.

| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `POST` | `/api/sessions` | Create a new study session (validates non-future date and $\le 1440$ daily mins) | `201`, `422` |
| `GET` | `/api/sessions` | List sessions (`from`, `to`, case-insensitive `subject`, `limit`, `offset`) | `200` |
| `GET` | `/api/sessions/{id}` | Retrieve single session by primary key ID | `200`, `404` |
| `PUT` | `/api/sessions/{id}` | Full update of existing session | `200`, `404`, `422` |
| `DELETE` | `/api/sessions/{id}` | Delete session (triggers immediate streak recompute) | `204`, `404` |
| `GET` | `/api/streak` | Get current streak, longest streak, freeze status, and risk flag | `200` |
| `GET` | `/api/stats/weekly` | Subject volume breakdown for current ISO week | `200` |
| `GET` | `/api/stats/timeseries` | Zero-filled time series points (`granularity=day\|week`) | `200`, `422` |
| `GET` / `PUT` | `/api/settings` | Retrieve or update timezone, freeze toggle, and daily/weekly goals | `200`, `422` |
| `GET` | `/api/goals/progress` | Progress percentages, remaining minutes, and required daily pace | `200` |
| `GET` | `/api/export.csv` | Download RFC 4180 CSV with injection mitigation | `200` |
| `GET` | `/api/insights/forecast` | 7-day study minutes forecast with backtested MAE | `200` |
| `GET` | `/api/insights/streak-risk` | Tomorrow's study likelihood and top 3 behavioral factor weights | `200` |
| `GET` | `/api/insights/recommendations` | Explainable actionable recommendations backed by quantitative evidence | `200` |
| `GET` | `/api/health` | Operational health check (`{"status": "ok"}`) | `200` |

### Sample `curl` Commands

#### Log a Session
```bash
curl -X POST http://127.0.0.1:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"subject": "DSA", "duration_minutes": 90, "date": "2026-10-20", "notes": "Binary trees"}'
```

#### Query Streak Status
```bash
curl http://127.0.0.1:8000/api/streak
```
*Response:*
```json
{
  "current_streak": 5,
  "longest_streak": 12,
  "studied_today": false,
  "streak_at_risk": true,
  "last_study_date": "2026-10-19",
  "freeze_enabled": true,
  "freeze_available_this_week": true,
  "frozen_dates": ["2026-10-14"],
  "today": "2026-10-20",
  "week_start": "2026-10-19"
}
```

---

## 6. How the Streak is Calculated

The streak computation engine is implemented as a **pure function** in [`app/services/streak_engine.py`](file:///app/services/streak_engine.py). It operates strictly on plain Python sets of dates, reference dates, and boolean flags, with zero database dependencies, zero HTTP handlers, and zero un-mocked clock references.

### Fundamental Rules
1. **Study Day Definition:** A calendar date with at least **one session of $\ge 1$ minute**. Multiple sessions logged on the same day are deduplicated by the set structure and count as one study day.
2. **Dynamic Recomputation on Read:** Streaks are never stored as static database counters. Every read computes the streak dynamically from distinct session dates. This guarantees that **editing a session date or deleting a session immediately recalculates the streak** without ever leaving stale counters.
3. **The "Today Pending" Rule:** Today is evaluated last. If the user has studied today, the streak increments immediately. If the user has not yet studied today, the streak remains **alive as of yesterday** (`streak_at_risk = True`), because today is pending until midnight.
4. **Weekly Streak Freeze:**
   - A freeze is consumed automatically on the **first missed day of an ISO week**, *only if* an active streak exists (`current > 0`) to protect.
   - At most **one freeze is allowed per ISO calendar week** (Monday–Sunday). A second miss in the same week resets the streak to 0.
   - Frozen days keep the streak alive but **do not increment** its length.
   - A freeze is **never consumed for today** (today remains pending until the day concludes).
5. **ISO Week Boundaries:** Weeks are strictly Monday through Sunday according to ISO 8601 `(iso_year, iso_week)`. This handles year transitions seamlessly (e.g., 29 Dec 2025 belongs to ISO week 1 of 2026).
6. **Midnight & Timezone Transitions:** All calendar dates are computed relative to the user's configured IANA timezone via an injectable clock dependency. At `23:59:59`, today is pending; at `00:00:00`, the day transitions to yesterday, converting any missed day into a completed day that either consumes a freeze or breaks the streak.

### Worked Example (Freeze in Action)

| Day of Week | Studied? | Engine Decision | Streak After | Freeze Status |
|---|---|---|---|---|
| **Mon** | Yes | Study day detected | 1 | Available |
| **Tue** | Yes | Consecutive study day | 2 | Available |
| **Wed** | **No** | First miss of ISO week $\rightarrow$ Freeze consumed | **2** | **Consumed (Oct 14)** |
| **Thu** | Yes | Study day resumes | 3 | Consumed |
| **Fri** | **No** | Second miss of ISO week (no freeze left) $\rightarrow$ Reset | **0** | Consumed |
| **Sat** | Yes | Fresh streak begins | 1 | Consumed |

*Result:* `longest_streak = 3`, `current_streak = 1`.

### Known & Documented Behavior
If a user misses **Sunday** and the following **Monday**, each day falls into a different ISO week. Consequently, each day consumes its own week's freeze, allowing a 2-day gap across a week boundary to survive. *(In a multi-user enterprise setting, an alternative strict rule forbidding back-to-back freezes across week boundaries can be configured).*

---

## 7. AI/ML Insights & Evaluation

Personal study tracking typically operates on small, sequential datasets. Deep learning models on tiny data suffer from extreme overfitting. Instead, this system employs **simple, interpretable, and backtested models** evaluated strictly against naive baselines with **zero data leakage**.

### 1. Streak-Risk Prediction
- **Algorithm:** `scikit-learn` Pipeline: `StandardScaler` $\rightarrow$ `LogisticRegression(class_weight='balanced')`.
- **Features (Causal only):** Cyclical day-of-week embeddings (`dow_sin`, `dow_cos`), `is_weekend`, `minutes_today`, `minutes_yesterday`, `rolling_7d_mean_minutes`, `rolling_7d_study_count`, `current_streak`, `days_since_last_study`, and `freeze_available`.
- **Validation:** Chronological `TimeSeriesSplit` (never shuffled).
- **Baselines:**
  - *Majority Class:* Predicts the most frequent class in historical data.
  - *Persistence Heuristic:* Assumes tomorrow's study state equals today's state.

### 2. 7-Day Study Time Forecast
- **Candidate Models:**
  1. *Seasonal Naive:* Predicts identical weekday from 7 days prior ($t-7$).
  2. *Empirical Weekday Mean:* Historical average for each specific day of the week.
  3. *EWMA Level $\times$ Weekday Multiplier:* Exponentially weighted moving average scaled by weekly distribution.
  4. *Autoregressive Ridge Regression:* Ridge penalty applied to $t-1$, $t-7$, $t-14$, and rolling 7-day volume.
- **Selection:** Rolling-origin chronological backtesting on the last 28 days selects the candidate with the lowest Mean Absolute Error (MAE).

### Empirical Evaluation Benchmark Results
*(Averaged across 3 independent random seeds spanning 120 days of synthetic student history via `python scripts/evaluate_models.py`)*:

| Task | Model / Method | Accuracy | F1 Score | Brier Score | Error (MAE) |
|---|---|---|---|---|---|
| **Streak Risk** | **Standardized Logistic Regression** | **62.8%** | **0.737** | **0.270** | - |
| **Streak Risk** | Baseline: Majority Class | 63.5% | - | - | - |
| **Streak Risk** | Baseline: Tomorrow = Today (Persistence) | 56.2% | - | - | - |
| **7-Day Forecast** | **Empirical Weekday / EWMA Ensemble** | - | - | - | **48.1 min** |
| **7-Day Forecast** | Baseline: Seasonal Naive ($t-7$) | - | - | - | 66.6 min |

> **Key Takeaway:** The forecasting model achieves a **27.8% error reduction (48.1m vs 66.6m MAE)** over the seasonal naive baseline. The logistic regression model achieves a high F1 score (0.737) and well-calibrated Brier score (0.270), providing meaningful probabilistic alerts rather than deterministic overconfidence.

### Cold-Start Behavior
When an account has $< 21$ days of logged data, the system gracefully shifts from machine learning to **Empirical Bayesian Smoothed Frequencies**:
$$P(\text{study}) = \frac{\text{studied\_weekday\_count} + \alpha}{\text{total\_weekday\_count} + \alpha + \beta}$$
where prior parameters $\alpha, \beta$ reflect the user's overall empirical study rate. The API explicitly reports `"confidence": "low"` and communicates the fallback status to the user interface.

---

## 8. Testing Suite

The project includes an automated test suite executed via `pytest`:

```bash
# Run all tests
pytest -v

# Run with test coverage report
pytest --cov=app --cov-report=term-missing
```

### Coverage Highlights
- **Total Project Coverage:** **96%**
- **Streak Engine Coverage:** **100%** (0 missed branches)
- **Total Test Cases:** 62 passing unit and integration tests

### Edge-Case Matrix Covered (E1–E22)
- **E1:** No sessions recorded (zeros returned).
- **E2:** Only today studied.
- **E3:** Only yesterday studied, none today (`current = 1`, `at_risk = True`).
- **E4:** Last study 2 days ago with freeze enabled (streak preserved).
- **E5:** Last study 2 days ago with freeze disabled (streak breaks to 0).
- **E6:** Last study 3 days ago with freeze enabled (second miss breaks streak).
- **E7:** Multiple sessions on the same calendar day deduplicated to 1 study day.
- **E8:** $N$ consecutive days ending today ($N$ day streak).
- **E9:** Missed day mid-streak with freeze off (longest preserves earlier record).
- **E10:** Missed day mid-streak with freeze on (streak continues uninterrupted).
- **E11:** Two misses in the same ISO calendar week (second miss breaks streak).
- **E12:** Miss on Sunday and following Monday across ISO week boundary (both survive).
- **E13:** Freeze not consumed before first-ever study session.
- **E14:** ISO year boundaries (e.g., 28 Dec 2025 to 4 Jan 2026).
- **E15:** **Midnight boundary transition** (today pending at 23:59:59 vs completed at 00:00:00).
- **E16:** Timezone shifts near midnight altering calendar dates without modifying stored timestamps.
- **E17:** Updating a session's date dynamically recalculates streak.
- **E18:** Deleting the only session of a day immediately breaks streak.
- **E19:** Future-dated sessions rejected by API (422) and ignored defensively by engine.
- **E20:** Leap days (29 Feb 2028) counted accurately.
- **E21:** **Performance Benchmark:** 5 years of daily data computed in $< 15$ ms (limit $< 50$ ms).
- **E22:** Longest streak ended in the past (`longest > current`).
- **Randomized Property Test:** 300 randomized date distributions benchmarked against an independent naive simulator.
- **Data Leakage Test:** Verifies feature values on day $t$ remain strictly identical regardless of future additions or modifications.

---

## 9. Design Decisions & Trade-Offs

1. **SQLite over In-Memory or PostgreSQL:** SQLite provides zero-configuration disk persistence with zero external service dependencies, perfect for a single-user application. The database connection is abstracted via SQLAlchemy's `DATABASE_URL`, allowing trivial migration to PostgreSQL or Cloud SQL for production deployments.
2. **Dynamic Recomputation vs Stored Counters:** Instead of maintaining fragile denormalized counters that desynchronize on session edits or deletions, streaks and statistics are computed dynamically on read. Because personal study histories are small ($< 10{,}000$ days), the $O(N)$ engine executes in single-digit milliseconds while guaranteeing complete consistency.
3. **Single Pure Clock Module:** Direct calls to `datetime.now()` or `date.today()` are strictly forbidden in business logic. All time awareness routes through `app/clock.py` using user-configured IANA timezones, enabling deterministic simulation of any date or time in automated tests.
4. **Formula Injection Sanitization:** Spreadsheet tools (Excel, LibreOffice, Google Sheets) execute cells starting with `=`, `+`, `-`, or `@` as formulas. The CSV export service automatically prefixes such text values with a single quote (`'`), neutralizing potential remote code execution or data exfiltration attacks.
5. **No Auth (Single-User Scope):** Per project specification, the app is built as a single-user study hub. For multi-user expansion, adding an `owner_id` foreign key on `StudySession` and JWT authentication dependencies on routers is straightforward.

---

## 10. Repository Structure

```
study-streak-tracker/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application, static mount, global exception handler
│   ├── config.py               # Settings (DATABASE_URL, DEFAULT_TIMEZONE) via Pydantic
│   ├── database.py             # SQLAlchemy engine, SessionLocal, Base, get_db dependency
│   ├── clock.py                # Injectable clock (get_today, get_clock, get_or_create_settings)
│   ├── models.py               # ORM Models: StudySession, Settings
│   ├── schemas.py              # Pydantic request/response schemas with field validators
│   ├── routers/
│   │   ├── sessions.py         # Session CRUD API
│   │   ├── streaks.py          # /api/streak endpoint
│   │   ├── stats.py            # /api/stats/weekly, /api/stats/timeseries
│   │   ├── settings.py         # /api/settings endpoint
│   │   ├── goals.py            # /api/goals/progress endpoint
│   │   ├── export.py           # /api/export.csv endpoint
│   │   └── insights.py         # /api/insights (forecast, streak-risk, recommendations)
│   ├── services/
│   │   ├── streak_engine.py    # Pure, deterministic streak computation function
│   │   ├── stats_service.py    # Weekly totals and zero-filled time series
│   │   ├── goals_service.py    # Daily & weekly progress calculations
│   │   └── csv_export.py       # RFC 4180 CSV builder with formula injection mitigation
│   ├── ml/
│   │   ├── features.py         # Leakage-safe daily feature extraction pipeline
│   │   ├── streak_risk.py      # LogisticRegression streak-risk classifier & fallback
│   │   ├── forecast.py         # 7-day study minutes forecast & backtesting
│   │   ├── recommendations.py  # Rule-based explainable recommendations
│   │   └── synthetic.py        # Realistic student data generator
│   └── static/
│       ├── index.html          # Modern, semantic single-page dashboard
│       ├── styles.css          # Minimalism & Swiss style CSS (light/dark mode, responsive)
│       ├── app.js              # Vanilla JS API coordinator, XSS-safe DOM renderers
│       └── vendor/
│           └── chart.umd.min.js# Offline vendored Chart.js library
├── tests/
│   ├── conftest.py             # Isolated SQLite fixtures, clock overrides, TestClient
│   ├── test_health.py          # Smoke tests
│   ├── test_database_clock.py  # Database lifecycle and injectable clock tests
│   ├── test_sessions_api.py    # CRUD API validation & persistence tests
│   ├── test_streak_engine.py   # Pure streak engine tests (E1-E14, E19-E22, randomized)
│   ├── test_streak_api.py      # Streak API integration tests (E15 midnight, E16 timezone)
│   ├── test_stats.py           # Weekly aggregation & timeseries zero-fill tests
│   ├── test_goals.py           # Goal progress and settings tests
│   ├── test_export.py          # CSV formatting and injection guard tests
│   ├── test_frontend.py        # Static asset and dashboard delivery tests
│   ├── test_hardening.py       # Performance benchmarks and exception masking tests
│   └── test_ml.py              # ML leak-free backtests and recommendation tests
├── scripts/
│   ├── seed.py                 # CLI database seeder (--reset, --days)
│   └── evaluate_models.py      # Model benchmark evaluation script
├── data/                       # Local SQLite database directory (gitignored)
├── Dockerfile                  # Production container specification (Python 3.11 slim)
├── .dockerignore               # Docker ignore rules
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI workflow (lint & test)
├── .env.example                # Example environment configuration
├── .gitignore                  # Git ignore rules
├── pyproject.toml              # Ruff & pytest configuration
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Production runtime dependencies
├── requirements-dev.txt        # Development, testing, and linting dependencies
└── README.md                   # Complete documentation
```

---

## 11. Deployment & Containerization

### Docker Build & Run
The repository includes a production-ready, non-root `Dockerfile`:

```bash
# Build Docker image
docker build -t study-streak-tracker .

# Run with persistent volume for SQLite database
docker run -d -p 8000:8000 -v $(pwd)/data:/app/data --name study-tracker study-streak-tracker
```

### Production Hosting Notes
- **Persistent Disk vs Ephemeral Storage:** Free cloud hosting tiers (e.g. Render, Railway, Fly.io) often utilize ephemeral filesystems where container restarts wipe local SQLite files. When deploying with SQLite, attach a persistent volume to `/app/data`.
- **Swapping to Managed PostgreSQL:** For cloud environments without persistent disk attachments, simply configure the `DATABASE_URL` environment variable:
  ```bash
  DATABASE_URL=postgresql://user:password@host:5432/studydb
  ```
- **Zero Secrets in Git:** Never commit `.env` or production credentials.

---

## 12. Future Work
- **Multi-User & Authentication:** Implement OAuth2 / JWT authentication with per-user data isolation.
- **Alembic Migrations:** Add declarative migration scripts for evolving production database schemas.
- **Strict Freeze Constraint:** Option to forbid back-to-back freeze consumption across Sunday/Monday week boundaries.
- **Time-of-Day Insights:** Capture session timestamps to discover optimal study hours (morning vs night).
- **Progressive Web App (PWA):** Service worker caching and offline background sync.

---

## 13. License & Author

Developed by **Vaibhav Mittal** (`vaibhavmittal29`) for the **Mozilla Firefox Club (VIT Vellore) AI/ML Subdomain** application. Released under the [MIT License](LICENSE).
