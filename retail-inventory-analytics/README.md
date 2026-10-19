# Retail Inventory & Stock Analytics (MongoDB + PyMongo + Streamlit)

CSE494 – Intelligent NoSQL Databases · Academic Task 2

A small-retail inventory system built on **MongoDB** (real persistence layer), **PyMongo**
(all database access), **$jsonSchema validators**, **aggregation pipelines**, a **Streamlit**
UI, and **pytest** integration tests. All data is fictional.

## 1. Project layout

```
app.py                      Streamlit UI (presentation only)
config.py                   Settings from environment variables
database/  connection.py    PyMongo client, friendly errors, transaction detection
           validators.py    $jsonSchema validators (validationAction=error, level=strict)
           indexes.py       Unique + helper indexes, initialize_database()
services/  product_service.py  supplier_service.py  stock_service.py  analytics_service.py
           validation.py (input rules) errors.py (domain exceptions) _mongo.py (error translation)
scripts/   init_db.py  seed_data.py  demo.py
tests/     test_crud.py  test_validation.py  test_stock_operations.py  test_analytics.py
report/    project_report.docx  (+ build_report.js that generates it)
docs/      screenshot_checklist.md
```

## 2. Prerequisites (Windows)

1. **Python 3.10+** – https://www.python.org/downloads/ (tick *Add python.exe to PATH*).
2. **MongoDB** – choose ONE:
   * **Local:** install *MongoDB Community Server* (https://www.mongodb.com/try/download/community)
     with "Install as a Service". Check it runs: open *Services* → `MongoDB Server` → Running.
     Optional: install *MongoDB Compass* (GUI) – useful for screenshots.
   * **Atlas (cloud):** create a free M0 cluster at https://www.mongodb.com/atlas, add a database
     user, allow your IP under *Network Access*, and copy the `mongodb+srv://...` connection string.
3. (Optional) Git, VS Code.

## 3. Setup

Open **PowerShell** in the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
```

### Connection string (environment variable `MONGODB_URI`)

```powershell
# Local MongoDB (this is also the default if you set nothing):
$env:MONGODB_URI = "mongodb://localhost:27017"

# Atlas (use YOUR credentials; never commit them):
$env:MONGODB_URI = "mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
```
`$env:` values last for the current PowerShell window only. For a permanent value use
`setx MONGODB_URI "..."` (then open a new window) or copy `.env.example` to `.env`
(`.env` is git-ignored).

Optional variables: `MONGODB_DB_NAME` (default `retail_inventory`), `MONGODB_TEST_DB_NAME`
(default `retail_inventory_test`), `CURRENCY_SYMBOL` (default `$`).

## 4. Initialise, seed, run

```powershell
python -m scripts.init_db                 # collections + validators + indexes (no data)
python -m scripts.seed_data               # 5 suppliers, 20 products, 45 movements (safe to re-run)
streamlit run app.py                      # opens http://localhost:8501
```
* `seed_data` never duplicates: it uses `$setOnInsert` upserts. `--reset --yes` drops the three
  collections and re-seeds from scratch.
* The app itself only (re)applies validators/indexes at startup; it **never inserts seed data**.

## 5. Run the tests

```powershell
python -m pytest -v
```
Integration tests use a **separate real database** (`retail_inventory_test`) that they drop/recreate.
If MongoDB is unreachable the database tests are **skipped, not passed** – read the summary line
(`N passed, M skipped`). `-rs` shows skip reasons. Tests marked `requires_transactions` only run on a
replica set / Atlas; on a standalone local mongod they are skipped.

## 6. Design notes (useful in the viva)

| Topic | Decision |
|---|---|
| Why MongoDB | Flexible documents, strong aggregation framework, `$lookup` joins when needed, schema validation without losing flexibility. |
| References | `products.supplier_id` → suppliers, `stock_movements.sku` → products. **$jsonSchema cannot enforce references**, so services check existence before writing. |
| Stock integrity | One atomic `find_one_and_update` with filter `quantity_in_stock >= needed` + `$inc`. Concurrent stock-outs cannot go negative. |
| Product + movement | Transaction when supported (replica set/Atlas). On standalone mongod: stock update first, then movement insert; if the insert fails the stock change is reversed (compensation). If even that fails a `StockConsistencyError` is raised. Success is only reported when both writes happened. |
| Opening stock | A product created with stock > 0 also gets an "Opening stock" IN movement so stock always equals its history. |
| Quantity edits | Not allowed via product update – only via stock movements. |
| Deletion rules | A product with movement history cannot be deleted (it would orphan the audit trail). A supplier that still supplies products cannot be deleted. |
| Money | Prices are stored as doubles rounded to 2 dp; values are *estimated inventory value at current selling prices*, not accounting cost. For real accounting use `Decimal128`. |
| Dates | Real BSON `Date` values (timezone-aware UTC in Python). MongoDB stores millisecond precision. |
| Consistency check | `analytics_service.stock_consistency_mismatches` is an aggregation (`$lookup` + `$reduce`) comparing each product's stock with its movement history. |

Requires MongoDB **4.2+** (`$round`, `$jsonSchema` with `anyOf`, etc.). Transactions need 4.0+ replica set.

## 7. Demonstration sequence (viva / screenshots)

Run `python -m scripts.demo --pause` (prints real output for steps 1-10) alongside the UI:

1. Connect to MongoDB – step 1 output (server version).
2. Show the three collections – step 2 (also Compass).
3. Insert and retrieve a product – step 3.
4. Update the product – step 4.
5. Delete a temporary record – step 5 (and refusal to delete a product with history).
6. MongoDB rejects invalid data – step 6 (`WriteError code=121`).
7. Stock IN – step 7 (or UI → Stock Operations).
8. Valid stock OUT – step 8.
9. Invalid stock-out rejected – step 9.
10. Aggregation pipelines – step 10 (or UI → Analytics → *Show MongoDB aggregation pipeline*).
11. Analytics in the interface – UI → Dashboard and Analytics.

Also run `python -m pytest -v` and screenshot the result. A checklist is in `docs/screenshot_checklist.md`.

## 8. Troubleshooting

* **"Cannot reach MongoDB"** – service not running / wrong `MONGODB_URI` / Atlas IP not allow-listed.
* **`Unauthorized`** – wrong Atlas username/password, or the user lacks `readWrite` on the database.
* **Transactions skipped** – expected on a standalone local mongod.
* **`ModuleNotFoundError`** – run commands from the project root with the virtualenv active.
