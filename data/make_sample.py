"""Genera un CSV de pólizas sintéticas con errores intencionados para probar el pipeline."""

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent / "policies_sample.csv"


def main(n: int = 2000, seed: int = 7) -> None:
    rng = np.random.default_rng(seed)
    products = ["auto", "hogar", "vida", "salud", "AUTO"]
    regions = ["Madrid", "Valencia", "Sevilla", "Bilbao", "Barcelona"]

    df = pd.DataFrame(
        {
            "policy_id": [f"P{i:06d}" for i in range(n)],
            "customer_id": [f"C{rng.integers(1, 800):05d}" for _ in range(n)],
            "start_date": pd.to_datetime("2023-01-01") + pd.to_timedelta(rng.integers(0, 730, n), unit="D"),
            "premium": rng.lognormal(5.5, 0.4, n).round(2),
            "product": rng.choice(products, n),
            "region": rng.choice(regions, n),
            "claim_amount": (rng.exponential(200, n) * (rng.uniform(size=n) < 0.3)).round(2),
        }
    )
    # Errores intencionados para validar las reglas de calidad
    df.loc[rng.choice(n, 20, replace=False), "premium"] = -1
    df.loc[rng.choice(n, 15, replace=False), "customer_id"] = None
    df = pd.concat([df, df.head(10)], ignore_index=True)  # duplicados

    df["start_date"] = df["start_date"].dt.strftime("%Y-%m-%d")
    df.to_csv(OUT, index=False)
    print(f"Escrito {OUT} con {len(df)} filas")


if __name__ == "__main__":
    main()
