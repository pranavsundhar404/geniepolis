"""
Quick standalone check that GENIEPOLIS can reach your Databricks Genie space.
No Streamlit needed.

Usage (from the project root, with .env filled in):
    python databricks/test_connection.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from databricks.genie_client import GenieClient  # noqa: E402


def main():
    c = GenieClient()
    print("HOST      :", c.host or "(missing)")
    print("SPACE_ID  :", c.space_id or "(missing)")
    print("TOKEN     :", "set" if c.token else "(missing)")
    print("-" * 50)

    if not c.configured:
        print("❌ Not configured. Fill DATABRICKS_HOST / DATABRICKS_TOKEN / GENIE_SPACE_ID in .env")
        return

    print("1) health check ...")
    ok = c.health_check()
    print("   ", "✅ reachable" if ok else f"❌ {c.last_error}")
    if not ok:
        return

    q = "Which buildings have the highest occupancy?"
    print(f"2) asking Genie: {q!r} ...")
    res = c.ask(q, new_conversation=True)
    if res.get("ok"):
        print("   ✅ Genie answered:")
        print("   ", (res.get("text") or "(table only)").replace("\n", "\n    "))
        if res.get("sql"):
            print("   SQL:", res["sql"][:200])
        if res.get("rows"):
            print("   rows:", res["rows"][:3])
        print("\n🎉 Connection works. Run:  streamlit run app.py")
    else:
        print("   ❌", res.get("error"))
        print("   Common fixes: token expired/insufficient scope, wrong SPACE_ID, "
              "space has no tables added, or workspace not entitled for the Genie API.")


if __name__ == "__main__":
    main()
