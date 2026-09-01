"""
Export all synthetic GENIEPOLIS tables to CSV for upload into Databricks
(Data > Create table > Upload files, target schema = geniepolis.campus).

Run from the project root:
    python databricks/export_csvs.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.synthetic_data import generate_all  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")


def main():
    os.makedirs(OUT, exist_ok=True)
    data = generate_all()
    for name, df in data.items():
        if name == "snapshot":
            continue
        path = os.path.join(OUT, f"{name}.csv")
        df.to_csv(path, index=False)
        print(f"  wrote {path:<45} {len(df):>6} rows")
    print(f"\nDone. {len(os.listdir(OUT))} CSVs in {OUT}")
    print("Next: upload each to Databricks schema  geniepolis.campus  (keep the file name as the table name).")


if __name__ == "__main__":
    main()
