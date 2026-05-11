<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a0a0f,30:0d1f3c,60:0a3d2e,100:0a0a0f&height=200&section=header&text=Qolyx&fontSize=72&fontColor=ffffff&fontAlignY=38&desc=AI-Native%20Data%20Reliability%20Platform&descAlignY=58&descSize=18&animation=fadeIn" width="100%"/>

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-00d4aa?style=for-the-badge)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Apache Airflow](https://img.shields.io/badge/Apache-Airflow-017CEE?style=for-the-badge&logo=apache-airflow&logoColor=white)](https://airflow.apache.org)
[![dbt Core](https://img.shields.io/badge/dbt-Core-FF694B?style=for-the-badge&logo=dbt&logoColor=white)](https://getdbt.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14+-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Status](https://img.shields.io/badge/Status-Building%20in%20Public-00d4aa?style=for-the-badge)](#build-status)

<br/>

<h2>Your data pipelines run. But can you trust what they produce?</h2>

<p align="center" style="max-width:680px; color:#8b949e; font-size:16px; line-height:1.6;">
Qolyx is an open-source data reliability platform that gives every dataset a <b>Trust Score</b> —
a single explainable number from 0 to 100. It detects anomalies automatically,
enforces data contracts, traces root causes through lineage,
and tells you exactly why your data cannot be trusted — before it reaches your dashboards.
</p>

<br/>

[**Quick Start**](#quick-start) · [**How It Works**](#how-it-works) · [**Architecture**](#architecture) · [**Trust Score**](#trust-score) · [**Build Status**](#build-status) · [**Contributing**](#contributing)

<br/>

</div>

---

## The Problem

```
Pipeline:  ✅ completed successfully
Status:    ✅ all tasks passed
Data:      ❌ completely wrong
```

Every data team has this nightmare. A pipeline runs. Data loads. Dashboards update. Business decisions are made. Three days later — the numbers were wrong.

A column was silently renamed upstream. A volume spike doubled every metric. A schema change broke 12 downstream models and nobody noticed. The finance team presented incorrect quarterly numbers to the board.

**This is not a monitoring problem. It is a trust problem.**

Existing solutions are either too expensive ($50,000/year enterprise contracts), require manual rule writing for every check, or produce walls of anomaly logs without a clear answer to the only question that matters:

> *"Can I trust this data right now?"*

**Qolyx answers that question. Automatically. For every dataset. Every pipeline run.**

---

## See It In Action

```bash
# One command. Full platform. Working demo.
git clone https://github.com/Ayush-kushwah/qolyx
cd qolyx && make demo
```

Within 5 minutes, you will see this on your screen:

```
╔══════════════════════════════════════════════════════════════╗
║                    QOLYX — LIVE DASHBOARD                    ║
╠══════════════════════════════════════════════════════════════╣
║  Dataset: sales_transactions          Trust Score: 41 ██░░░  ║
║  Status:  CRITICAL                    Was: 91  Now: 41       ║
╠══════════════════════════════════════════════════════════════╣
║  Score dropped 50 points because:                            ║
║                                                              ║
║  ├── Row count anomaly        -20pts                         ║
║  │   Expected: 380–420 rows                                  ║
║  │   Received: 12,847 rows  (+3,212%)                        ║
║  │                                                           ║
║  ├── Schema contract violated -10pts                         ║
║  │   Column 'revenue_usd' was renamed to 'amount'            ║
║  │                                                           ║
║  ├── dbt uniqueness test      -7pts                          ║
║  │   Duplicate transaction_ids detected                      ║
║  │                                                           ║
║  └── Statistical anomaly      -5pts                          ║
║      revenue_usd distribution shifted 340%                   ║
║                                                              ║
║  Affected downstream assets:                                 ║
║  ├── executive_revenue_dashboard                             ║
║  ├── monthly_finance_report                                  ║
║  └── ml_churn_model_features                                 ║
║                                                              ║
║  Root cause: Duplicate records in transactions.csv           ║
║  Traced to:  DAG 'ingest_transactions' — 2 hours ago         ║
╚══════════════════════════════════════════════════════════════╝
  ✉ Slack alert dispatched  ·  Timeline updated  ·  Incident #47 created
```

This is not a log. This is a diagnosis.

---

## How It Works

Qolyx wraps around your existing data stack. Every pipeline run passes through 8 sequential steps:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   Data Sources          Orchestration          Transformation           │
│  ┌──────────┐          ┌──────────────┐       ┌──────────────────┐     │
│  │ REST API │──────┐   │    Apache    │──────▶│   dbt Core       │     │
│  │ CSV/File │──────┼──▶│    Airflow   │       │ Bronze→Silver    │     │
│  │ Database │──────┘   │              │       │        →Gold     │     │
│  └──────────┘          └──────┬───────┘       └────────┬─────────┘     │
│                               │                        │               │
│                               ▼                        │               │
│                    ┌──────────────────┐                │               │
│                    │  Data Contracts  │◀───────────────┘               │
│                    │  Validation Gate │                                 │
│                    │  schema·types·   │                                 │
│                    │  nullability·SLA │                                 │
│                    └────────┬─────────┘                                │
│                             │  BLOCKS pipeline on violation             │
│                             ▼                                           │
│              ┌──────────────────────────────┐                          │
│              │       AI Quality Engine       │                          │
│   ┌──────────┴──────────┐  ┌────────────────┴──────┐                  │
│   │  Anomaly Detection  │  │   Dataset Profiling    │                  │
│   │  Isolation Forest   │  │   Baseline Learning    │                  │
│   │  PSI · Volume check │  │   Schema Drift Detect  │                  │
│   └──────────┬──────────┘  └────────────────┬───────┘                 │
│              └──────────────┬────────────────┘                         │
│                             │                                           │
│         ┌───────────────────┤                                           │
│         │  Lineage Engine   │  ← runs in parallel                      │
│         │  OpenLineage      │                                           │
│         │  Graph traversal  │                                           │
│         └─────────┬─────────┘                                          │
│                   │                                                     │
│                   ▼                                                     │
│   ┌───────────────────────────────────────────────────────────────┐    │
│   │                    TRUST SCORE ENGINE                         │    │
│   │                                                               │    │
│   │   trust_score = 100 - contract_penalty - freshness_penalty    │    │
│   │                      - volume_penalty - anomaly_penalty       │    │
│   │                      - dbt_penalty                            │    │
│   │                                                               │    │
│   │   Always explainable. Never cached. Never black-box.          │    │
│   └───────────────────────┬───────────────────────────────────────┘    │
│                           │                                             │
│              ┌────────────┴────────────┐                               │
│              ▼                         ▼                               │
│   ┌──────────────────┐    ┌────────────────────────┐                  │
│   │ Incidents Module │    │   Data Reliability     │                  │
│   │ RCA generation   │───▶│   Timeline             │                  │
│   │ Severity grading │    │   Per-dataset history  │                  │
│   └──────────────────┘    └────────────┬───────────┘                  │
│                                        │  always last                  │
│                                        ▼                               │
│                            ┌───────────────────────┐                  │
│                            │   Alert Dispatch       │                  │
│                            │   Slack · Email · Hook │                  │
│                            └───────────────────────┘                  │
│                                                                         │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                    ┌───────────┴────────────┐
                    │      FastAPI           │
                    │      Backend           │
                    └───────────┬────────────┘
                                │
                    ┌───────────┴────────────┐
                    │     Next.js            │
                    │     Dashboard          │
                    │  Trust Score · Timeline│
                    │  Lineage Explorer · RCA│
                    └────────────────────────┘
```

---

## Trust Score

The Trust Score is the central identity of Qolyx. It is always **explainable**, always **fresh**, and calculated from **five independent signals** — no black-box ML, no double-counting.

```python
trust_score = 100

# 1. Contract violations (schema, types, nullability)
trust_score -= min(40, violations_count * 10)

# 2. Freshness (time since last update vs SLA)
trust_score -= 0 if on_time else 15 if slightly_late else 30

# 3. Volume anomaly (row count vs 30-day baseline)
trust_score -= 0 if <10% deviation else 10 if <30% else 20 if <50% else 30

# 4. Statistical anomalies (Isolation Forest — numeric columns only)
trust_score -= min(20, anomalous_columns * 5)

# 5. dbt test failures
trust_score -= min(20, failed_tests * 7)

trust_score = max(0, min(100, trust_score))  # clamped to [0, 100]
```

| Score | Status | Action |
|---|---|---|
| 80 – 100 | 🟢 **HEALTHY** | No action required |
| 60 – 79 | 🟡 **WARNING** | Review recommended |
| 40 – 59 | 🟠 **DEGRADED** | Investigation required |
| 0 – 39 | 🔴 **CRITICAL** | Pipeline quarantined · Incident created · Alert fired |

Every score change returns a human-readable breakdown:

```json
{
  "trust_score": 41,
  "trust_score_delta": -50,
  "breakdown": {
    "contract_penalty": -10,
    "freshness_penalty": 0,
    "volume_penalty": -20,
    "anomaly_penalty": -13,
    "dbt_penalty": -7
  },
  "explanation": "Trust score dropped 91 → 41 because: row count anomaly (+3212% above baseline), schema contract violated (column renamed), dbt uniqueness test failed (duplicate transaction_ids), statistical anomaly in revenue_usd column."
}
```

---

## Data Reliability Timeline

Every pipeline run produces a timestamped event story — not just a log, a narrative:

```
09:02:01  Pipeline started          sales_transactions · run_id: a4f7c2
09:02:04  Contract validated        ❌ FAILED — column 'revenue_usd' not found
09:02:04  Trust Score recalculated  91 → 81  (contract_penalty: -10)
09:02:05  Anomaly detection         ❌ Row count: 12,847 (expected 380–420)
09:02:05  Trust Score recalculated  81 → 41  (volume_penalty: -20, anomaly_penalty: -13, dbt_penalty: -7)
09:02:05  Lineage traced            3 downstream assets identified
09:02:06  Incident created          #47 · CRITICAL · RCA generated
09:02:06  Timeline updated          6 events recorded
09:02:07  Alert dispatched          Slack #data-alerts · email: data-team@company.com
```

---

## Key Features

| Feature | Description |
|---|---|
| **Trust Score** | Single 0–100 reliability metric per dataset. Always explainable. Never black-box. |
| **Zero Rule Writing** | AI learns what normal looks like from your data automatically. No manual thresholds. |
| **Data Contracts** | Enforce schema, type, and nullability agreements. **Block** pipelines on violation — not just alert. |
| **Anomaly Detection** | Isolation Forest + PSI + volume checks. Learns baseline in 7 days. Works on any numeric column. |
| **Data Lineage** | OpenLineage integration. Traces every column to its source. Shows every affected downstream asset. |
| **Root Cause Analysis** | Plain English. Not "anomaly_score: 0.94" — "revenue column has 340% more rows than expected, traced to commit abc1234." |
| **Reliability Timeline** | Event-by-event story per dataset. Replayable. Auditable. |
| **Full Observability** | Prometheus metrics + Grafana dashboards for pipeline health, DQ scores, and SLA tracking. |
| **make demo** | One command. Full platform. Synthetic data. Injected failures. Live Trust Score collapse. Under 5 minutes. |

---

## Architecture

### Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Orchestration** | Apache Airflow | Pipeline scheduling, retries, DAG management |
| **Transformation** | dbt Core | Bronze → Silver → Gold data models + tests |
| **Contracts** | Custom + Great Expectations | Schema enforcement, pipeline gating |
| **Anomaly Detection** | Isolation Forest (scikit-learn) | Statistical anomaly detection, baseline learning |
| **Lineage** | OpenLineage | Dataset lineage tracking and graph storage |
| **Backend** | FastAPI + Python 3.11 | REST API, business logic, event orchestration |
| **Database** | PostgreSQL + Alembic | Primary store + migrations |
| **Queue** | Redis | Background task management |
| **Frontend** | Next.js 14 + TypeScript | Dashboard, lineage explorer, incident view |
| **Observability** | Prometheus + Grafana | Platform and pipeline monitoring |
| **Infrastructure** | Docker Compose | Local development, demo environment |

### Project Structure

```
qolyx/
├── backend/
│   ├── modules/
│   │   ├── ingestion/           # Airflow DAG connectors + source adapters
│   │   ├── profiling/           # Dataset baseline learning + statistics
│   │   ├── anomaly_detection/   # Isolation Forest + PSI + volume checks
│   │   ├── contracts/           # Schema validation + pipeline gating
│   │   ├── lineage/             # OpenLineage integration + graph storage
│   │   ├── trust_scoring/       # Core scoring engine — protected module
│   │   ├── incidents/           # Incident lifecycle + RCA generation
│   │   ├── timeline/            # Per-dataset event history
│   │   └── alerts/              # Slack + email + webhook dispatch
│   ├── api/                     # FastAPI routes (zero business logic)
│   └── core/                    # Config · database · internal event bus
├── frontend/                    # Next.js 14 dashboard
├── dbt_project/                 # Bronze → Silver → Gold transformation models
├── airflow_dags/                # Pipeline DAG definitions
├── infra/                       # Docker Compose · Prometheus · Grafana configs
├── demo/                        # Synthetic datasets + failure injection scripts
└── tests/                       # Full test suite mirroring backend/ structure
```

---

## Why Qolyx

| | Monte Carlo | Great Expectations | Soda Core | **Qolyx** |
|---|---|---|---|---|
| Open source | ❌ | ✅ | ✅ | ✅ |
| Zero rule writing | ✅ | ❌ | ❌ | ✅ |
| Single Trust Score | ❌ | ❌ | ❌ | ✅ |
| Explainable scoring | ❌ | ❌ | ❌ | ✅ |
| Pipeline blocking | ✅ | ✅ | ✅ | ✅ |
| Data lineage | ✅ | ❌ | ❌ | ✅ |
| Plain English RCA | ❌ | ❌ | ❌ | ✅ |
| Self-hostable | ❌ | ✅ | ✅ | ✅ |
| Price | $50K+/yr | Free | Free | **Free** |
| One-command demo | ❌ | ❌ | ❌ | ✅ |

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- 8GB RAM minimum
- 10GB free disk space

### Run the Demo

```bash
# Clone
git clone https://github.com/Ayush-kushwah/qolyx
cd qolyx

# Start everything — Airflow, dbt, FastAPI, Next.js, Prometheus, Grafana
make demo

# Open dashboard
open http://localhost:3000

# Open Grafana
open http://localhost:3001

# Open Airflow
open http://localhost:8080
```

The demo automatically:
1. Starts all services via Docker Compose
2. Seeds 3 pipelines with synthetic data (sales, inventory, weather)
3. Injects realistic failures: schema drift, null explosion, volume spike, freshness delay
4. Shows Trust Scores collapsing in real time
5. Generates incidents with root cause analysis
6. Fires simulated Slack alerts

### Connect Your Own Pipeline

```yaml
# qolyx/contracts/my_pipeline.yaml
dataset: sales_transactions
source: postgresql
schedule: "@hourly"
sla_hours: 2

contracts:
  schema:
    - name: transaction_id    type: integer   nullable: false   unique: true
    - name: revenue_usd       type: float     nullable: false
    - name: customer_id       type: integer   nullable: false
    - name: created_at        type: timestamp nullable: false

  volume:
    min_rows: 300
    max_rows: 600
    baseline_days: 30

  freshness:
    max_hours: 2
```

That is all Qolyx needs to start monitoring.

---

## Build Status

> **Building in public.** Every phase is git-tagged. Star the repo to follow progress. ⭐

| Phase | Status | Description |
|---|---|---|
| **Phase 1** — Repository + Governance | 🔄 In Progress | Repo, Docker skeleton, project structure |
| **Phase 2** — Backend Skeleton | ⏳ Pending | FastAPI, Alembic, database foundation, event bus |
| **Phase 3** — Ingestion + Bronze Layer | ⏳ Pending | 3 Airflow DAGs, raw data loading, error handling |
| **Phase 4** — dbt Transformations | ⏳ Pending | Bronze → Silver → Gold, CI/CD for models |
| **Phase 5** — Contracts Module | ⏳ Pending | Schema validation, pipeline gating, YAML contracts |
| **Phase 6** — Profiling + Anomaly Engine | ⏳ Pending | Baseline learning, Isolation Forest, PSI |
| **Phase 7** — Trust Score System | ⏳ Pending | Core scoring engine, explainability breakdown |
| **Phase 8** — Incidents + Timeline | ⏳ Pending | RCA generation, event timeline, severity grading |
| **Phase 9** — Lineage Tracking | ⏳ Pending | OpenLineage, graph traversal, affected assets |
| **Phase 10** — Frontend Dashboards | ⏳ Pending | Next.js, D3 lineage explorer, real-time updates |
| **Phase 11** — make demo | ⏳ Pending | One-command full platform demo experience |
| **Phase 12** — Open Source Launch | ⏳ Pending | Docs, contribution guide, community |

---

## Contributing

Contributions are welcome once Phase 3 is complete.

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/qolyx

# Install dependencies
cd qolyx && make install-dev

# Run tests
make test

# Start dev environment
make dev
```

Read [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

Free to use, modify, and distribute. Attribution required.

---

<div align="center">

<br/>

Built by [**Ayush Kushwah**](https://github.com/Ayush-kushwah) · [LinkedIn](https://linkedin.com/in/ayush-kushwah)

<br/>

*Open-source alternative to Monte Carlo Data ($1.6B valuation)*

*If Qolyx helps you trust your data, give it a ⭐*

<br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a0a0f,30:0d1f3c,60:0a3d2e,100:0a0a0f&height=100&section=footer" width="100%"/>

</div>
