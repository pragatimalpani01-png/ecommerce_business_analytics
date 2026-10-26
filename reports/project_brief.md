# Business brief: Marketplace performance review

## The situation

An online marketplace has a large number of orders and several sellers fulfilling them. A simple sales report is not enough to show whether the marketplace is keeping its delivery promises or where poor customer experiences are more common.

## The questions

- How much item value is associated with delivered orders, and how does it change month to month?
- Where do late deliveries occur more often?
- Do review scores vary with the delivery promise gap?
- Which categories and sellers should operations examine first?
- Are customers placing another order during the observed period?

## The proposed analysis

Build a reusable order-level table from the public Olist tables, preserve item-level detail for category and seller comparisons, document each KPI, run data checks, and publish a dashboard and short business report. Include a small planning tool to estimate the staffing cost of contacting a selected share of customers whose orders were late and rated poorly.

## What the data can and cannot say

The dataset contains prices, freight, order timestamps and reviews. It does not contain all expenses or refunds, so it cannot support a proper profit calculation. The service-recovery figure is the item value associated with flagged orders, not lost revenue. Relationships between late delivery and reviews are descriptive; they do not prove that delivery alone caused a poor rating.

## What a manager could do next

Start by checking the operations behind the biggest promise gaps. Use the seller and category views to choose a small number of cases for investigation, not to rank teams or sellers without context. If service recovery is tested, compare outcomes against a similar group and track actual intervention cost, customer response and repeat orders.

## Files for review

The PDF report is `marketplace_performance_review.pdf`. The interactive dashboard and planning tool are in `outputs/`. For repeatable runs, use `python run_project.py --source demo` or replace the demo tables with the original Olist download and run `python run_project.py --source raw`.
