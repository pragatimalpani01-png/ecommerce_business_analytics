# Project description

**Title:** E-commerce Business Performance and Profitability Signals

**Business problem:** Marketplace leaders need a clear view of sales activity, delivery performance and customer experience. A sales total alone does not show whether orders reach customers when promised, whether review scores vary across delivery experiences, or where an operations team should investigate first.

**Approach:** Combine order, item, payment, customer, product, seller and review tables. Create an order-level fact table, define a consistent set of metrics, check data quality, compare performance over time, and use targeted views to flag categories and sellers that may need a closer look.

**Main deliverables:** A management dashboard, a short PDF review, an interactive service-recovery budget planner, SQL queries, reusable CSV tables and a SQLite database.

**Out-of-the-box element:** The project uses a delivery promise gap rather than only average delivery time, a category opportunity map that compares sales with service-friction signals, and a simple seller exception score. It also separates item value associated with poor service from actual financial loss. The source data does not support a true profit calculation, so the project does not label item value as profit.

**Data:** The public Brazilian E-Commerce Dataset by Olist, covering historical orders from 2016 to 2018. Synthetic tables are included for an immediate demo run. They are labeled as synthetic and are not presented as Olist results.

**Tools:** Python, pandas, Matplotlib, Plotly, SQLite, SQL and ReportLab.
