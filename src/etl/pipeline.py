"""Pipeline ETL con validaciones de calidad de datos.

Extract -> Validate -> Transform -> Load (SQLite, modelo en estrella).

Principio: ninguna fila se descarta en silencio. Cada regla cuenta sus incidencias
y el informe final indica cuántas filas entraron, cuántas se cargaron y por qué se rechazaron.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

logger = logging.getLogger("etl")

REQUIRED_COLUMNS = [
    "policy_id", "customer_id", "start_date", "premium", "product", "region", "claim_amount",
]
VALID_PRODUCTS = ("auto", "hogar", "vida", "salud")


@dataclass
class QualityReport:
    rows_in: int = 0
    rows_out: int = 0
    issues: dict[str, int] = field(default_factory=dict)

    @property
    def rows_rejected(self) -> int:
        return self.rows_in - self.rows_out

    def to_dict(self) -> dict:
        return {
            "rows_in": self.rows_in,
            "rows_out": self.rows_out,
            "rows_rejected": self.rows_rejected,
            "issues": dict(self.issues),
        }


def extract(path: Path) -> pd.DataFrame:
    """Lee el CSV de origen manteniendo los identificadores como texto."""
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de entrada: {path}")
    return pd.read_csv(path, dtype={"policy_id": str, "customer_id": str})


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["product"] = out["product"].astype("string").str.strip().str.lower()
    out["region"] = out["region"].astype("string").str.strip()
    out["start_date"] = pd.to_datetime(out["start_date"], errors="coerce")
    for col in ("premium", "claim_amount"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def validate(df: pd.DataFrame) -> tuple[pd.DataFrame, QualityReport]:
    """Aplica las reglas de calidad y devuelve solo las filas válidas más el informe."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {missing}")

    df = _normalise(df)
    report = QualityReport(rows_in=len(df))

    rules = {
        "null_key": df["policy_id"].isna() | df["customer_id"].isna(),
        "bad_date": df["start_date"].isna(),
        "null_or_bad_premium": df["premium"].isna() | (df["premium"] <= 0),
        "negative_claim": df["claim_amount"].isna() | (df["claim_amount"] < 0),
        "unknown_product": ~df["product"].isin(VALID_PRODUCTS),
    }
    invalid = pd.Series(False, index=df.index)
    for name, mask in rules.items():
        mask = mask.fillna(True).astype(bool)
        report.issues[name] = int(mask.sum())
        invalid |= mask

    duplicated = df["policy_id"].duplicated(keep="first") & ~invalid
    report.issues["duplicate_policy"] = int(duplicated.sum())
    invalid |= duplicated

    clean = df.loc[~invalid].copy()
    report.rows_out = len(clean)
    logger.info("Validación: %d de %d filas válidas", report.rows_out, report.rows_in)
    return clean, report


def transform(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Modelo en estrella: una tabla de hechos y dimensiones de cliente, producto y región."""
    df = df.copy()
    df["loss_ratio"] = (df["claim_amount"] / df["premium"]).round(4)
    df["start_date"] = df["start_date"].dt.strftime("%Y-%m-%d")

    return {
        "dim_customer": df[["customer_id"]].drop_duplicates().reset_index(drop=True),
        "dim_product": pd.DataFrame({"product": list(VALID_PRODUCTS)}),
        "dim_region": pd.DataFrame({"region": sorted(df["region"].dropna().unique())}),
        "fact_policy": df[[
            "policy_id", "customer_id", "product", "region", "start_date",
            "premium", "claim_amount", "loss_ratio",
        ]].reset_index(drop=True),
    }


def load(tables: dict[str, pd.DataFrame], db_path: Path) -> None:
    """Carga las tablas reemplazándolas por completo (carga idempotente)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        for name, table in tables.items():
            table.to_sql(name, conn, if_exists="replace", index=False)
        conn.executescript(Path(__file__).parents[2].joinpath("sql", "kpis.sql").read_text(encoding="utf-8"))


def run(input_csv: Path, db_path: Path) -> QualityReport:
    raw = extract(input_csv)
    clean, report = validate(raw)
    load(transform(clean), db_path)
    logger.info("Carga completada en %s", db_path)
    return report
