-- Monthly order activity and delivered item value.
-- Run against outputs/marketplace_analysis.db.
SELECT
    purchase_month,
    COUNT(DISTINCT order_id) AS orders,
    SUM(CASE WHEN is_delivered = 1 OR is_delivered = 'True' THEN 1 ELSE 0 END) AS delivered_orders,
    ROUND(SUM(CASE WHEN is_delivered = 1 OR is_delivered = 'True' THEN item_sales_brl ELSE 0 END), 2) AS delivered_item_value_brl,
    ROUND(AVG(CASE WHEN is_delivered = 1 OR is_delivered = 'True' THEN promise_gap_days END), 2) AS average_promise_gap_days
FROM order_fact
GROUP BY purchase_month
ORDER BY purchase_month;
