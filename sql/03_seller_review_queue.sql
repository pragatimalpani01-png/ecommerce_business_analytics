-- This is a screening queue, not an official seller ranking.
-- Check the sample size and destination/product mix before contacting a seller.
SELECT
    seller_id,
    orders,
    ROUND(delivered_item_value_brl, 2) AS delivered_item_value_brl,
    ROUND(service_friction_index, 1) AS service_friction_index,
    ROUND(100.0 * late_share, 1) AS late_share_pct,
    ROUND(100.0 * low_review_share, 1) AS low_review_share_pct,
    rank_eligible
FROM seller_service_scorecard
WHERE rank_eligible = 1 OR rank_eligible = 'True'
ORDER BY service_friction_index DESC
LIMIT 15;
