import sqlite3

import pandas as pd
import pytest

from etl.__main__ import main
from etl.pipeline import REQUIRED_COLUMNS, extract, run, transform, validate


def sample_df():
    return pd.DataFrame(
        [
            ["P1", "C1", "2024-01-10", 300.0, "auto", "Madrid", 100.0],
            ["P2", "C2", "2024-02-11", 150.0, "Hogar", "Valencia", 0.0],   # mayúsculas válidas
            ["P2", "C2", "2024-02-11", 150.0, "hogar", "Valencia", 0.0],   # duplicado
            ["P3", None, "2024-03-01", 90.0, "vida", "Sevilla", 10.0],     # clave nula
            ["P4", "C4", "fecha-mala", 90.0, "salud", "Bilbao", 10.0],     # fecha inválida
            ["P5", "C5", "2024-04-01", -5.0, "auto", "Madrid", 0.0],       # prima negativa
            ["P6", "C6", "2024-04-02", None, "auto", "Madrid", 0.0],       # prima nula
            ["P7", "C7", "2024-04-03", 80.0, "moto", "Madrid", 0.0],       # producto desconocido
            ["P8", "C8", "2024-04-04", 80.0, "auto", "Madrid", -1.0],      # siniestro negativo
        ],
        columns=REQUIRED_COLUMNS,
    )


def test_validate_keeps_only_valid_rows_and_counts_each_rule():
    clean, report = validate(sample_df())
    assert list(clean["policy_id"]) == ["P1", "P2"]
    assert report.rows_in == 9
    assert report.rows_out == 2
    assert report.rows_rejected == 7
    assert report.issues["null_key"] == 1
    assert report.issues["bad_date"] == 1
    assert report.issues["null_or_bad_premium"] == 2
    assert report.issues["negative_claim"] == 1
    assert report.issues["unknown_product"] == 1
    assert report.issues["duplicate_policy"] == 1


def test_product_is_normalised_to_lowercase():
    clean, _ = validate(sample_df())
    assert set(clean["product"]) <= {"auto", "hogar", "vida", "salud"}
    assert "Hogar" not in set(clean["product"]) and "hogar" in set(clean["product"])


def test_missing_required_column_raises():
    with pytest.raises(ValueError, match="premium"):
        validate(sample_df().drop(columns=["premium"]))


def test_empty_input_gives_empty_output():
    clean, report = validate(pd.DataFrame(columns=REQUIRED_COLUMNS))
    assert clean.empty
    assert report.rows_in == 0 and report.rows_out == 0


def test_transform_builds_star_schema_and_loss_ratio():
    clean, _ = validate(sample_df())
    tables = transform(clean)
    assert set(tables) == {"dim_customer", "dim_product", "dim_region", "fact_policy"}
    fact = tables["fact_policy"].set_index("policy_id")
    assert fact.loc["P1", "loss_ratio"] == pytest.approx(round(100 / 300, 4))
    assert fact.loc["P1", "start_date"] == "2024-01-10"


def test_run_loads_tables_and_kpi_views(tmp_path):
    csv = tmp_path / "policies.csv"
    sample_df().to_csv(csv, index=False)
    db = tmp_path / "warehouse.db"

    report = run(csv, db)
    assert report.rows_out == 2

    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM fact_policy").fetchone()[0] == 2
        views = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
        ).fetchall()
    assert [v[0] for v in views] == ["v_loss_ratio_by_product", "v_monthly_premium", "v_region_summary"]


def test_load_is_idempotent(tmp_path):
    csv = tmp_path / "policies.csv"
    sample_df().to_csv(csv, index=False)
    db = tmp_path / "warehouse.db"
    run(csv, db)
    run(csv, db)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM fact_policy").fetchone()[0] == 2


def test_extract_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract(tmp_path / "no_existe.csv")


def test_cli_writes_report(tmp_path):
    csv = tmp_path / "policies.csv"
    sample_df().to_csv(csv, index=False)
    report_path = tmp_path / "report.json"
    code = main(["--input", str(csv), "--db", str(tmp_path / "w.db"), "--report", str(report_path)])
    assert code == 0
    assert '"rows_out": 2' in report_path.read_text(encoding="utf-8")
