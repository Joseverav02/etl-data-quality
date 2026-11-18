-- Vistas de KPI para Power BI. Se recrean en cada carga.
DROP VIEW IF EXISTS v_loss_ratio_by_product;
CREATE VIEW v_loss_ratio_by_product AS
SELECT
    product,
    COUNT(*)                                   AS policies,
    ROUND(SUM(premium), 2)                     AS total_premium,
    ROUND(SUM(claim_amount), 2)                AS total_claims,
    ROUND(SUM(claim_amount) / SUM(premium), 4) AS loss_ratio
FROM fact_policy
GROUP BY product;

DROP VIEW IF EXISTS v_monthly_premium;
CREATE VIEW v_monthly_premium AS
SELECT
    substr(start_date, 1, 7) AS month,
    COUNT(*)                 AS new_policies,
    ROUND(SUM(premium), 2)   AS premium
FROM fact_policy
GROUP BY month
ORDER BY month;

DROP VIEW IF EXISTS v_region_summary;
CREATE VIEW v_region_summary AS
SELECT
    region,
    COUNT(*)                                   AS policies,
    ROUND(SUM(claim_amount) / SUM(premium), 4) AS loss_ratio
FROM fact_policy
GROUP BY region;
