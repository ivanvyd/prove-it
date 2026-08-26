# Databricks notebook source
# MAGIC %md
# MAGIC # Prove It — build the tables
# MAGIC
# MAGIC Run this once in a Databricks Free Edition workspace. It creates the two tables the
# MAGIC Genie space sits over.
# MAGIC
# MAGIC **Table 1 — `student_scores` (synthetic).** Per-student rows, generated with a fixed
# MAGIC seed. Synthetic is the honest choice rather than the convenient one: the lesson turns
# MAGIC on a small gap between group means hiding a large spread *within* each group, and open
# MAGIC education data is published as country-level aggregates that cannot express that.
# MAGIC
# MAGIC **Table 2 — `country_indicators` (real).** Genuine public data, loaded from a CSV you
# MAGIC upload. Free Edition restricts outbound internet, so this notebook does not download
# MAGIC it — see the cell near the bottom.
# MAGIC
# MAGIC The generator itself lives in `prove_it/demo_data.py` rather than in this notebook, so
# MAGIC the app, the tests and this notebook cannot drift apart. `tests/test_demo_data.py`
# MAGIC regenerates from the seed and fails if the numbers quoted anywhere stop matching.

# COMMAND ----------

import sys

# Point this at wherever the repo is synced in the workspace. With Databricks Repos /
# Git folders, the notebook already sits inside the repo, so the parent's `src` is right.
REPO_SRC = "../src"
if REPO_SRC not in sys.path:
    sys.path.insert(0, REPO_SRC)

from prove_it.demo_data import (  # noqa: E402
    CATALOG,
    COLUMN_COMMENTS,
    GROUPS,
    INDICATORS_TABLE,
    OBSERVED,
    SCHEMA,
    STUDENTS_TABLE,
    TABLE_COMMENT,
    effect_size,
    generate_students,
)

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"Using {CATALOG}.{SCHEMA}")
print(f"Groups requested: {dict(GROUPS)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table 1 — student_scores

# COMMAND ----------

students = generate_students()
print(students.groupby("gender")[["maths_score", "reading_score"]].agg(["count", "mean", "std"]))

# COMMAND ----------

(
    spark.createDataFrame(students)
    .write.mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(STUDENTS_TABLE)
)

# Quotes doubled, not interpolated raw: these comments are English prose about pupils, and
# prose acquires apostrophes. Without this, adding "the pupil's score" produces a statement
# with an unbalanced quote.
def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


spark.sql(f"COMMENT ON TABLE {STUDENTS_TABLE} IS {sql_literal(TABLE_COMMENT)}")

for column, comment in COLUMN_COMMENTS.items():
    spark.sql(
        f"ALTER TABLE {STUDENTS_TABLE} ALTER COLUMN {column} COMMENT {sql_literal(comment)}"
    )

print(f"{STUDENTS_TABLE} written and documented")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Check the lesson still lands
# MAGIC
# MAGIC The demo only works while the maths gap is negligible. If the effect size climbs above
# MAGIC 0.2, the repaired query would *confirm* the claim rather than overturn it and the whole
# MAGIC lesson inverts. This is asserted in the test suite too; it is repeated here because
# MAGIC this is where the data is actually created.

# COMMAND ----------

check = spark.sql(f"""
    SELECT gender, COUNT(*) AS students,
           ROUND(AVG(maths_score), 1) AS avg_score,
           ROUND(STDDEV(maths_score), 1) AS spread
    FROM {STUDENTS_TABLE}
    GROUP BY gender
""").toPandas()

print(check)
print("\nExpected, from prove_it.demo_data.OBSERVED:")
for gender, o in OBSERVED.items():
    print(f"  {gender:5s} n={o.students} avg={o.maths_mean} spread={o.maths_sd}")

e = effect_size()
print(f"\neffect size {e:.3f}")
print(
    "OK — the gap is negligible, the lesson will land."
    if e < 0.2
    else "PROBLEM — the gap is too large; the repaired query would confirm the claim."
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table 2 — country_indicators (real public data)
# MAGIC
# MAGIC **Download it yourself and upload the CSV** — Free Edition restricts outbound internet,
# MAGIC so this notebook deliberately does not fetch it. Either source works:
# MAGIC
# MAGIC - World Bank Open Data — <https://data.worldbank.org/indicator> (e.g. `SE.XPD.TOTL.GD.ZS`,
# MAGIC   government expenditure on education as % of GDP), "Download CSV".
# MAGIC - Our World in Data — <https://ourworldindata.org/> — any indicator, "Download" → CSV.
# MAGIC
# MAGIC Then: **Catalog → workspace → prove_it → Create table → Upload file**, name it
# MAGIC `country_indicators`, and run the cell below. Do not tidy the column names — leaving
# MAGIC them as published is part of what makes it real, and the column comments carry the
# MAGIC meaning for Genie.

# COMMAND ----------

if spark.catalog.tableExists(INDICATORS_TABLE):
    spark.sql(f"""
        COMMENT ON TABLE {INDICATORS_TABLE} IS
        'Real published country-level indicators, downloaded from a public source. One row
         per country per year. Aggregate data: it has no per-person rows, so it can compare
         countries but cannot say anything about any individual.'
    """)
    display(spark.table(INDICATORS_TABLE).limit(10))
    print("country_indicators documented")
else:
    print(
        f"{INDICATORS_TABLE} does not exist yet.\n"
        "Upload the CSV first (see the cell above), then re-run this cell.\n"
        "The app works without it — you lose the second demo rumour, not the product."
    )
