-- Prioritize categories where there is meaningful item value and a service signal to investigate.
-- Review scores are order-level. They are repeated onto item lines in category comparisons,
-- so use this as a screening view rather than a product-level quality score.
SELECT
    category,
    orders,
    ROUND(delivered_item_sales_brl, 2) AS delivered_item_value_brl,
    ROUND(100.0 * low_review_share, 1) AS low_review_share_pct,
    ROUND(100.0 * late_share_item_line_proxy, 1) AS late_item_line_share_pct,
    ROUND(100.0 * freight_share, 1) AS freight_share_pct
FROM category_performance
WHERE orders >= 10
ORDER BY delivered_item_sales_brl DESC;
