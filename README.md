# CADLY — AI-Powered Design for Manufacturing Assistant

**Cadly turns any CAD design into a manufacturing-ready part.** It connects to Fusion 360, detects manufacturing violations in real-time, auto-fixes geometry, recommends machines and materials, and runs multi-agent AI design reviews — all from a single web interface.

> DFMPro charges $5,000/year. Cadly does more, for free, in real-time.

---

## What It Does

| Feature | Description |
|---------|-------------|
| **DFM Violation Detection** | 13 rules across FDM, SLA, CNC, and Injection Molding. Detects thin walls, small holes, sharp corners, steep overhangs, deep holes, missing draft angles, and more. |
| **One-Click Auto-Fix** | Automatically thickens walls, resizes holes to standard drill sizes, and adds fillets to sharp corners — live in Fusion 360. |
| **Process Switch Simulator** | "What if I switch from CNC to FDM?" Instantly see which violations appear/disappear, the cost delta, and a step-by-step redesign roadmap. |
| **Machine Recommendation** | Database of 16 real machines. Ranks by fit score based on build volume, precision, speed, and cost. Flags machines that can't physically make your part. |
| **Material Recommendation** | 23 materials with property spider charts (strength, heat resistance, flexibility, cost, machinability). Ranked by weighted match to your requirements. |
| **AI Design Review Board** | 4 specialist AI agents (CNC Expert, FDM Expert, Materials Engineer, Cost Optimizer) review your part in parallel, then a synthesis agent combines their opinions into a unified report. Powered by Dedalus Labs. |
| **Sustainability Scoring** | Waste analysis, carbon footprint per process, green score with letter grade, actionable savings tips, and AI-powered sustainability recommendations. |
| **Cost Estimation** | FDM / SLA / CNC / Injection Molding cost breakdown with quantity curves and crossover point detection. |

---

## Architecture

```
┌─────────────────────────────┐     ┌──────────────────────┐
│   Cadly Web UI (Browser)    │     │    Fusion 360 CAD     │
│   localhost:3000            │     │                      │
└─────────┬───────────────────┘     └──────────┬───────────┘
          │ HTTP + WebSocket                    │
          ▼                                     │
┌─────────────────────────────┐                 │
│   FastAPI Server (Python)   │                 │
│   - DFM Engine (13 rules)   │    HTTP :5000   │
│   - Cost Estimator          │◄────────────────┘
│   - Process Simulator       │     Fusion Add-in
│   - Machine/Material DB     │     (runs inside Fusion)
│   - AI Review Board         │
│   - Sustainability Scorer   │
└─────────────────────────────┘
```

**Two-layer architecture:** FastAPI backend (port 3000) communicates with a Fusion 360 add-in (port 5000) that runs inside Fusion's process. The add-in uses a task queue pattern for thread safety since Fusion's API is single-threaded.

---

## Tech Stack

- **Backend:** Python 3.11, FastAPI, httpx (async HTTP), WebSockets
- **Frontend:** Vanilla HTML/CSS/JS — no frameworks, no build step
- **CAD Integration:** Fusion 360 Add-in (HTTP server inside Fusion)
- **AI Agents:** Dedalus Labs SDK (4-agent design review + sustainability scoring)
- **Data:** JSON-driven rule engine, machine database, material database

---

## How to Run

**Prerequisites:** Python 3.11+, Fusion 360 with the Cadly add-in installed

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment (optional — for AI features)
cp .env.example .env
# Add your DEDALUS_API_KEY to .env

# 3. Start the server
python -m uvicorn src.main:app --host 0.0.0.0 --port 3000 --app-dir .
```

Open **http://localhost:3000** in your browser. Make sure the Fusion 360 add-in is running (connection status shown in the header).

---

## Prize Track Alignment

### Best Overall
Full-stack DFM platform: detection + auto-fix + simulation + recommendation + AI review + sustainability — all integrated with real CAD software.

### Crosses 2+ Fields
Manufacturing Engineering + Computer Science/AI + Materials Science + Sustainability + Education — five fields in one tool.

### Most Significant Innovation
The only free tool that combines real-time DFM detection with one-click auto-fix and process switch simulation. Commercial alternatives (DFMPro, DFMXpress) cost thousands per year, lack auto-fix, and don't do process switching.

### Best AI for Decision Support
- **Decision Summary Panel** — consolidated recommendation at a glance
- **Process Switch Simulator** — AI-guided "what-if" analysis
- **Machine & Material Recommender** — ranked suggestions with explanations
- **AI Design Review Board** — 4 specialist agents debate your design

### Best Use of Dedalus Labs
4-agent AI Design Review Board: CNC Expert, FDM Expert, Materials Engineer, and Cost Optimizer run in parallel via the Dedalus SDK, then a synthesis agent merges their opinions. Also powers AI sustainability scoring with environmental impact analysis.

### Sustainability
Green score calculation, waste/carbon analysis per process, weight equivalencies ("that's 2.3 plastic bags of waste"), actionable savings tips, and AI-powered sustainability recommendations.

### Societal Impact
Democratizes manufacturing expertise. An engineering student or small business owner gets the same DFM intelligence that Fortune 500 companies pay consultants for — instantly, for free.

---

## Project Structure

```
cadly-v2/
├── src/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py             # Settings + Fusion endpoint registry
│   ├── fusion/               # Fusion 360 HTTP client + geometry helpers
│   ├── dfm/                  # Rule engine + registry (13 rules from JSON)
│   ├── analysis/             # Wall, hole, corner, overhang analyzers
│   ├── fixes/                # Auto-fix: hole resize, wall thicken, corner fillet
│   ├── simulator/            # Process switch + redesign planner + comparison
│   ├── recommend/            # Machine + material matching engine
│   ├── costs/                # Cost estimator + quantity curves + comparison
│   ├── sustainability/       # Waste, carbon, green score, AI scoring
│   ├── agents/               # Dedalus-powered 4-agent review board
│   ├── models/               # Shared dataclasses (violations, geometry, costs, machines, materials)
│   ├── api/                  # REST routes + WebSocket + middleware
│   └── ui/                   # Frontend (HTML + CSS + JS components)
├── data/
│   ├── rules.json            # 13 DFM rules (FDM, SLA, CNC, IM)
│   ├── machines.json         # 16 real machines with specs
│   ├── materials.json        # 23 materials with properties
│   └── standard_holes.json   # 76 standard drill sizes (metric + imperial)
└── requirements.txt
```

---

## Built By

**Nayansh Patni** — Carnegie Mellon University

Built for TartanHacks 2026.
