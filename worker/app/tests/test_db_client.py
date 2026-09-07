from sqlalchemy.dialects import postgresql

from app.services.db_client import CLAIM_NEXT_JOB_SQL, RECOVER_STALE_GENERATION_JOBS_SQL


def test_claim_query_uses_postgres_row_locking() -> None:
    sql = str(CLAIM_NEXT_JOB_SQL.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "status = 'pending'" in sql
    assert "status = 'running'" in sql


def test_stale_generation_recovery_requeues_interrupted_jobs() -> None:
    sql = str(RECOVER_STALE_GENERATION_JOBS_SQL.compile(dialect=postgresql.dialect()))
    assert "status = 'pending'" in sql
    assert "job_type = 'background_generation'" in sql
    assert "status = 'running'" in sql
