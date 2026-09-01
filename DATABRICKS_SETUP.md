# Databricks Genie setup for GENIEPOLIS (beginner-friendly)

You need: a **Databricks Free Edition** account. ~20 minutes.
GENIEPOLIS runs fine **without** this (Demo fallback mode) — but the judging
demo should show the **real Databricks Genie Agent** as the intelligence layer.

---

## 1. Open Databricks Free Edition
Sign in at <https://www.databricks.com/learn/free-edition> and open your
workspace.

## 2. (If offered) start a SQL warehouse
Left nav → **SQL Warehouses** → start the default `Serverless Starter` (or
similar). Free Edition may auto-provide compute for SQL — that's fine.

## 3. Create the catalog + schema
Open **SQL Editor**, paste and run the top of
[`databricks/setup.sql`](databricks/setup.sql):

```sql
CREATE CATALOG IF NOT EXISTS geniepolis;
CREATE SCHEMA  IF NOT EXISTS geniepolis.campus;
```

## 4. Generate the synthetic CSVs (locally)
```bash
python databricks/export_csvs.py
```
This writes ~16 CSVs to `databricks/exports/`.

## 5. Upload the tables
For **each** CSV in `databricks/exports/`:
**Data** (Catalog) → **Create** → **Create table** → **Upload files** →
drop the CSV → set **Catalog = geniepolis**, **Schema = campus** →
keep the table name equal to the file name (e.g. `occupancy.csv` → table
`occupancy`) → **Create table**.

Minimum set for a good demo: `buildings`, `occupancy`, `parking`, `traffic`,
`classes`, `faculty`, `workers`, `washrooms`, `canteens`, `sports`,
`transport`, `events`, `issues`, `wish_history`, `impact_relationships`.

> All tables are registered in Unity Catalog automatically by the upload flow.

## 6. Create a Genie Space (the "Genie Agent")
Left nav → **Genie** → **New** →
- **Name:** `GENIEPOLIS Campus Genie`
- **Tables:** add every `geniepolis.campus.*` table from step 5
- **Instructions:** paste the contents of
  [`databricks/genie_instructions.md`](databricks/genie_instructions.md)
- **Sample questions:** add the 10 listed in that file
- **Save**

## 7. Test Genie
In the Genie Space chat, ask:
- "Which buildings have the highest occupancy?"
- "What is the busiest parking area?"
- "What are the most requested campus improvements?"

You should get grounded answers + SQL.

## 8. Get the IDs and a token
- **Genie Space ID:** it's in the Space URL —
  `.../genie/rooms/<SPACE_ID>` → copy `<SPACE_ID>`.
- **Host:** your workspace URL, e.g. `https://dbc-xxxx-xxxx.cloud.databricks.com`
- **Token:** top-right avatar → **Settings** → **Developer** →
  **Access tokens** → **Generate new token**.

## 9. Configure GENIEPOLIS
Copy `.env.example` to `.env` and fill in:

```
DATABRICKS_HOST=https://dbc-xxxx-xxxx.cloud.databricks.com
DATABRICKS_TOKEN=dapi...           # never commit this
GENIE_SPACE_ID=01ef....
```

## 10. Run
```bash
streamlit run app.py
```
The header badge should read **“Databricks Genie connected”**. If Databricks is
unreachable it automatically shows **“Demo fallback mode”** and the demo still
works end-to-end.

---

### API used
GENIEPOLIS talks to Genie via the **Genie Conversation API**
(`/api/2.0/genie/spaces/{space_id}/start-conversation`,
`/conversations/{id}/messages`, poll message, `/query-result`) — stateful
conversations with follow-ups, exactly as intended for embedding Genie in apps.
See [`databricks/genie_client.py`](databricks/genie_client.py).

### Never commit secrets
`.env` is git-ignored. The token is read from the environment only.
