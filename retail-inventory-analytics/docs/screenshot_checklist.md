# Screenshot checklist (capture REAL runs only – do not edit or mock)

Tick each item after capturing. Save images as `report/screenshots/NN-name.png`, then paste them
into the matching placeholder in `report/project_report.docx`.

| # | What to capture | Command / place | Done |
|---|---|---|---|
| 01 | MongoDB running + connection OK (server version) | `python -m scripts.demo` step 1 | [ ] |
| 02 | Three collections with validators (`validationAction: error`) | `python -m scripts.init_db` output, or Compass → *Validation* tab | [ ] |
| 03 | Unique indexes (sku, supplier_id, movement_id) | Compass → *Indexes* tab | [ ] |
| 04 | Sample documents in each collection (BSON `Date` types visible) | Compass | [ ] |
| 05 | Seed script output (counts, "OK (all consistent)"); run it twice to show no duplicates | `python -m scripts.seed_data` | [ ] |
| 06 | CRUD demo: insert/retrieve, update, delete temp record | demo steps 3-5 | [ ] |
| 07 | MongoDB rejecting an invalid document (`WriteError code=121`) | demo step 6 | [ ] |
| 08 | Duplicate SKU rejection message | demo step 6 / UI Add product | [ ] |
| 09 | Stock IN, valid OUT, rejected OUT | demo steps 7-9 / UI Stock Operations | [ ] |
| 10 | Four aggregation outputs | demo step 10 | [ ] |
| 11 | Pipelines shown in the UI (expanders) | UI → Analytics | [ ] |
| 12 | Dashboard (metrics + category chart) | UI → Dashboard | [ ] |
| 13 | Product Management (browse/search, add, edit, delete-blocked message) | UI | [ ] |
| 14 | Supplier Management | UI | [ ] |
| 15 | pytest summary line (`passed`/`skipped` counts visible) | `python -m pytest -v` | [ ] |
