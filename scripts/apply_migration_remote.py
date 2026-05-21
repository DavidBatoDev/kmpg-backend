"""Apply supabase/migrations/*.sql to hosted Postgres (uses .env SUPABASE_*)."""
from pathlib import Path
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

project_ref = os.environ["SUPABASE_PROJECT_REF"]
db_password = os.environ["SUPABASE_DB_PASSWORD"]

conninfo = (
    f"host=db.{project_ref}.supabase.co port=5432 dbname=postgres "
    f"user=postgres password={db_password} sslmode=require"
)

migration = (
    Path(__file__).resolve().parents[1]
    / "supabase/migrations/20260521120000_init_academic_context_schema.sql"
)
seed = Path(__file__).resolve().parents[1] / "supabase/seed.sql"


def run_sql(cur, sql: str, label: str) -> None:
    print(f"Running {label}...")
    cur.execute(sql)
    print(f"OK: {label}")


def main() -> None:
    sql = migration.read_text(encoding="utf-8")
    seed_sql = seed.read_text(encoding="utf-8")

    with psycopg2.connect(conninfo) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            run_sql(cur, sql, migration.name)
            run_sql(cur, seed_sql, seed.name)

    print(f"Done. Project: {project_ref}")


if __name__ == "__main__":
    main()
