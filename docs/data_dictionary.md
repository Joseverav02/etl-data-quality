# Diccionario de datos

## Entrada: `policies.csv`
| Columna | Tipo | Obligatoria | Regla de calidad |
|---|---|---|---|
| `policy_id` | texto | sí | no nula, única (se conserva la primera aparición) |
| `customer_id` | texto | sí | no nula |
| `start_date` | fecha `YYYY-MM-DD` | sí | parseable |
| `premium` | decimal | sí | no nula y > 0 |
| `product` | texto | sí | `auto`, `hogar`, `vida` o `salud` (sin distinguir mayúsculas) |
| `region` | texto | sí | sin reglas de dominio |
| `claim_amount` | decimal | sí | no nulo y ≥ 0 |

## Salida: modelo en estrella (SQLite)
| Tabla | Tipo | Clave | Contenido |
|---|---|---|---|
| `fact_policy` | hechos | `policy_id` | una fila por póliza válida, con `loss_ratio = claim_amount / premium` |
| `dim_customer` | dimensión | `customer_id` | clientes distintos |
| `dim_product` | dimensión | `product` | catálogo de productos válidos |
| `dim_region` | dimensión | `region` | regiones presentes en los datos |

## Vistas para Power BI
| Vista | Uso |
|---|---|
| `v_loss_ratio_by_product` | siniestralidad por producto |
| `v_monthly_premium` | primas y pólizas nuevas por mes |
| `v_region_summary` | siniestralidad por región |

## Informe de calidad
Cada ejecución devuelve `rows_in`, `rows_out`, `rows_rejected` y el número de incidencias por regla.
