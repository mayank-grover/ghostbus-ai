# 🚌 GhostBus AI

> An ML-powered public transit monitoring system that predicts when an upcoming bus stop is likely to be skipped — turning real-time transit telemetry into actionable passenger alerts.

## Why GhostBus AI?

This project started with a problem I kept hearing from fellow students in Chandigarh.

Students would talk about CTU buses unexpectedly skipping stops, not stopping where they expected, or leaving them significantly farther from their college or destination than planned. When you're relying on a bus to get to class, a single missed stop can mean a much longer walk, a missed connection, or being late.

I wanted to build something that could **predict a potentially skipped stop before the bus reaches it**, rather than simply reporting that a bus was already late or that a stop had already been missed.

That led to GhostBus AI.

### Why not build it directly for CTU?

The Chandigarh Transport Undertaking (CTU) operates a substantial city, suburban, and interstate bus network. CTU's official website publishes route maps and timetable information, and CTU states that its operations include computerized systems such as Intelligent Transport Systems (ITS), Automatic Vehicle Location Systems (AVLS), and a Command Control Centre.

However, the public-facing CTU data I could access was not available as the machine-readable GTFS/GTFS-RT feed required to directly train and validate this system against Chandigarh's real-time operations.

So GhostBus AI is currently a **proof of concept**.

Instead of pretending to have access to CTU's internal telemetry, I built the complete pipeline against an available GTFS/GTFS-RT transit dataset from Sweden. This lets me test the core technical question:

> **Can historical stop behavior, route-level patterns, time-of-day information, and live transit telemetry be combined to predict whether a bus is likely to skip an upcoming stop?**

If a comparable public real-time CTU feed becomes available, the same prediction architecture can be adapted to Chandigarh.

---

## 🎯 What the System Does

GhostBus AI currently focuses on **stop-level skip prediction**.

For an active bus approaching a stop, the system combines:

* Historical skip behavior for the route
* Historical skip behavior for the stop
* Route + hour skip patterns
* Time of day
* Day of week
* Whether the trip has already skipped stops
* Current known delay
* Number of stops remaining
* Live GTFS-RT trip updates

The result is a probability that the bus will skip the upcoming stop.

For example:

```text
Route:              512
Stop:               Ankdammsgatan
Stops remaining:    3

Predicted skip probability: 95.9%
High-confidence alert:      No
```

The system can then surface high-risk stops through the backend and frontend dashboard.

---

# 🧠 How It Works

```text
             GTFS Static Data
                    │
                    ▼
          ┌───────────────────┐
          │ Transit Structure │
          │ routes / stops /  │
          │ trips / schedules │
          └─────────┬─────────┘
                    │
                    │
GTFS-RT Feed ───────┤
                    ▼
          ┌───────────────────┐
          │  Data Ingestion   │
          │  + Event Parsing  │
          └─────────┬─────────┘
                    │
                    ▼
          ┌───────────────────┐
          │ Historical Labels │
          │ & Feature Lookup  │
          └─────────┬─────────┘
                    │
                    ▼
          ┌───────────────────┐
          │ XGBoost Predictor  │
          │                   │
          │ route behavior    │
          │ stop behavior     │
          │ route-hour stats  │
          │ trip state        │
          │ time features     │
          └─────────┬─────────┘
                    │
                    ▼
          ┌───────────────────┐
          │   FastAPI API     │
          └─────────┬─────────┘
                    │
             ┌──────┴──────┐
             ▼             ▼
      React Dashboard   Telegram Bot
```

## 1. Data Ingestion

The `ingestion/` pipeline processes static GTFS data and historical/live GTFS-RT trip updates.

The GTFS-RT parser extracts information such as:

* Trip ID
* Route ID
* Stop ID
* Service date
* Predicted arrival/departure time
* Delay
* Schedule relationship
* Feed timestamp

Historical observations are aggregated into stop-level events before model training.

---

## 2. Ground Truth

GhostBus AI uses the GTFS-RT `schedule_relationship` field as the ground-truth signal for skipped/cancelled stop events in the current proof of concept.

The historical dataset contains approximately:

```text
10.2M+ stop-event records
~19.8K skip-labelled records
14 service dates
```

The overall observed skip rate is approximately:

```text
0.19%
```

The extreme class imbalance is one of the main modelling challenges.

---

## 3. Feature Engineering

The model currently uses 12 features:

```text
hour
day_of_week
is_weekend
prior_skips_this_trip
last_known_delay
has_known_delay
stops_remaining
delay_trend
route_skip_rate
route_count
route_hour_skip_rate
route_hour_count
```

Historical route, stop, and route-hour statistics are calculated using **training data only** to avoid leaking future information into the model.

This is particularly important for this problem because a naive historical skip-rate calculation can accidentally include information from the holdout period.

---

## 4. Machine Learning

GhostBus AI currently uses **XGBoost** for binary classification.

The model outputs:

```text
P(bus skips upcoming stop)
```

rather than simply predicting a binary yes/no result.

This probability can then be converted into different alert levels depending on the desired precision/recall tradeoff.

For example, the current high-confidence threshold is:

```text
skip_probability >= 0.99
```

---

# 📊 Model Results

The current model was evaluated using a date-based holdout split rather than a random row split.

### Dataset

```text
Training examples: 8,285,649
Test examples:     1,834,799

Train skip rate:   0.1924%
Test skip rate:    0.1925%
```

### Overall performance

```text
ROC-AUC: 0.8764
PR-AUC:  0.4775
```

PR-AUC is particularly important here because skipped-stop events are extremely rare.

### Threshold = 0.99

```text
Alerts:    2,318
True Positives: 1,568
False Positives: 750

Precision: 67.64%
Recall:    44.39%
```

This means the high-confidence alert mode prioritizes precision: roughly two-thirds of alerts correspond to actual skip events in the holdout data, while detecting about 44% of the positive events.

Lower thresholds can increase recall, but at the cost of substantially more false alerts.

| Threshold | Alerts | Precision | Recall |
| --------- | -----: | --------: | -----: |
| 0.99      |  2,318 |    67.64% | 44.39% |
| 0.95      |  4,353 |    45.69% | 56.31% |
| 0.90      |  5,671 |    37.52% | 60.25% |
| 0.75      |  8,497 |    26.64% | 64.10% |
| 0.50      | 14,080 |    16.84% | 67.13% |

The threshold is therefore a product decision as much as a modelling decision: a passenger alerting system generally needs to avoid overwhelming users with false alarms.

---

# 🔬 Example Live Prediction

A live prediction currently looks like:

```text
Route:              512
Stop:               Ankdammsgatan
Stops remaining:    3

Historical route skip rate:       4.05%
Historical stop skip rate:       83.31%
Route-hour skip rate:             3.46%

Predicted skip probability:      95.94%
High-confidence alert:            No
```

The important distinction is that the model does **not** simply say:

> "This stop is skipped often."

Instead, it combines the stop's historical behavior with the current trip's route, time, position within the trip, and other available signals.

---

# 🖥️ Current Interface

GhostBus AI includes a React + Vite dashboard for interacting with the prediction API.

The dashboard supports:

* Stop search
* Live stop risk
* Route information
* Trip-level predictions
* Skip probability visualization
* Delay information
* Stops remaining
* High-confidence alerts
* Live activity monitoring

The FastAPI backend exposes the underlying prediction and transit data through REST endpoints.

---

# 🤖 Telegram Bot

The project is also designed around a Telegram interface so that passengers can eventually query a stop and receive alerts without needing to keep a dashboard open.

The intended interaction is:

```text
User
 │
 ├── Select stop
 │
 ├── View upcoming buses
 │
 ├── View predicted skip risk
 │
 └── Receive alert if risk becomes high
```

The Telegram layer is intentionally separated from the prediction system so that the same backend can serve multiple interfaces.

---

# 🏗️ Repository Structure

```text
ghostbus-ai/
│
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── predictor.py         # Live model inference
│   └── gtfs_lookup.py       # Static GTFS lookup layer
│
├── bot/
│   └── ...                  # Telegram bot
│
├── frontend/
│   ├── src/
│   │   ├── components/      # React UI components
│   │   ├── services/        # API client
│   │   └── ...
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── ingestion/
│   ├── parser.py            # GTFS-RT protobuf parser
│   ├── backfill.py          # Historical feed ingestion
│   ├── aggregate_events_v2.py
│   └── aggregate_events_v2.sql
│
├── model/
│   ├── train_v2.py          # Model training
│   ├── build_labels_v2.py   # Ground-truth construction
│   ├── export_feature_lookups.py
│   └── ...
│
├── notebooks/               # Analysis and experimentation
│
├── data/                    # Local datasets / SQLite database
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

> Large datasets and generated local artifacts are intentionally kept out of the Git repository.

---

# 🚀 Quickstart

## 1. Clone the repository

```bash
git clone <repository-url>
cd ghostbus-ai
```

## 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Configure environment variables

```bash
cp .env.example .env
```

Configure the required credentials in `.env`, such as:

```text
TRAFIKLAB_API_KEY=...
TELEGRAM_BOT_TOKEN=...
```

Do not commit `.env` or API keys.

---

# ▶️ Running the Backend

Start FastAPI:

```bash
uvicorn backend.main:app --reload --port 8000
```

Health check:

```text
http://localhost:8000/health
```

Swagger API documentation:

```text
http://localhost:8000/docs
```

---

# ▶️ Running the Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite development server will normally be available at:

```text
http://localhost:5173
```

---

# ▶️ Running the Telegram Bot

From the project root:

```bash
python -m bot.bot
```

---

# 🧪 Model Training

The current model can be retrained with:

```bash
python model/train_v2.py
```

The training pipeline performs a date-based train/test split and constructs historical lookup features from training data only.

The resulting model artifact is written to:

```text
model/skip_model_v2.json
```

---

# ⚠️ Data Limitations

This project is a proof of concept, and its results should not be interpreted as production-level transit reliability estimates.

### Partial service dates

Service dates `20260812` and `20260815` are excluded from training and labeling because they contain partial-day spillover from adjacent archives rather than complete observation windows.

Including them would distort historical skip-rate calculations.

### Static schedule alignment

The static GTFS schedule may have been downloaded after the historical real-time data window of `2026-08-13` through `2026-08-25`.

For this proof of concept, the system assumes that no relevant schedule changes occurred during that window.

A production deployment would need versioned static schedules so that each real-time observation is matched against the schedule that was actually valid at that time.

### Dataset mismatch

The model is currently trained and evaluated using Swedish transit data rather than CTU data.

Therefore, the model's numerical performance **does not represent CTU bus reliability**.

The purpose of the current dataset is to validate the technical feasibility of the prediction pipeline.

### Rare-event classification

Skipped-stop events represent only a small fraction of all observations.

This creates severe class imbalance and makes accuracy a poor metric for evaluating the system. Precision, recall, PR-AUC, and threshold-specific alert quality are more informative.

---

# 🛣️ Roadmap

## Completed

* [x] GTFS-RT protobuf parsing
* [x] Historical transit data ingestion
* [x] Stop-level event aggregation
* [x] GTFS static lookup layer
* [x] Ground-truth skip-event construction
* [x] Train/test date split
* [x] Leak-free historical feature generation
* [x] XGBoost skip prediction model
* [x] Live model inference
* [x] FastAPI prediction endpoints
* [x] React + Vite dashboard
* [x] Stop search
* [x] Live stop risk visualization
* [x] High-confidence prediction alerts

## Next

* [ ] Optimize live-activity inference latency
* [ ] Add caching/background processing for live predictions
* [ ] Replace placeholder delay-trend signal with real live trip history
* [ ] Improve calibration of predicted probabilities
* [ ] Add richer trip-level explanations
* [ ] Complete Telegram alert workflow
* [ ] Evaluate against a public Chandigarh/CTU real-time feed if one becomes available
* [ ] Build versioned schedule handling for production deployment

---

# 🔭 Long-Term Goal

The eventual goal is not simply to predict whether a bus is late.

It is to answer a more useful passenger question:

> **"Can I rely on this bus to actually stop where I need it to?"**

For Chandigarh, that could mean taking a system like GhostBus AI and connecting it to a reliable CTU real-time data source.

A passenger could then select their college or bus stop and receive an alert before an approaching bus becomes a problem — giving them enough time to choose another bus, another stop, or another route.

Until that data is publicly accessible, GhostBus AI serves as a technical proof of concept for how such a system could work.
