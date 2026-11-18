"""Pipeline ETL con validaciones de calidad de datos.

Extract -> Validate -> Transform -> Load (SQLite, modelo en estrella).
Los datos de ejemplo son sintéticos (pólizas ficticias).
"""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ["policy_id", "customer_id", "start_date", "premium", "product", "region", "claim_amount"]
VALID_PRODUCTS = {"auto", "hogar", "vida", "salud"}


@dataclass
class QualityReport:
    rows_in: int
    rows_out: int
    issues: dict = field(default_factory=dict)

    @property
    def rows_rejected(self) -> int:
        return self.rows_in - self.rows_out


def extract(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"policy_id": str, "customer_id": str})


def validate(df: pd.DataFrame) -> tuple[pd.DataFrame, QualityReport]:
    """Aplica reglas de calidad. Las filas inválidas se separan y se cuentan, no se pierden en silencio."""
    report = QualityReport(rows_in=len(df), rows_out=0)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {missing}")

    issues = {}
    df = df.copy()
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")

    checks = {
        "null_key": df["policy_id"].isna() | df["customer_id"].isna(),
        "bad_date": df["start_date"].isna(),
        "negative_premium": df["premium"] <= 0,
        "negative_claim": df["claim_amount"] < 0,
        "unknown_product": ~df["product"].str.lower().isin(VALID_PRODUCTS),
    }
    invalid = pd.Series(False, index=df.index)
    for name, mask in checks.items():
        mask = mask.fillna(True)
        issues[name] = int(mask.sum())
        invalid |= mask

    duplicates = df["policy_id"].duplicated(keep="first") & ~invalid
    issues["duplicate_policy"] = int(duplicates.sum())
    invalid |= duplicates

    report.issues = issues
    clean = df[~invalid].copy()
    report.rows_out = len(clean)
    return clean, report


def transform(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Construye un modelo en estrella: una tabla de hechos y dimensiones simples."""
    df = df.copy()
    df["product"] = df["product"].str.lower()
    df["loss_ratio"] = df["claim_amount"] / df["premium"]

    dim_customer = df[["customer_id"]].drop_duplicates().reset_index(drop=True)
    dim_product = pd.DataFrame({"product": sorted(VALID_PRODUCTS)})
    dim_region = pd.DataFrame({"region": sorted(df["region"].dropna().unique())})

    fact_policy = df[
        ["policy_id", "customer_id", "product", "region", "start_date", "premium", "claim_amount", "loss_ratio"]
    ]
    return {
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_region": dim_region,
        "fact_policy": fact_policy,
    }


def load(tables: dict[str, pd.DataFrame], db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        for name, table in tables.items():
            table.to_sql(name, conn, if_exists="replace", index=False)


def run(input_csv: Path, db_path: Path) -> QualityReport:
    raw = extract(input_csv)
    clean, report = validate(raw)
    tables = transform(clean)
    load(tables, db_path)
    return report
