# ✨ GENIEPOLIS

**Three Wishes. One Campus. Infinite Ripples.**
HackCulture · Track B · Creative Campus Intelligence · *Genie-Powered Campus Intelligence*

> Traditional campus dashboards tell you **what** is happening.
> GENIEPOLIS lets students ask **what if?** — the Genie narrows the wish, a
> deterministic engine simulates the ripple, and **Databricks Genie** grounds
> and explains it. Repeated wishes stop being isolated complaints and become a
> **campus signal**.

---

## What it is

A **Genie-powered campus what-if simulator** for a synthetic digital twin of
**BMS College of Engineering**. You explore an interactive 2.5D campus, then a
Genie gives you **three independent wishes**. For each wish the Genie plays
Akinator — asking 3–6 narrowing questions — confirms what you *really* meant,
then shows:

`SEE CAMPUS → MEET GENIE → MAKE WISH → GENIE NARROWS → MAKE IT HAPPEN → magic
transition → ripple animation → direct + indirect impacts → before/after →
risks + benefits → alternative wishes → WISH COMPLETE` … ×3 … `→ CAMPUS PULSE`

> **All operational data is synthetic demonstration data.** Nothing here is real
> BMSCE information.

## Architecture (spec §7)

```
USER → STREAMLIT → GENIE (interpret / clarify / retrieve / explain)
     → STRUCTURED SCENARIO JSON
     → DETERMINISTIC SIMULATION ENGINE (Python — all the numbers)
     → RIPPLE GRAPH → CAMPUS VISUALIZATION → IMPACT ANALYSIS
     → GENIE EXPLANATION
```

| Layer | Tech | Job |
|---|---|---|
| Intelligence | **Databricks Genie Agent** (Conversation API) | interpret wishes, answer campus-data questions, explain scenarios |
| Data + Analytics | **Databricks** Unity Catalog (`geniepolis.campus.*`) | 16 synthetic tables incl. `impact_relationships` |
| Simulation | **Python** `simulation/engine.py` | deterministic before/after, ripple, risk/benefit — **never the LLM** |
| Experience | **Streamlit** + custom CSS | the game-like UI and the 12-screen journey |
| Visual | **Plotly** 2.5D campus | clickable buildings, live conditions, ripple highlights |

Visualization concept adapted (traded 3D for a fast, stable Plotly map) from
[Smart-Campus-Digital-Twin](https://github.com/Smart-Campus-Digital-Twin)
(Three.js + IoT streaming).

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

That's it. No Docker, no extra services. It opens in **Demo fallback mode** and
the entire journey works end-to-end.

### Connect the real Databricks Genie (recommended for judging)

Follow [`DATABRICKS_SETUP.md`](DATABRICKS_SETUP.md) (~20 min, Free Edition):
generate CSVs → upload 16 tables → create a Genie Space → paste
[`databricks/genie_instructions.md`](databricks/genie_instructions.md) → copy
IDs into `.env`:

```bash
cp .env.example .env      # then fill DATABRICKS_HOST / DATABRICKS_TOKEN / GENIE_SPACE_ID
streamlit run app.py
```

Header badge flips to **“Databricks Genie connected”**. If Databricks becomes
unreachable mid-demo it auto-falls back — the app never crashes (spec §45, §54).

## Demo scenarios (prebuilt)

1. **Start classes at 10 AM** — sleep vs. a sharper, later traffic + bus peak
2. **Move the front gate near parking** — shorter walk vs. one traffic pinch-point
3. **Boost sports participation** — washroom / parking / cafeteria spikes near the ground
4. **Make the central campus pedestrian-only** — real congestion drop vs. emergency-access risk
5. **Put the cafeteria in the center** — shorter walk vs. dangerous crowd concentration
6. **Make the campus medieval** — pure visual re-theme, no simulation (Type C wish)

Three wish classes are supported: **A Operational**, **B Infrastructure**,
**C Creative/Visual**.

## Demo script

1. "This is BMS College of Engineering — a synthetic campus digital twin."
   Click buildings: rooms, faculty, classes, occupancy, workers.
2. "GENIEPOLIS doesn't want you to read dashboards. It gives you three wishes."
   → *Summon the Genie.*
3. Wish 1: type *"I want classes to start at 10."* Genie asks who it helps,
   why, scope → **"Ahhh. Now I understand."** → **MAKE IT HAPPEN**.
4. Smoke transition → ripple: Academic Block → Bus → Traffic → Parking →
   Faculty → Workers → Canteen light up in sequence.
5. Before → After table, Benefits, Risks, Trade-offs, the Genie's "Why?",
   then alternatives → **WISH 1 COMPLETE**.
6. Repeat for Wish 2 & 3.
7. **Campus Pulse:** "63 students asked for better parking. This is no longer a
   wish — it's a campus signal."

## Project structure

```
geniepolis/
  app.py                     # 12-screen journey state machine
  components/
    style.py  genie.py  campus.py  ripple.py  impact.py  stats.py  wish_panel.py
  simulation/
    engine.py                # deterministic simulation (12 scenario handlers)
    scenarios.py             # wish classification + Akinator question trees
    relationships.py         # campus butterfly-effect graph
  data/
    campus_data.py           # static 2.5D layout (buildings, roads, zones, themes)
    synthetic_data.py        # reproducible synthetic tables (np.random.seed(42))
  databricks/
    genie_client.py          # Genie Conversation API client + GenieBridge fallback
    setup.sql  genie_instructions.md  export_csvs.py
  DATABRICKS_SETUP.md   requirements.txt   .env.example
```

## Reliability notes

* Reproducible synthetic data (`np.random.seed(42)`).
* The LLM never invents numbers — `simulation/engine.py` computes every metric;
  Genie only explains them.
* `GenieBridge` health-checks Databricks and degrades to local answers over the
  same synthetic data on any failure, labelled *"Demo fallback mode"*.
* Secrets are read from the environment only; `.env` is git-ignored.

## Future vision

Swap synthetic tables for real campus IoT / occupancy sensors / transport feeds
/ complaint systems / energy meters — the Genie, simulation and Pulse layers
stay the same. Not built now: responsibly generated synthetic data only.
