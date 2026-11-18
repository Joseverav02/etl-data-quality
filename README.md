# etl-data-quality

Pipeline ETL en Python con **validaciones de calidad de datos** y carga a un **modelo en estrella** en SQLite, listo para conectar a Power BI.

> Datos **sintéticos** (pólizas ficticias) generados por `data/make_sample.py`.

## Qué demuestra
- Separación clara en etapas: extract → validate → transform → load.
- Reglas de calidad (claves nulas, fechas inválidas, primas negativas, productos desconocidos, duplicados).
- Las filas rechazadas se **cuentan y se informan**, no se descartan en silencio.
- Modelo en estrella (tabla de hechos + dimensiones) con métrica derivada (`loss_ratio`).
- Tests automatizados con `pytest`.

## Uso

```bash
pip install -r requirements.txt
python data/make_sample.py
PYTHONPATH=src python -c "from pathlib import Path; from etl.pipeline import run; print(run(Path('data/policies_sample.csv'), Path('warehouse.db')))"
pytest -q
```

Ejemplo de salida con los datos de muestra: 2010 filas de entrada, 1965 válidas y 45 rechazadas (15 claves nulas, 20 primas negativas y 10 duplicados).

## Estructura

```
src/etl/pipeline.py   # extract, validate, transform, load
data/make_sample.py   # generador de datos con errores intencionados
tests/
```

## Licencia
MIT
