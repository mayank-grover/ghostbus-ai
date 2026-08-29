<div align="center">

# 🚌 GhostBus AI

**Predicting the skip *before* it happens — not reporting it after.**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-model-EB0028?logo=xgboost&logoColor=white)
![React](https://img.shields.io/badge/React-frontend-61DAFB?logo=react&logoColor=black)
![Status](https://img.shields.io/badge/status-proof--of--concept-yellow)

</div>

---

## 🌱 Where this came from

I kept hearing the same complaint from other students in Chandigarh: a CTU bus doesn't stop where it's supposed to, or skips a stop entirely — and you either miss it or end up much farther from where you needed to be. If you're depending on that bus to get to class on time, that's not a minor inconvenience. It's a late arrival, a missed connection, sometimes a genuinely bad start to your day.

Most transit apps tell you a bus is late **after** it's late. I wanted to know if you could see it coming — flag a stop as high-risk while the bus is still a few stops away, so you'd actually have time to *do* something about it (grab a different bus, walk to a different stop, whatever works).

> That question is what GhostBus AI is trying to answer.

---

## 🇸🇪 Why it's not running on real CTU data

I looked into what CTU actually publishes. They talk about having ITS, AVLS, and a Command Control Centre — so the infrastructure for real-time data plausibly exists somewhere internally. But there's no public GTFS-RT feed I could get my hands on to actually build and test against.

So instead of faking it or waiting around, I built the **entire pipeline** against a real, public GTFS/GTFS-RT dataset — Stockholm's transit system (SL), via Trafiklab. It's not Chandigarh, but it's real live transit data with the same structure CTU's would have if it were public.

The point right now isn't *"here's how unreliable CTU buses are."* It's **"here's proof this approach actually works end to end on real data."** If a CTU feed ever becomes public, this is built to be pointed at it.

---

## 🔮 What it actually does

For a bus currently en route, the system looks at:

- 📊 how often that **route** skips stops historically
- 📍 how often that specific **stop** gets skipped
- 🕐 how that route behaves at **this particular hour**
- ⚠️ how many stops the bus has **already skipped** on this trip
- ⏱️ how **delayed** it currently is
- 🔢 how many stops are **left** before the one you care about

...and turns all of that into a single number: the probability this stop gets skipped.

```text
Route 512, approaching Ankdammsgatan, 3 stops out
→ 95.9% chance this stop gets skipped
```

That's **not** the model saying *"this stop is always bad."* It's combining the stop's history with what this specific bus is doing right now.

---

## 🏗️ How it's put together

```text
GTFS static (routes, stops, schedules)
        │
        ├──── GTFS-RT live feed
        │              │
        ▼              ▼
   ingestion & historical event parsing
        │
        ▼
   labeled skip events → feature lookups
        │
        ▼
   XGBoost model (trained offline)
        │
        ▼
   FastAPI backend ── serves predictions
        │
   ┌────┴────┐
   ▼         ▼
React UI   Telegram bot
```

**🎯 Ground truth.** GTFS-RT has a `schedule_relationship` field, and one of its values is *literally* `SKIPPED`. That's the label — no guessing, no inferring it from missing data. Out of about **10.2M** stop-events across 14 service dates, roughly **19.8K** are labeled skips — a skip rate of **~0.19%**. Sounds tiny, but that's also the whole reason this is a hard problem: the model has to learn a rare-event pattern without drowning in false alarms *or* missing the real ones.

**🧬 Features (12 total):** hour, day of week, weekend flag, prior skips on this trip, current delay, whether that delay is even known, stops remaining, delay trend, and skip-rate stats at the route level, the stop level, and the route+hour level. All historical stats are computed from **training data only** — a subtle but important detail, since calculating a stop's "historical skip rate" using data that includes the test period would quietly leak the answer into the model.

**🌲 Model.** XGBoost, binary classification, outputs a *probability* rather than a flat yes/no. Trained on 8.28M examples, tested on 1.83M held out **by date** (not randomly split — that matters for a time-series-flavored problem like this).

---

## 📈 How well it actually works

```text
ROC-AUC: 0.876
PR-AUC:  0.478
```

PR-AUC is the number that matters more here, because with a 0.19% positive rate, a model that just says *"never skipped"* would already look decent on plain accuracy. It wouldn't be useful, though.

At the current alert threshold (skip probability ≥ 99%):

| Threshold | Alerts | Precision | Recall |
|:---:|:---:|:---:|:---:|
| **0.99** ⭐ | 2,318 | **67.6%** | 44.4% |
| 0.95 | 4,353 | 45.7% | 56.3% |
| 0.90 | 5,671 | 37.5% | 60.3% |
| 0.75 | 8,497 | 26.6% | 64.1% |
| 0.50 | 14,080 | 16.8% | **67.1%** |

At 0.99, about **two out of three** alerts are real skips, and it catches roughly **44%** of all skips that happen. Lower the threshold and you catch more skips, but you also start crying wolf a lot more — and for something meant to alert an actual passenger, that matters.

> 🐺 I'd rather it under-alert than become the boy who cried bus.

---

## ⚙️ What's running right now

### 🔧 Backend (FastAPI)

| Endpoint | What it does |
|---|---|
| `POST /api/v1/predict` | One-off prediction given route/stop/trip context |
| `GET /api/v1/stops/{stop_id}/risk` | Live risk for a specific stop (aggregates all platforms if it's a parent station) |
| `GET /api/v1/live-predictions` | Live predictions across the whole current GTFS-RT feed |
| `GET /api/v1/stops/search` | Stop name search — served from an in-memory index built once at startup |
| `GET /api/v1/live-activity` | Highest-risk stops right now, read from a cache |

> ⚡ **Performance note:** `/live-activity` used to run the *entire* fetch → feature → predict → aggregate pipeline inside the HTTP request — about **90 seconds** per call. It now runs on a background loop every 20 seconds and caches the result, so the endpoint itself just reads the cache and returns almost instantly.

### 🖥️ Frontend (React + Vite)

Stop search, a live risk dashboard, a map view, trip cards showing skip probability and delay per bus, a live activity radar, and alert banners for high-confidence predictions.

### 🤖 Telegram bot

Early stage. The idea: pick a stop, see what's coming, get pinged if something you're relying on turns risky — without needing to keep a browser tab open.

---

## 📁 Repo layout

<details>
<summary>Click to expand</summary>

```text
backend/
  main.py            FastAPI app, live-activity background worker + cache
  predictor.py        loads the model + lookup tables, runs predictions (single and batched)
  gtfs_lookup.py       static GTFS lookups — trip→route, stop metadata, route metadata
  live_data.py         pulls the live GTFS-RT feed
  live_features.py     turns a live TripUpdate into model-ready features

model/
  train_v2.py           training script (date-based split, leak-free feature construction)
  build_labels_v2.py    builds ground-truth skip labels from schedule_relationship
  export_feature_lookups.py
  skip_model_v2.json    the trained model artifact
  lookup_*.csv          historical route/stop/route-hour stats used at inference time

ingestion/
  parser.py             GTFS-RT protobuf parsing
  backfill.py            historical feed ingestion
  aggregate_events_v2.py / .sql

frontend/
  src/components/       StopSearch, StopRiskDashboard, LiveActivityPanel, LiveActivityRadar,
                         LiveRiskMap, RiskDistributionCard, TripCard, AlertBanner, Header, UIStates
  src/services/api.js    API client
  src/utils/formatters.js

bot/bot.py               Telegram interface

data/                    local GTFS + SQLite database (not committed)
```

</details>

---

## 🚀 Running it yourself

**1. Clone & set up the environment**

```bash
git clone <repository-url>
cd ghostbus-ai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in TRAFIKLAB_API_KEY, TELEGRAM_BOT_TOKEN
```

**2. Start the backend**

```bash
uvicorn backend.main:app --reload --port 8000
```
📍 `http://localhost:8000/health` · 📚 `http://localhost:8000/docs`

**3. Start the frontend** *(separate terminal)*

```bash
cd frontend
npm install
npm run dev
```
📍 `http://localhost:5173`

**4. Start the Telegram bot** *(optional)*

```bash
python -m bot.bot
```

**5. Retrain the model** *(optional)*

```bash
python model/train_v2.py
```

---

## ⚠️ Things this is not, yet

Being upfront about the limitations, because a proof of concept is only useful if you're honest about where it's still rough:

- 🌍 **It's Swedish data, not Chandigarh data.** The performance numbers say something about whether this modeling *approach* works, not about how reliable CTU buses actually are. Two different claims — I don't want to blur them.
- 📅 **Two service dates got excluded** (Aug 12 and Aug 15) because they only had partial-day data from adjacent archive files, and including them would've quietly skewed the historical skip rates.
- 🕰️ **The static schedule and the historical real-time window aren't perfectly time-aligned** — the static GTFS may have been pulled after the Aug 13–25 real-time window it's matched against. Fair assumption for a proof of concept; wouldn't fly in production, which would need properly versioned schedules.
- 🧩 **The delay-trend feature is currently a placeholder** (fixed at 0) in live inference, since the live poller doesn't yet track a trip's delay history over time the way the training pipeline does retroactively.
- 🎲 **Skips are rare**, by a lot. That's the whole modeling challenge, and why precision/recall at different thresholds matters more here than plain accuracy — which would look great even with a model that does nothing.

---

## 🔭 Where I'd like this to go

The real goal was never *"tell me the bus is late."* It's answering a more specific question:

> **Can I actually trust this bus to stop where I need it to — or should I already be planning an alternative?**

For Chandigarh, that means eventually pointing this whole pipeline at a real CTU feed, if one ever becomes publicly available — same architecture, real target audience. Until then, this is the part I can actually build and prove works: real live data in, a real prediction out, fast enough to be useful.

**Still to do:**

- [ ] swap the placeholder delay-trend feature for real live trip history
- [ ] better probability calibration
- [ ] richer explanations per prediction (why is *this one* risky, specifically)
- [ ] finish the Telegram alert flow end to end
- [ ] versioned schedule handling, for if this ever needs to be production-grade
- [ ] point it at a real CTU feed, the day that's possible

---

<div align="center">

*Built because a missed stop shouldn't be a surprise.*

</div>
