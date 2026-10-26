# Methodology and metric definitions

## Workflow

1. Read the source CSV files without modifying them.
2. Check key fields and parse order timestamps.
3. Join items to products and product-category translations.
4. Aggregate item prices and freight to one row per order.
5. Aggregate payment values and review scores separately.
6. Join customer identity and delivery timestamps to the order-level table.
7. Calculate service, customer and commercial measures.
8. Save clean output tables, static charts, an interactive dashboard and a report.

The program supports two inputs. The included `data/demo/` tables are synthetic and let the project run immediately. The `data/raw/` tables are the original public files downloaded from Kaggle. Use `--source raw` to ensure that a run uses the original files.

## Measures

| Measure | Definition | Important note |
|---|---|---|
| Item sales value | Sum of item `price` values across recorded order lines | Includes lines on non-delivered orders; does not include freight and is not net revenue. |
| Delivered item value | Item `price` on orders marked delivered | Excludes freight and does not subtract refunds, costs or other expenses. |
| Delivered item value | Item value on orders marked delivered | Does not subtract refunds, cost of goods, discounts or operating expenses. |
| Freight value | Sum of `freight_value` | Freight charged in the source data; not necessarily the actual carrier cost. |
| Average item value per delivered order | Delivered item value divided by delivered order count | Uses item prices only, not freight. |
| Delivery time | Customer delivery timestamp minus purchase timestamp | Calculated only where both timestamps are available. |
| Promise gap | Customer delivery timestamp minus estimated delivery timestamp | Positive means late; zero or negative means on time or early. |
| On-time delivery rate | Delivered orders with a non-positive promise gap divided by delivered orders with a known gap | Orders with missing dates are excluded from the denominator. |
| Low-review share | Share of reviewed delivered orders with a score of 1 or 2 | Review data is self-selected. |
| Repeat-customer share | Unique customer identities with more than one observed order, divided by identities with at least one order | This describes the observed period, not a forecast of lifetime value. |
| Item value in late, low-rated orders | Item value on delivered orders that are late and have a review score of 1 or 2 | A flag for service follow-up, not lost revenue or an estimate of saved sales. |
| Service-friction index | 55% times seller late-line share plus 45% times seller low-review share, multiplied by 100 | A screening score, not an official seller KPI. Seller reviews are attached to order lines. |
| Category low-review share | Low-review scores carried from each order onto the order's item lines | Multi-item orders can associate the same review with more than one category. Do not describe this as a product-specific rating. |

## Data quality checks

The output includes checks for duplicate order identifiers, item rows without matching orders, orders without item rows, missing delivery timestamps on delivered orders, missing estimated dates, reviews without matching orders, multiple review rows per order and the gap between payment totals and item-plus-freight totals.

A check does not automatically mean the source is wrong. For example, a canceled or unavailable order may legitimately have no item line. Review the result and the order context before changing or excluding data.

## Questions to investigate with the original data

- Does the late-delivery share vary by purchase month, customer state, seller or product category?
- Do lower review scores become more common as the promise gap grows?
- Which categories have both material item value and service-friction signals?
- Are seller-level differences still visible after filtering out sellers with low order counts?
- Which customer cohorts have enough time in the dataset to be compared fairly?
- What extra fields would be needed to calculate contribution margin or an actual service-recovery return?

## Limits

The source has historical transactions from 2016-2018. It is not a current market read. Several important financial fields, including cost of goods, returns, refunds, discounts, marketing and operating expenses, are not available in these tables. The analysis is descriptive and should not be used to claim that one observed pattern caused another.
