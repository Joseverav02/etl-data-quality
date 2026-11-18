# etl-data-quality

[![CI](https://github.com/Joseverav02/etl-data-quality/actions/workflows/ci.yml/badge.svg)](https://github.com/Joseverav02/etl-data-quality/actions/workflows/ci.yml)

Pipeline ETL en Python con **validaciones de calidad de datos** y carga a un **modelo en estrella** en SQLite, con vistas de KPI listas para conectar a Power BI.

> Datos **sintéticos** (pólizas ficticias) generados por `data/make_sample.py`. Ver el [diccionario de datos](docs/data_dictionary.md).

## Principio de diseño
Ninguna fila se descarta en silencio. Cada regla cuenta sus incidencias y el informe indica cuántas filas entraron, cuántas se cargaron y por qué se rechazaron. Así se puede auditar el proceso y detectar problemas en el origen.

## Resultado con los datos de muestra

| Entrada | Válidas | Rechazadas |
|---|---|---|
| 2010 | 1965 | 45 |

| Regla | Incidencias |
|---|---|
| Clave nula (`policy_id` o `customer_id`) | 15 |
| Prima nula o ≤ 0 | 20 |
| Póliza duplicada | 10 |
| Fecha inválida, siniestro negativo, producto desconocido | 0 en esta muestra, cubiertas por tests |

Siniestralidad por producto (`v_loss_ratio_by_product`):

| Producto | Pólizas | Primas | Siniestros | Loss ratio |
|---|---|---|---|---|
| auto | 803 | 208 701 | 44 582 | 0,214 |
| hogar | 425 | 113 009 | 31 374 | 0,278 |
| vida | 373 | 100 412 | 21 499 | 0,214 |
| salud | 364 | 100 394 | 19 864 | 0,198 |

## Qué demuestra
- Etapas separadas: extract → validate → transform → load.
- Reglas de calidad explícitas, con recuento por regla.
- Modelo en estrella: tabla de hechos, dimensiones y métrica derivada (`loss_ratio`).
- **Carga idempotente:** volver a ejecutar reemplaza las tablas y no duplica datos.
- Vistas SQL para KPI (`sql/kpis.sql`).
- Tests con `pytest` (9 casos) y CI en GitHub Actions con una ejecución de extremo a extremo.

## Uso

```bash
pip install -r requirements.txt
python data/make_sample.py
PYTHONPATH=src python -m etl --input data/policies_sample.csv --db warehouse.db --report reports/quality_report.json
pytest -q
```

## Estructura

```
src/etl/
  pipeline.py    # extract, validate, transform, load
  __main__.py    # CLI
sql/kpis.sql     # vistas para Power BI
data/make_sample.py
docs/data_dictionary.md
reports/quality_report.json
tests/test_pipeline.py
```

## Próximas mejoras
- Orquestación con Airflow o Prefect y ejecución programada.
- Pruebas de contrato sobre el esquema de entrada (por ejemplo, con pandera).
- Carga incremental por fecha de modificación en lugar de carga completa.
- Conexión directa a SQL Server con SQLAlchemy.

## Licencia
MIT
