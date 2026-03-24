# Energy Geopolitics Intelligence Platform

Real-time intelligence platform for **oil & gas geopolitical risk assessment**. Tracks events, assets, sanctions, and supply disruptions with a resilient recovery stack.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI REST API (:8000)                      │
│  /api/v1/events  /api/v1/assets  /api/v1/intelligence  /health  │
└──────────────┬──────────────────────────────┬───────────────────┘
               │                              │
    ┌──────────▼──────────┐       ┌───────────▼──────────┐
    │   Analysis Engine   │       │   Recovery Stack      │
    │  ┌───────────────┐  │       │  ┌─────────────────┐  │
    │  │  Risk Scorer  │  │       │  │ Circuit Breaker  │  │
    │  │Impact Analyzer│  │       │  │ Retry + Backoff  │  │
    │  │ Alert Engine  │  │       │  │  Checkpointing  │  │
    │  └───────────────┘  │       │  └─────────────────┘  │
    └──────────┬──────────┘       └───────────┬──────────┘
               │                              │
    ┌──────────▼──────────────────────────────▼──────────┐
    │              Data Collectors (background)           │
    │   PriceCollector  NewsCollector  SanctionsCollector │
    │       (EIA API)     (NewsAPI)    (OFAC/EU/UN lists) │
    └─────────────────────────────────────────────────────┘
               │
    ┌──────────▼──────────┐
    │    In-Memory Store  │
    │  events / assets /  │
    │  risks / reports /  │
    │  alerts / prices    │
    └─────────────────────┘
```

## Quick Start

### With Docker (recommended)

```bash
cd energy-geopolitics
cp .env.example .env
docker-compose up -d
```

Open `http://localhost:8000` for the dashboard or `http://localhost:8000/api/docs` for API docs.

### Local development

```bash
cd energy-geopolitics
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
PYTHONPATH=. python src/main.py
```

### Run tests

```bash
cd energy-geopolitics
pip install -r requirements.txt
PYTHONPATH=. pytest tests/ -v
```

## Features

### Geopolitical Event Tracking
- 10 event types: conflict, sanctions, pipeline incident, cartel decision, supply disruption, etc.
- Severity levels: low, moderate, high, critical
- Supply impact in barrels per day (bpd)
- Price impact estimation
- Confidence scoring per event

### Energy Asset Monitoring
- 9 asset types: oilfield, gas field, pipeline, refinery, LNG terminal, chokepoint, etc.
- Strategic importance scoring
- Real-time status tracking (operational, degraded, offline, under threat, sanctioned)
- Chokepoint risk analysis (Strait of Hormuz, Bab el-Mandeb, etc.)

### Risk Scoring Engine
Multi-dimensional risk assessment:
| Dimension | Weight | Description |
|-----------|--------|-------------|
| Supply Disruption | 30% | Direct output impact |
| Geopolitical | 25% | State-level conflict/instability |
| Infrastructure | 20% | Physical asset threats |
| Sanctions | 15% | Legal/financial restrictions |
| Market Volatility | 10% | Price/demand uncertainty |

### Intelligence Reports
- Daily intelligence briefs (auto-generated)
- Global + regional risk summaries
- Key findings and actionable recommendations
- Price snapshot integration

### Recovery Stack
- **Circuit Breaker**: Prevents cascading failures when data sources are down
  - States: CLOSED → OPEN → HALF_OPEN → CLOSED
  - Configurable failure threshold and recovery timeout
- **Retry with Backoff**: Exponential backoff with jitter for transient failures
  - Configurable max attempts, base delay, max delay
- **Checkpointing**: Persists collector state to disk
  - Resumes from last successful cursor after restarts
  - Tracks failure history per collector

## API Reference

### Events
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/events/` | List all events (filterable) |
| GET | `/api/v1/events/summary` | Event count breakdown |
| GET | `/api/v1/events/{id}` | Get specific event |
| POST | `/api/v1/events/` | Create new event |
| PATCH | `/api/v1/events/{id}` | Update event status/severity |
| DELETE | `/api/v1/events/{id}` | Delete event |

### Assets
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/assets/` | List assets (filterable) |
| GET | `/api/v1/assets/chokepoints` | Chokepoint risk analysis |
| GET | `/api/v1/assets/{id}/exposure` | Asset supply exposure |

### Intelligence
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/intelligence/risk/global` | Global risk score |
| GET | `/api/v1/intelligence/risk/regional` | Regional risk summaries |
| GET | `/api/v1/intelligence/risk/asset/{id}` | Asset-specific risk |
| GET | `/api/v1/intelligence/impact/global` | Supply chain impact |
| GET | `/api/v1/intelligence/impact/chokepoints` | Chokepoint analysis |
| POST | `/api/v1/intelligence/reports/daily-brief` | Generate daily brief |
| GET | `/api/v1/intelligence/alerts` | List alerts |
| POST | `/api/v1/intelligence/alerts/scan` | Run alert scan |
| PATCH | `/api/v1/intelligence/alerts/{id}/acknowledge` | Acknowledge alert |
| GET | `/api/v1/intelligence/prices/latest` | Latest oil prices |
| GET | `/api/v1/intelligence/prices/history` | Price history |

### Health & Recovery
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health/` | Health check |
| GET | `/api/v1/health/recovery` | Recovery stack status |
| GET | `/api/v1/health/recovery/collectors` | Collector health |
| POST | `/api/v1/health/recovery/reset/{name}` | Reset circuit breaker |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment |
| `APP_PORT` | `8000` | Server port |
| `EIA_API_KEY` | `""` | EIA API key (optional, uses simulation if empty) |
| `NEWS_API_KEY` | `""` | NewsAPI key (optional) |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | Failures before circuit opens |
| `CIRCUIT_BREAKER_RECOVERY_TIMEOUT` | `60` | Seconds before half-open retry |
| `RETRY_MAX_ATTEMPTS` | `3` | Max retry attempts |
| `RETRY_BASE_DELAY` | `2.0` | Base delay seconds for exponential backoff |
| `CHECKPOINT_DIR` | `./checkpoints` | Directory for checkpoint files |
| `HIGH_RISK_THRESHOLD` | `0.70` | Score threshold for HIGH alerts |
| `CRITICAL_RISK_THRESHOLD` | `0.85` | Score threshold for CRITICAL alerts |

## Seed Data

On startup with `LOAD_SEED_DATA=true`, the platform loads realistic scenario data:

**Assets**: Ghawar, Strait of Hormuz, Permian Basin, Trans-Siberian Pipeline, Ras Tanura, Bab el-Mandeb, Kashagan, Rotterdam Refinery

**Events**:
- Houthi attacks on Red Sea shipping (HIGH, 1.4M bpd impact)
- Russia-Ukraine energy infrastructure conflict (CRITICAL, 2.1M bpd)
- OPEC+ production cut extension (HIGH, 2.2M bpd)
- Iran nuclear talks breakdown (MODERATE, 1.2M bpd)
- Libya field blockade (HIGH, 400K bpd)
- Venezuela PDVSA sanction easing (MODERATE, -200K bpd)
- Iraq Kirkuk-Ceyhan pipeline delay (MODERATE, 450K bpd)

**Sanctions**: Rosneft, NIOC (Iran), Syrian Petroleum Co., PDVSA
