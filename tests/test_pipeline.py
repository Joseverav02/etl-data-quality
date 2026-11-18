import sqlite3

import pandas as pd
import pytest

from etl.pipeline import REQUIRED_COLUMNS, run, transform, validate


def sample_df():
    return pd.DataFrame(
        [
            ["P1", "C1", "2024-01-10", 300.0, "auto", "Madrid", 100.0],
            ["P2", "C2", "2024-02-11", 150.0, "hogar", "Valencia", 0.0],
            ["P2", "C2", "2024-02-11", 150.0, "hogar", "Valencia", 0.0],   # duplicado
            ["P3", None, "2024-03-01", 90.0, "vida", "Sevilla", 10.0],     # clave nula
            ["P4", "C4", "fecha-mala", 90.0, "salud", "Bilbao", 10.0],     # fecha inválida
            ["P5", "C5", "2024-04-01", -5.0, "auto", "Madrid", 0.0],       # prima negativa
            ["P6", "C6", "2024-04-02", 80.0, "moto", "Madrid", 0.0],       # producto desconocido
        ],
        columns=REQUIRED_COLUMNS,
    )


def test_validate_rejects_bad_rows_and_counts_them():
    clean, report = validate(sample_df())
    assert list(clean["policy_id"]) == ["P1", "P2"]
    assert report.rows_in == 7
    assert report.rows_out == 2
    assert report.issues["duplicate_policy"] == 1
    assert report.issues["unknown_product"] == 1


def test_missing_required_column_raises():
    with pytest.raises(ValueError):
        validate(sample_df().drop(columns=["premium"]))


def test_transform_builds_star_schema_with_loss_ratio():
    clean, _ = validate(sample_df())
    tables = transform(clean)
    assert set(tables) == {"dim_customer", "dim_product", "dim_region", "fact_policy"}
    fact = tables["fact_policy"]
    assert fact.loc[fact["policy_id"] == "P1", "loss_ratio"].item() == pytest.approx(100 / 300)


def test_run_loads_sqlite(tmp_path):
    csv = tmp_path / "policies.csv"
    sample_df().to_csv(csv, index=False)
    db = tmp_path / "warehouse.db"
    report = run(csv, db)
    assert report.rows_out == 2
    with sqlite3.connect(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM fact_policy").fetchone()[0]
    assert count == 2
