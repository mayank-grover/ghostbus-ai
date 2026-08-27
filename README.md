# 🚌 GhostBus AI

> An intelligent public transit monitoring system and Telegram bot that tracks bus schedules, detects "ghost buses" (missing or unexpectedly cancelled transit trips), and delivers ML-driven arrival predictions.

---

## 📌 Summary

**GhostBus AI** combines static GTFS data with real-time transit telemetry (e.g., Trafiklab API) and machine learning models to detect cancelled/disappearing bus trips ("ghost buses") and provide accurate real-time arrival notifications directly through an interactive Telegram bot interface.

---

## ⚙️ How It Works

1. **Data Ingestion (`ingestion/`)**: Fetches static GTFS schedules and streams real-time vehicle positions & trip update feeds (such as Trafiklab GTFS-RT).
2. **Ghost Bus & Delay Prediction (`model/`)**: Analyzes live telemetry against historical schedules to detect missing buses and predict arrival delays using ML algorithms.
3. **FastAPI Backend (`backend/`)**: Provides REST API endpoints for transit data, health monitoring, stop schedules, and prediction outputs.
4. **Telegram Bot Interface (`bot/`)**: Interactive bot interface allowing users to select bus stops, query live arrival times, and receive instant alert notifications when trips are delayed or missing.

---

## 📁 Repository Structure

```
ghostbus-ai/
├── backend/            # FastAPI backend service
│   ├── __init__.py
│   └── main.py         # Application entry point & health check route (/health)
├── bot/                # Telegram bot application
│   ├── __init__.py
│   └── bot.py          # Telegram bot handlers (/start, /stop stub, /help)
├── data/               # Local data storage & SQLite database files
├── ingestion/          # GTFS & GTFS-RT data ingestion scripts (stub)
├── model/              # ML delay prediction & ghost bus detection models (stub)
├── notebooks/          # Exploratory data analysis & model prototyping
├── .env.example        # Environment variable template
├── .gitignore          # Git ignore rules for Python, venv, and environment files
├── requirements.txt    # Python dependencies
└── README.md           # Project documentation
```

---

## 🚀 Quickstart Guide

### 1. Environment Setup

Clone the repository and set up a Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your API keys and tokens:

```bash
cp .env.example .env
```

Update `.env` with:
- `TRAFIKLAB_API_KEY`: API key for Trafiklab transit feeds
- `TELEGRAM_BOT_TOKEN`: Bot token obtained from [@BotFather](https://t.me/BotFather)
- `DATABASE_URL`: Path to SQLite database (default: `sqlite:///./data/ghostbus.db`)

---

## 🏃 Running the Services

### Run FastAPI Backend

```bash
uvicorn backend.main:app --reload --port 8000
```
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)
- API Documentation (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)

### Run Telegram Bot

```bash
python -m bot.bot
```

---

## 📝 TODO Roadmap

- [ ] Implement GTFS-RT data ingestion pipeline in `ingestion/`
- [ ] Set up SQLite database models & migrations (SQLAlchemy)
- [ ] Train & integrate ML ghost bus prediction model in `model/`
- [ ] Expand FastAPI backend endpoints (`/stops`, `/predictions`, `/alerts`)
- [ ] Wire Telegram bot handlers to backend API endpoints

## Known data limitations

- Service dates `20260812` and `20260815` are excluded from training and labeling. They contain only partial-day spillover from adjacent archives (`20260813` and `20260816`), not full days of observations, and would distort skip-rate calculations.

## Known assumptions

- The static GTFS schedule may be downloaded after the historical realtime data window of `2026-08-13` through `2026-08-25`. For this POC, we assume no schedule changes occurred during that window. This assumption would need to be verified for production use.
