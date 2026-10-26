# Analyst notes: marketplace performance review

**Important: this run uses synthetic demo data, not Olist's original transactions.** The figures below confirm that the workflow runs; they are not business findings about Olist.

## What the run covers

The analysis processed 1,800 orders, of which 1,713 are marked delivered. Item value is tracked separately from freight. The source does not include enough cost information to calculate actual profit or margin.

## Scorecard

| Measure | Result |
|---|---:|
| Orders | 1,800 |
| Delivered orders | 1,713 |
| Delivered order share | 95.2% |
| Canceled orders | 40 |
| Cancellation rate | 2.2% |
| Delivered item value | R$ 367,985 |
| Delivered freight value | R$ 65,624 |
| Average item value per delivered order | R$ 215 |
| On-time delivery rate | 76.5% |
| Median delivery time | 11.0 days |
| Average review score | 3.99 / 5 |
| Review coverage among delivered orders | 84.5% |
| Repeat-customer share | 49.0% |
| Item value in late, low-rated orders | R$ 21,691 |

## How to read the analysis

### 1. Follow the delivery promise, not only average delivery time
The promise gap is the actual delivery date minus the estimated delivery date. A positive value means the order arrived late. Median delivery time can look reasonable even while a meaningful group of customers receive orders after the promised date, so the distribution and the share arriving late deserve separate attention.

### 2. Prioritize categories where sales and poor experiences overlap
The category opportunity chart puts delivered item value beside low-review share and uses late delivery as another signal. It helps narrow the first set of categories to investigate. Reviews are attached to the order, not to individual product lines, so a review for a multi-item order is associated with each category in that order. It does not prove that shipping delays caused the lower ratings, and a category with few reviews should not be treated as a reliable outlier.

### 3. Use seller rankings as a queue for investigation
The seller service-friction index is a simple screening score: 55% late share plus 45% low-review share, scaled to 0-100. It is not an official performance measure. Review eligibility, order count, product mix and destination mix before taking action on any seller.

### 4. Separate value at risk from a financial loss
The report counts item value in orders that were both late and rated 1 or 2. That is the value of orders associated with a poor service outcome, not lost revenue and not an estimate of refunds. The data does not show whether customers returned items or stopped buying.

### 5. Look at customer cohorts without overstating retention
Cohort activity shows the share of customers in each first-order month who placed an order again in a later month. It is a practical repeat-order view, but the newest cohorts have less time to return and the historical window ends in 2018.

## Business actions to test

1. Start with the categories that combine material sales with high late-delivery and low-review rates. Check stock location, carrier hand-offs, estimated delivery promises and product handling before changing assortment or pricing.
2. Give the operations team a weekly seller exception list, but suppress sellers with small samples. Ask for a root-cause explanation before making commercial decisions.
3. Review the worst service cases alongside customer comments. Use those cases to define a small recovery test, such as proactive delay messaging or a targeted service credit, and measure whether ratings or repeat orders improve.
4. Keep item sales, freight and cost of goods separate. Add real cost and refund data before describing any measure as profit, margin or recoverable revenue.

## Data limits

- The original public dataset covers historical transactions, not current marketplace performance.
- It does not provide a complete cost-of-goods, returns, advertising, tax, discount or operating-expense ledger. Actual profit cannot be calculated from these tables alone.
- Review data is self-selected. Buyers who leave a review may not represent all customers.
- The relationships shown are descriptive. They should not be presented as proof of cause and effect.
- Category reviews are order-level reviews carried onto item lines. This is a useful screening proxy, not a product-level rating measure.
- Category and seller comparisons may be affected by sample size, price, product mix and customer location.

## Files created by the run

- `outputs/dashboard.html`: standalone interactive dashboard.
- `outputs/service_recovery_planner.html`: interactive contact-coverage and cost planner.
- `outputs/marketplace_analysis.db`: SQLite database for the SQL examples.
- `outputs/metrics.json`: headline metrics for the run.
- `outputs/tables/order_fact.csv`: one row per order with derived measures.
- `outputs/tables/item_fact.csv`: item lines with category and order attributes.
- `outputs/tables/category_performance.csv`: category comparison table.
- `outputs/tables/seller_service_scorecard.csv`: seller screening scorecard.
- `outputs/tables/customer_cohort_activity.csv`: repeat-order activity by cohort.
- `outputs/tables/monthly_performance.csv`: monthly activity and value summary.
- `outputs/tables/payment_method_summary.csv`: payment-method summary.
- `outputs/tables/data_quality_checks.csv`: checks to review before interpreting metrics.
- `visualizations/`: static charts used in this report.

## Data source and credit

Olist, & Sionek, A. (2018). Brazilian E-Commerce Public Dataset by Olist. Kaggle. https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce. The published dataset is licensed under CC BY-NC-SA 4.0; follow the source terms and attribution requirements when sharing adapted material.
