# Data dictionary

The original dataset is divided into related CSV files. The demo tables use the same core column names but contain synthetic values.

| Table | Row level | Key fields | Used for |
|---|---|---|---|
| `olist_orders_dataset.csv` | One row per order | `order_id`, `customer_id`, order status and timestamps | Order activity, delivery time and promise gap |
| `olist_order_items_dataset.csv` | One row per product line in an order | `order_id`, `order_item_id`, `product_id`, `seller_id`, `price`, `freight_value` | Item value, freight and seller/category analysis |
| `olist_customers_dataset.csv` | One row per order-specific customer record | `customer_id`, `customer_unique_id`, `customer_state` | Customer identity, repeat orders and geography |
| `olist_products_dataset.csv` | One row per product | `product_id`, `product_category_name` | Category mapping |
| `olist_order_payments_dataset.csv` | One row per payment record | `order_id`, `payment_type`, `payment_value` | Payment-method summary and reconciliation check |
| `olist_order_reviews_dataset.csv` | One row per review record | `order_id`, `review_score` | Customer feedback analysis |
| `olist_sellers_dataset.csv` | One row per seller | `seller_id`, seller city and state | Seller service scorecard |
| `product_category_name_translation.csv` | One row per category translation | `product_category_name`, `product_category_name_english` | Readable category labels |

The geolocation table is not needed for the current analysis and is not required by the download script. It can be added later for distance or map-based analysis, subject to the source terms.

## Derived tables

- `order_fact.csv`: one row per order, combining order, item, payment, customer and review measures.
- `item_fact.csv`: item lines joined to product categories and order service measures.
- `category_performance.csv`: item value, freight burden, low-review share and delivery flags by category.
- `seller_service_scorecard.csv`: seller volume, item value, late share, low-review share and the service-friction index.
- `customer_cohort_activity.csv`: customer order activity by first-order month and elapsed month.
- `data_quality_checks.csv`: checks for common join and timestamp issues.
