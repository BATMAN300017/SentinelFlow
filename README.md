# SentinelFlow - The Self-Directed Fraud Investigation Platform

[![CI Pipeline](https://github.com/sentinelflow/sentinelflow-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/sentinelflow/sentinelflow-ai/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.4+-orange.svg)](https://scikit-learn.org/)

> **SentinelFlow ** is a production-inspired financial crime surveillance and self-directed fraud investigation command center. It bridges the gap between raw anomaly detection and final authorized case disposition.

---

## 1. Product Vision & Core Architecture

In modern financial crime and anti-money laundering (AML) operations, over 90% of alerts are false positives. Existing tools either act as opaque binary classifiers or dump raw tables onto overworked analysts.

SentinelFlow AI transforms the investigative process through four foundational pillars:


## 2. Differentiators

- **Investigation System, Not Just a Classifier**: Alerts automatically construct a formal case dossier with verified supporting and contradictory evidence.
- **Account-Specific MAD Anomaly Baselines**: Uses Median Absolute Deviation (MAD) robust z-scores rather than naive static amount cutoffs.
- **Topological Graph Intelligence**: Detects fan-in collection hubs, circular flow cycles, and rapid multi-hop mule forwarding.
- **Controlled Continuous Learning**: Enforces a strict label policy—only human-reviewed confirmed fraud and verified false positives enter the training pipeline. Inconclusive and unconfirmed cases are excluded to prevent feedback poisoning.
- **Zero Paid Dependencies**: Runs 100% locally with deterministic synthetic data, offline model training, and built-in interactive dashboard.

---

## 3. Technology Stack

- **Backend**: Python 3.12+, FastAPI, Pydantic v2, Scikit-learn, NumPy, Pandas, SciPy, SQLite3 (with zero-config fallback) and PostgreSQL support.
- **Security**: PBKDF2-SHA256 password hashing, HMAC bearer tokens, sensitive-field redaction in structured JSON logs.
- **Frontend / UI**: Embedded Responsive Command Center SPA with Tailwind CSS, SVG radial money-flow graphs, real-time SSE telemetry, and Next.js / TypeScript structure in `frontend/`.
- **Testing**: Complete automated test suite covering unit rules, anomalies, graph metrics, label policies, integration pipelines, and API endpoints (32 tests passing).

---

## 4. Quick Start & Launch

### Prerequisites
- Python 3.11+ (installed)
- Virtual environment (optional but recommended)

### 1-Minute Launch
```bash
# 1. Clone or navigate to the repository
cd sentinelflow-ai

# 2. Seed the deterministic demo database (100 customers, 150 accounts, 1000 transactions, 30 alerts, 10 cases)
python scripts/seed_demo_data.py

# 3. Launch the complete application
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

Open your browser at: **[http://localhost:8000/](http://localhost:8000/)** (or `/app`).

Interactive Swagger API Documentation: **[http://localhost:8000/docs](http://localhost:8000/docs)**.

## 5. Development Credentials for Local Demo

| Username | Password | Role | Permissions |
| :--- | :--- | :--- | :--- |
| `sarah_investigator` | `password123` | **Investigator** | View alerts, triage, add evidence, submit dispositions |
| `marcus_senior` | `password123` | **Senior Investigator** | All investigator permissions + peer review approval |
| `elena_admin` | `password123` | **Fraud Ops Admin** | Rule configuration, simulation control, model promotion |
| `arthur_auditor` | `password123` | **Auditor** | Read-only compliance access to cases and audit trail |

---

## 6. Deterministic Demo Scenarios

SentinelFlow includes 4 reproducible demo scenarios accessible via the UI or CLI:

### Scenario A: Rapid Fund Movement
```bash
python scripts/run_demo_scenario.py --scenario rapid_movement
```
- Injects a $16,500 inbound wire followed immediately by a $15,200 transfer to an external LLC.
- Triggers velocity and rapid-forwarding rules; automatically generates a Critical Alert and opens an investigation case.

### Scenario B: Connected Account Network (Mule Ring)
```bash
python scripts/run_demo_scenario.py --scenario connected_network
```
- Multiple source accounts funnel funds into a single collection hub while sharing a common device fingerprint (`DEV-CLUSTER-987`).
- Detected in Network Intelligence as a **Fan-In Collection Hub**.

### Scenario C: Legitimate Unusual Activity (False Positive Reduction)
```bash
python scripts/run_demo_scenario.py --scenario legitimate_unusual
```
- High-value luxury travel purchase on an established account.
- Flagged with low anomaly confidence, allowing the analyst to verify and close as `LEGITIMATE_ACTIVITY`, contributing to false-positive reduction.

---
There are 4 contributors which contributes to final result of a transaction. above 4 scenarios are from contributor 1 which holds 30% power in the main result.

## 7. Running Automated Tests

Run the complete 32-test unit and integration suite:
```bash
python backend/tests/run_tests.py
```

Output:
```text
test_alerts_list (integration.test_api.TestAPIEndpoints) ... ok
test_dashboard_summary (integration.test_api.TestAPIEndpoints) ... ok
test_full_investigation_lifecycle (integration.test_investigation_workflow) ... ok
test_idempotent_event_replay_does_not_duplicate (integration.test_transaction_pipeline) ... ok
test_suspicious_event_creates_alert (integration.test_transaction_pipeline) ... ok
test_cold_start_reports_low_history_confidence (unit.test_anomaly_detection) ... ok
test_significant_amount_deviation_detected (unit.test_anomaly_detection) ... ok
test_high_velocity_rule_triggers_above_threshold (unit.test_detection_rules) ... ok
test_shortest_path_discovery (unit.test_graph_analysis) ... ok
test_label_policy_confirmed_fraud_eligible (unit.test_feedback_learning) ... ok
test_model_promotion_gate_rejects_insufficient_samples (unit.test_feedback_learning) ... ok
...
Ran 32 tests in 0.030s
OK (All tests passed successfully!)
```

---

## 8. Repository Layout

```
sentinelflow-ai/
├── README.md                           # Master platform guide & architecture
├── LICENSE                             # MIT Open Source License
├── .env.example                        # Environment variables template
├── docker-compose.yml                  # Container orchestration
├── Makefile                            # Standard developer workflows
├── pyproject.toml                      # Python build configuration
├── package.json                        # Monorepo NPM workspace configuration
├── docs/                               # 12 detailed engineering documentation files
│   ├── architecture.md                 # System components & Mermaid sequence
│   ├── api-reference.md                # Comprehensive REST API contracts
│   ├── database-schema.md              # 27 relational tables & constraints
│   ├── detection-engine.md             # Hybrid risk scoring & calibration
│   ├── graph-intelligence.md           # Money-flow network topology
│   ├── learning-feedback.md            # Label policy & model promotion gates
│   ├── security.md                     # RBAC & log sanitization
│   ├── threat-model.md                 # Prompt injection & adversarial defense
│   ├── demo-script.md                  # 5-minute judge demonstration walkthrough
│   ├── judging-pitch.md                # Executive value proposition
│   └── test-plan.md                    # Verification matrix
├── backend/
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py                     # FastAPI application entrypoint
│   │   ├── core/                       # Database, security, permissions, logging
│   │   ├── api/v1/                     # REST API version 1 endpoint routers
│   │   ├── detection/                  # Multi-signal rules, MAD anomaly, ML, ensemble
│   │   ├── graph/                      # Breadth-first traversal, shortest paths, hubs
│   │   ├── learning/                   # Dataset builder, label policy, trainer, evaluator
│   │   ├── services/                   # Business logic, orchestration, simulator
│   │   └── static/index.html           # Full interactive investigation command center SPA
│   └── tests/                          # 32 automated unit and integration tests
├── frontend/                           # Next.js 14 App Router TypeScript workspace
└── scripts/                            # CLI seeding, scenario runners, benchmarks
```

---

## 9. Responsible AI & Legal Safeguards

- **Human-in-the-Loop Requirement**: SentinelFlow AI assists and prepares evidence for investigators; it **never automatically freezes accounts, accuses individuals, or blocks legitimate customers**.
- **Synthetic Data Notice**: All customers, accounts, device fingerprints, and financial transactions generated and seeded in this application are completely fictional and intended solely for research, demonstration, and hackathon evaluation.
- **Production Pre-Requisites**: Deployment to live banking environments requires institutional compliance review, formal model risk validation (SR 11-7), and access-control certification.
