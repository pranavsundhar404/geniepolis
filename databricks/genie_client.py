"""
Databricks Genie integration for GENIEPOLIS.

Two layers:

  GenieClient  -- thin, honest wrapper over the Databricks Genie Conversation
                  API (start-conversation / create-message / poll / query-result).
                  Stateful: keeps a conversation_id for follow-ups.

  GenieBridge  -- what the app talks to. Uses the real Genie for data-grounded
                  answers + scenario explanations when configured; falls back to
                  a local DEMO_MODE (predefined flows over the synthetic data) so
                  the app never crashes during a live demo.

ARCHITECTURE CONTRACT (see spec §7, §32):
  Genie = interpretation / clarification / data retrieval / explanation.
  Genie DOES NOT run the numeric simulation — simulation/engine.py does.
"""
from __future__ import annotations

import os
import time

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

GENIE_CONNECTED = "GENIE_CONNECTED"
DEMO_MODE = "DEMO_MODE"

POLL_TIMEOUT_S = 180        # Genie's first answer can be slow (serverless cold start)
POLL_INTERVAL_S = 2.0
HTTP_TIMEOUT_S = 45         # per-request socket timeout


class GenieClient:
    def __init__(self, host=None, token=None, space_id=None):
        self.host = (host or os.getenv("DATABRICKS_HOST", "")).rstrip("/")
        self.token = token or os.getenv("DATABRICKS_TOKEN", "")
        self.space_id = space_id or os.getenv("GENIE_SPACE_ID", "")
        self.conversation_id = None
        self.last_error = None

    # -- config -----------------------------------------------------------
    @property
    def configured(self) -> bool:
        return bool(self.host and self.token and self.space_id and requests is not None)

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def _url(self, path: str) -> str:
        return f"{self.host}/api/2.0/genie/spaces/{self.space_id}{path}"

    # -- health ---------------------------------------------------------------
    def health_check(self) -> bool:
        """Cheap reachability + auth check.

        200            -> healthy
        401 / 403      -> credentials wrong / token lacks scope  -> fail
        404 / 405      -> this workspace exposes a different path shape, but host
                          + token resolved fine; the real check happens on ask()
                          -> treat as OK so we don't get stuck in demo mode
        """
        if not self.configured:
            self.last_error = "Missing DATABRICKS_HOST / DATABRICKS_TOKEN / GENIE_SPACE_ID"
            return False
        try:
            r = requests.get(self._url(""), headers=self._headers(), timeout=10)
            if r.status_code == 200:
                return True
            if r.status_code in (401, 403):
                self.last_error = (f"Auth failed (HTTP {r.status_code}). Check DATABRICKS_TOKEN "
                                   f"and that it belongs to this workspace.")
                return False
            if r.status_code in (404, 405):
                # This workspace exposes a different path shape, but host + token
                # resolved. Assume OK — the real error (if any) surfaces on ask().
                return True
            self.last_error = f"Genie space check HTTP {r.status_code}: {r.text[:200]}"
            return False
        except Exception as e:  # network / dns / timeout
            self.last_error = f"{type(e).__name__}: {e}"
            return False

    # -- conversation -------------------------------------------------------
    def ask(self, text: str, new_conversation: bool = False) -> dict:
        """Send a message to Genie, wait for completion, return a normalised dict.

        Returns: {ok, text, sql, rows, columns, conversation_id, message_id, error}
        Never raises.
        """
        if not self.configured:
            return {"ok": False, "error": "not configured", "text": ""}
        try:
            if new_conversation or not self.conversation_id:
                r = requests.post(self._url("/start-conversation"),
                                  headers=self._headers(), json={"content": text},
                                  timeout=HTTP_TIMEOUT_S)
                r.raise_for_status()
                j = r.json()
                self.conversation_id = j.get("conversation_id") or j.get("conversation", {}).get("id")
                message_id = j.get("message_id") or j.get("message", {}).get("id")
            else:
                r = requests.post(
                    self._url(f"/conversations/{self.conversation_id}/messages"),
                    headers=self._headers(), json={"content": text}, timeout=HTTP_TIMEOUT_S)
                r.raise_for_status()
                j = r.json()
                message_id = j.get("message_id") or j.get("id")

            return self._await_message(message_id)
        except Exception as e:
            self.last_error = f"{type(e).__name__}: {e}"
            return {"ok": False, "error": self.last_error, "text": ""}

    def _await_message(self, message_id: str) -> dict:
        deadline = time.time() + POLL_TIMEOUT_S
        msg = {}
        last_exc = None
        while time.time() < deadline:
            try:
                r = requests.get(
                    self._url(f"/conversations/{self.conversation_id}/messages/{message_id}"),
                    headers=self._headers(), timeout=HTTP_TIMEOUT_S)
                r.raise_for_status()
                msg = r.json()
                last_exc = None
                status = msg.get("status")
                if status in ("COMPLETED", "FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"):
                    break
            except requests.exceptions.RequestException as e:
                # a single slow / dropped poll shouldn't kill the whole wait
                last_exc = e
            time.sleep(POLL_INTERVAL_S)

        if msg.get("status") != "COMPLETED":
            err = f"status={msg.get('status')}" if msg else \
                  (f"timed out after {POLL_TIMEOUT_S}s"
                   + (f" ({type(last_exc).__name__})" if last_exc else ""))
            return {"ok": False, "error": err, "text": "",
                    "conversation_id": self.conversation_id, "message_id": message_id}

        out = {"ok": True, "text": "", "sql": None, "rows": None, "columns": None,
               "conversation_id": self.conversation_id, "message_id": message_id, "error": None}

        for att in msg.get("attachments", []) or []:
            if att.get("text", {}).get("content"):
                out["text"] += att["text"]["content"].strip() + "\n"
            q = att.get("query")
            if q:
                out["sql"] = q.get("query") or q.get("query_text")
                if q.get("description"):
                    out["text"] += q["description"].strip() + "\n"
                att_id = att.get("attachment_id")
                res = self._query_result(message_id, att_id)
                if res:
                    out["columns"], out["rows"] = res
        out["text"] = out["text"].strip()
        return out

    def _query_result(self, message_id: str, attachment_id: str | None):
        paths = []
        if attachment_id:
            paths.append(
                f"/conversations/{self.conversation_id}/messages/{message_id}/attachments/{attachment_id}/query-result")
        paths.append(
            f"/conversations/{self.conversation_id}/messages/{message_id}/query-result")
        for p in paths:
            try:
                r = requests.get(self._url(p), headers=self._headers(), timeout=HTTP_TIMEOUT_S)
                if r.status_code != 200:
                    continue
                j = r.json()
                sr = (j.get("statement_response") or j.get("query_result") or j)
                schema = (sr.get("manifest", {}).get("schema", {}).get("columns")
                          or sr.get("schema", {}).get("columns") or [])
                cols = [c.get("name") for c in schema]
                data = (sr.get("result", {}).get("data_array")
                        or sr.get("data_array") or [])
                return cols, data
            except Exception:
                continue
        return None


# ---------------------------------------------------------------------------
# High-level bridge used by the Streamlit app
# ---------------------------------------------------------------------------
class GenieBridge:
    def __init__(self, data: dict | None = None):
        self.data = data or {}
        self.client = GenieClient()
        self._connected = None  # lazily health-checked

    # -- mode -----------------------------------------------------------------
    @property
    def mode(self) -> str:
        if self._connected is None:
            self._connected = self.client.health_check() if self.client.configured else False
        return GENIE_CONNECTED if self._connected else DEMO_MODE

    @property
    def status_note(self) -> str:
        if self.mode == GENIE_CONNECTED:
            return f"Databricks Genie connected · space {self.client.space_id[:8]}…"
        reason = self.client.last_error or "no Databricks credentials set"
        return f"Demo fallback mode · {reason}"

    def force_recheck(self):
        self._connected = None
        return self.mode

    # -- data-grounded Q&A --------------------------------------------------
    def data_answer(self, question: str) -> dict:
        """Answer a campus-data question. Real Genie if connected, else local."""
        if self.mode == GENIE_CONNECTED:
            res = self.client.ask(question)
            if res.get("ok"):
                return {"source": "genie", "text": res["text"] or "(Genie returned a table)",
                        "sql": res.get("sql"), "columns": res.get("columns"), "rows": res.get("rows")}
            # fall through to demo on failure, but say so
            return {"source": "demo_fallback", "text": _demo_answer(question, self.data),
                    "note": f"Genie call failed ({res.get('error')}) — showing local answer."}
        return {"source": "demo", "text": _demo_answer(question, self.data)}

    # -- scenario explanation --------------------------------------------
    def explain_scenario(self, sim: dict) -> str:
        """Genie EXPLAINS the numbers the engine computed. It does not compute them."""
        base = sim.get("why", "")
        closer = sim.get("genie_closer", "")
        if self.mode == GENIE_CONNECTED:
            prompt = _explain_prompt(sim)
            res = self.client.ask(prompt)
            if res.get("ok") and res.get("text"):
                return res["text"].strip() + "\n\n" + closer
        return base + "\n\n" + closer

    # -- optional: let Genie suggest a clarifying question --------------
    def suggest_clarification(self, wish_text: str, so_far: dict) -> str | None:
        if self.mode != GENIE_CONNECTED:
            return None
        q = (f"A student wished: '{wish_text}'. Known so far: {so_far}. "
             f"Ask ONE short clarifying question to narrow this campus wish. "
             f"Do not answer it, do not run calculations.")
        res = self.client.ask(q)
        return res.get("text") if res.get("ok") else None

    def narrow(self, wish_text: str, answers: dict, step: int, max_steps: int = 5):
        """One live Akinator-style multiple-choice question from Genie.

        Returns {key, genie, prompt, options:[{label,value}]} or None (caller
        then falls back to the deterministic tree). Never raises.
        """
        if self.mode != GENIE_CONNECTED:
            return None
        import json
        import re
        asked = "; ".join(f"{k}={v}" for k, v in answers.items()) or "nothing yet"
        prompt = (
            "You are the GENIEPOLIS campus genie, narrowing a student's wish like a "
            "playful Akinator. Ground your options in the campus tables when useful.\n"
            f'WISH: "{wish_text}"\n'
            f"ANSWERS SO FAR: {asked}\n"
            f"This is question {step + 1} of at most {max_steps}. Ask something NOT already "
            "covered. Reply with ONLY a compact JSON object, no prose:\n"
            '{"genie":"<one witty sentence>","prompt":"<short question>",'
            '"options":[{"label":"<short>","value":"<slug>"}, 3 or 4 items]}'
        )
        res = self.client.ask(prompt, new_conversation=(step == 0))
        if not res.get("ok") or not res.get("text"):
            return None
        m = re.search(r"\{.*\}", res["text"], re.S)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
            opts = []
            for o in obj.get("options", [])[:4]:
                lbl = str(o["label"])[:60].strip()
                val = str(o.get("value", lbl)).strip().lower().replace(" ", "_")[:40]
                if lbl:
                    opts.append({"label": lbl, "value": val or lbl.lower()})
            if len(opts) < 2:
                return None
            return {
                "key": f"g{step}",
                "genie": str(obj.get("genie", "Hmm.")).strip()[:180] or "Hmm.",
                "prompt": str(obj.get("prompt", "Pick one")).strip()[:180] or "Pick one",
                "options": opts,
            }
        except Exception:
            return None


# ---------------------------------------------------------------------------
# DEMO_MODE local answers over the synthetic data
# ---------------------------------------------------------------------------
def _explain_prompt(sim: dict) -> str:
    m = sim.get("metrics", {})
    lines = [f"- {k}: {v['before']}{v.get('unit','')} -> {v['after']}{v.get('unit','')} "
             f"({v['delta_pct']:+}% )" for k, v in m.items()]
    return (
        "You are the GENIEPOLIS Campus Genie. A deterministic simulation already "
        "computed the following before/after metrics for the wish "
        f"\"{sim.get('raw_text','')}\" ({sim.get('scenario',{}).get('title','')}). "
        "Do NOT recompute or invent numbers. In 3-4 witty but clear sentences, explain "
        "WHY these shifts happen and name the single biggest ripple.\n" + "\n".join(lines)
    )


def _demo_answer(question: str, data: dict) -> str:
    q = (question or "").lower()
    if not data:
        return "Demo data not loaded yet."
    occ = data.get("occupancy")
    snap = data.get("snapshot", {})

    if "available" in q and "room" in q:
        s = snap.get("academic_block", {})
        return (f"Main Academic Block: ~{s.get('available_rooms','?')} of {s.get('rooms','?')} rooms free right now, "
                f"{s.get('classes_running','?')} classes running. [synthetic]")
    names = data["buildings"].set_index("id")["name"].to_dict()
    if "highest occupancy" in q or ("busiest" in q and "building" in q):
        if occ is not None:
            bt = data["buildings"].set_index("id")["type"].to_dict()
            cur = occ[occ.hour == 16].copy()
            cur = cur[~cur.building_id.map(bt).isin(["parking", "gate", "transport"])]
            cur = cur.sort_values("occupancy_rate", ascending=False).head(3)
            rows = ", ".join(f"{names.get(r.building_id, r.building_id)} ({r.occupancy_rate:.0%})"
                             for r in cur.itertuples())
            return f"Highest building occupancy at 4 PM: {rows}. [synthetic]"
    if "parking" in q and ("busiest" in q or "full" in q or "occup" in q):
        pk = data["parking"]
        cur = pk[pk.hour == 16].sort_values("occupancy_rate", ascending=False).iloc[0]
        return (f"{names.get(cur.parking_id, cur.parking_id)} is fullest at 4 PM: "
                f"{cur.occupancy_rate:.0%} ({cur.occupied}/{cur.capacity}). [synthetic]")
    if "traffic" in q and ("highest" in q or "peak" in q or "worst" in q):
        tr = data["traffic"]
        worst = tr.sort_values("congestion", ascending=False).iloc[0]
        return f"Traffic peaks around {int(worst.hour):02d}:00 on the {worst.road_id.replace('_',' ')} (congestion {worst.congestion:.0%}). [synthetic]"
    if "most classes" in q or ("building" in q and "class" in q):
        cls = data["classes"].groupby("building_id").size().sort_values(ascending=False)
        names = data["buildings"].set_index("id")["name"].to_dict()
        top = cls.index[0]
        return f"{names.get(top, top)} runs the most classes ({int(cls.iloc[0])} scheduled). [synthetic]"
    if "faculty" in q and "academic" in q:
        s = snap.get("academic_block", {})
        return (f"~{s.get('faculty_present','?')} faculty linked to the Academic Block: "
                f"{s.get('faculty_in_class','?')} in class, {s.get('faculty_in_office','?')} in offices. [synthetic]")
    if "issue" in q and ("most" in q or "frequent" in q or "common" in q):
        top = data["issues"]["type"].value_counts().idxmax()
        n = int(data["issues"]["type"].value_counts().max())
        return f"Most reported issue: “{top}” ({n} reports). [synthetic]"
    if "requested" in q or ("wish" in q and ("most" in q or "top" in q)) or "improvement" in q:
        wh = data["wish_history"]["wish_text"].value_counts().head(3)
        return "Top student wishes: " + "; ".join(f"{t} ({c})" for t, c in wh.items()) + ". [synthetic]"
    if "parking demand" in q and "evening" in q:
        return ("When evening activity rises, Parking Zone B demand climbs ~12-22% because players, "
                "spectators and event visitors compete for the same fixed capacity. [synthetic + relationships table]")
    return ("I can answer campus-data questions like: available rooms in the academic block, "
            "busiest parking, peak traffic hour, most-requested improvements. (Demo mode over synthetic data.)")
