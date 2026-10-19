// Generates report/project_report.docx.   Run from the project root:
//   NODE_PATH=$(npm root -g) node report/build_report.js
// Code excerpts are read from the real source files so the report always matches the code.
// RESULT sections contain clearly marked PLACEHOLDERS: paste only genuine output/screenshots.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  BorderStyle, AlignmentType, HeadingLevel, LevelFormat, Footer, PageNumber, PageBreak,
  TableOfContents,
} = require("docx");

const ROOT = path.join(__dirname, "..");
const FONT = "Calibri";
const YEL = { type: ShadingType.CLEAR, fill: "FFF200", color: "auto" }; // placeholder highlight
const CODE_FONT = "Consolas";
const W = 9026; // A4 content width (DXA) with 1-inch margins

// ---------- helpers ----------
const t = (text, o = {}) => new TextRun({ text, font: FONT, ...o });
const p = (text, o = {}) =>
  new Paragraph({ spacing: { after: 120, line: 276 }, ...o.para,
    children: Array.isArray(text) ? text : [t(text, o.run)] });
const h1 = (s) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [t(s)] });
const h2 = (s) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [t(s)] });
const h3 = (s) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [t(s)] });
const bullets = (items) => items.map((x) => new Paragraph({
  numbering: { reference: "bul", level: 0 }, spacing: { after: 60 },
  children: Array.isArray(x) ? x : [t(x)] }));
const b = (s) => t(s, { bold: true });

// Yellow-highlighted placeholder so it can never be mistaken for a real result.
const ph = (s) => new Paragraph({
  spacing: { before: 60, after: 160 },
  border: { left: { style: BorderStyle.SINGLE, size: 18, color: "BF9000", space: 6 } },
  children: [t("[PLACEHOLDER] " + s, { shading: YEL, italics: true })],
});
const shot = (n, s) => new Paragraph({
  spacing: { before: 80, after: 200 }, alignment: AlignmentType.CENTER,
  border: { top: { style: BorderStyle.DASHED, size: 6, color: "999999", space: 10 },
            bottom: { style: BorderStyle.DASHED, size: 6, color: "999999", space: 10 } },
  children: [t(`[SCREENSHOT ${n} - insert real capture: ${s}]`, { shading: YEL })],
});

function code(text) {
  const lines = text.replace(/\t/g, "    ").split("\n");
  return lines.map((ln, i) => new Paragraph({
    spacing: { after: 0, line: 240 },
    shading: { type: ShadingType.CLEAR, fill: "F3F3F3" },
    keepLines: true,
    children: [new TextRun({ text: ln === "" ? " " : ln, font: CODE_FONT, size: 15 })],
  })).concat([new Paragraph({ spacing: { after: 120 }, children: [] })]);
}
// Pull a block of a real source file between two marker strings (inclusive of start).
function excerpt(file, start, end) {
  const src = fs.readFileSync(path.join(ROOT, file), "utf8");
  const a = src.indexOf(start);
  if (a < 0) throw new Error(`marker not found in ${file}: ${start}`);
  const bIdx = end ? src.indexOf(end, a + start.length) : src.length;
  if (bIdx < 0) throw new Error(`end marker not found in ${file}: ${end}`);
  const lines = src.slice(a, bIdx).split("\n");
  while (lines.length && (lines[lines.length - 1].trim() === "" || lines[lines.length - 1].startsWith("# -"))) lines.pop();
  return lines.join("\n");
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "BBBBBB" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(headers, rows, widths) {
  const total = widths.reduce((x, y) => x + y, 0);
  const cell = (txt, w, head) => new TableCell({
    borders, width: { size: w, type: WidthType.DXA },
    shading: head ? { type: ShadingType.CLEAR, fill: "1F3864" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [t(String(txt), head
      ? { bold: true, color: "FFFFFF", size: 20 } : { size: 20 })] })],
  });
  return [new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, widths[i], true)) }),
      ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, widths[i], false)) }))],
  }), new Paragraph({ spacing: { after: 160 }, children: [] })];
}

// ---------- cover ----------
const centered = (text, size, o = {}) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: o.after ?? 200 },
  children: [t(text, { size, bold: o.bold, color: o.color })] });
const cover = [
  new Paragraph({ spacing: { before: 2200 }, children: [] }),
  centered("PROJECT REPORT", 24, { color: "7F7F7F", after: 300 }),
  centered("Retail Inventory & Stock Analytics", 56, { bold: true, color: "1F3864", after: 120 }),
  centered("using MongoDB, PyMongo and Aggregation Pipelines", 28, { color: "404040", after: 900 }),
  centered("CSE494 \u2013 Intelligent NoSQL Databases", 28, { bold: true, after: 100 }),
  centered("Academic Task 2", 24, { after: 900 }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 140 },
    children: [t("Student Name: ", { size: 26, bold: true }), t("[Student Name]", { size: 26, shading: YEL })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 140 },
    children: [t("Roll Number: ", { size: 26, bold: true }), t("[Roll Number]", { size: 26, shading: YEL })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 140 },
    children: [t("Submission Date: ", { size: 26, bold: true }), t("[DD Month YYYY]", { size: 26, shading: YEL })] }),
  new Paragraph({ children: [new PageBreak()] }),
];

// ---------- 1. Introduction ----------
const intro = [
  h1("1. Introduction"),
  h2("1.1 Background and motivation"),
  p("Small retail shops typically track stock in notebooks or spreadsheets. Both make it hard to answer simple but " +
    "important questions: Which products are about to run out? How much money is tied up in each product category? " +
    "Which supplier holds most of the stock? How did stock change over time? Answering these questions reliably needs a " +
    "database that stores current stock together with a trustworthy history of every change, and that can summarise " +
    "that data on demand."),
  p("Inventory data is also naturally document-shaped: a product is a self-contained record with a handful of " +
    "attributes, while stock movements form a growing event log. This makes it a good fit for a document database such as MongoDB."),
  h2("1.2 Problem statement"),
  p("Design and implement an executable Retail Inventory & Stock Analytics application that manages products, " +
    "suppliers, current stock and stock-movement history, prevents invalid or inconsistent data (for example negative stock), " +
    "and provides analytics for inventory valuation, low-stock detection and stock movement by category, using MongoDB as " +
    "the real persistence layer and PyMongo as the only database driver."),
  h2("1.3 Objectives"),
  ...bullets([
    "Design suitable MongoDB document structures for products, suppliers and stock movements.",
    "Enforce data quality with MongoDB $jsonSchema validators (action: error) and Python-side business rules.",
    "Implement Create, Read, Update and Delete operations through PyMongo with meaningful error handling.",
    "Implement stock IN, OUT and ADJUSTMENT operations that can never make stock negative, even under concurrency.",
    "Implement four aggregation pipelines that compute analytics inside MongoDB.",
    "Provide a repeatable seed script, automated pytest tests, a Streamlit interface and clear documentation.",
  ]),
  h2("1.4 Scope"),
  p("In scope: a single-store inventory with three collections (products, suppliers, stock_movements), validation, CRUD, " +
    "stock operations, four analytics pipelines, a Streamlit UI and automated tests. All demonstration data is fictional."),
  p("Out of scope: user authentication and roles, purchase-order workflows, multi-warehouse stock, accounting cost " +
    "methods (FIFO/average cost) and taxes. Inventory values reported are estimated values at current selling prices, " +
    "not accounting cost values."),
];

// ---------- 2. Methods ----------
const methods = [
  h1("2. Methods Implemented"),
  h2("2.1 Technologies used"),
  ...table(["Technology", "Role in the project"], [
    ["MongoDB", "Document database; the only persistence layer (database: retail_inventory)."],
    ["PyMongo", "The official Python driver; all reads/writes/aggregations go through it."],
    ["Python 3", "Application and business logic (services package)."],
    ["$jsonSchema validators", "Database-level validation with validationAction = error."],
    ["Aggregation framework", "All analytics computed inside MongoDB ($match, $group, $lookup, ...)."],
    ["Streamlit", "Simple web interface (presentation only)."],
    ["pytest", "Automated tests against a separate real MongoDB test database."],
  ], [2600, 6426]),
  h2("2.2 System architecture"),
  p("The project separates presentation, business logic and database access into layers, so each can be explained and tested independently."),
  ...table(["Layer", "Files", "Responsibility"], [
    ["Presentation", "app.py", "Streamlit pages; displays data and shows error messages. No business rules."],
    ["Services", "services/product_service.py, supplier_service.py, stock_service.py, analytics_service.py, validation.py",
     "Business rules, referential checks, atomic stock updates, aggregation pipelines."],
    ["Database", "database/connection.py, validators.py, indexes.py", "Connection handling, $jsonSchema validators, indexes."],
    ["Scripts", "scripts/init_db.py, seed_data.py, demo.py", "Schema initialisation, repeatable seeding, scripted demonstration."],
    ["Tests", "tests/", "Integration tests against a real MongoDB test database."],
  ], [1500, 3500, 4026]),
  p("The connection string is read from the MONGODB_URI environment variable; no credentials are stored in the source code."),

  h2("2.3 Why MongoDB was selected"),
  ...bullets([
    [b("Natural document fit. "), t("A product is a self-contained record; the whole record is read or updated in one operation.")],
    [b("Flexible yet controllable schema. "), t("Documents can evolve, while $jsonSchema validators still enforce types, ranges and required fields where it matters.")],
    [b("Atomic single-document updates. "), t("A conditional $inc on one product document is atomic, which is the key to preventing negative stock under concurrency.")],
    [b("Powerful aggregation framework. "), t("Grouping, joining ($lookup) and conditional sums are computed by the database server, not by Python loops.")],
    [b("Easy scaling of the event log. "), t("The ever-growing stock_movements history is a separate collection and is not constrained by the 16 MB document limit.")],
  ]),

  h2("2.4 MongoDB database and document design"),
  p("Database: retail_inventory. It contains exactly three core collections. Each exists for a distinct reason:"),
  ...bullets([
    [b("products"), t(" \u2013 the current state of every sellable item, including quantity_in_stock. Keeping the current quantity here makes the most common question (\"how many do we have?\") a single fast read instead of a calculation over history.")],
    [b("suppliers"), t(" \u2013 supplier details stored once and referenced by many products, so contact details are never duplicated or left inconsistent.")],
    [b("stock_movements"), t(" \u2013 an append-only audit trail of every IN, OUT and ADJUSTMENT. It grows without bound, so it is kept outside the product document, and it supports analytics by category and date.")],
  ]),
  h3("products"),
  ...table(["Field", "Type", "Rule"], [
    ["sku", "string", "Required, unique index (uq_sku), non-blank"],
    ["name, category", "string", "Required, non-blank"],
    ["supplier_id", "string", "Required; must reference an existing supplier (checked in Python)"],
    ["unit_price", "number", "Required, >= 0"],
    ["quantity_in_stock", "integer", "Required, >= 0"],
    ["reorder_level", "integer", "Required, >= 0"],
    ["created_at, updated_at", "BSON Date", "Required real Date values (not strings)"],
  ], [2400, 1700, 4926]),
  h3("suppliers"),
  ...table(["Field", "Type", "Rule"], [
    ["supplier_id", "string", "Required, unique index (uq_supplier_id), non-blank"],
    ["name", "string", "Required, non-blank"],
    ["contact_person, phone, email, city", "string", "Optional; email and phone format checked in Python"],
  ], [2900, 1500, 4626]),
  h3("stock_movements"),
  ...table(["Field", "Type", "Rule"], [
    ["movement_id", "string", "Required, unique index (uq_movement_id)"],
    ["sku", "string", "Required; must reference an existing product (checked in Python)"],
    ["movement_type", "enum", "IN, OUT or ADJUSTMENT"],
    ["quantity", "integer", "Non-zero. IN/OUT must be positive; ADJUSTMENT may be signed"],
    ["reason", "string", "Required, non-blank"],
    ["movement_date", "BSON Date", "Required"],
  ], [2400, 1700, 4926]),

  h2("2.5 Collection relationships"),
  p("Relationships are modelled with references rather than embedding, because suppliers change independently of products and movements are unbounded."),
  ...table(["Relationship", "Cardinality", "Implemented by"], [
    ["suppliers \u2192 products", "One supplier supplies many products", "products.supplier_id = suppliers.supplier_id"],
    ["products \u2192 stock_movements", "One product has many movements", "stock_movements.sku = products.sku"],
  ], [2600, 3000, 3426]),
  p("Important: MongoDB's $jsonSchema validator checks a single document and cannot verify that a referenced document exists in another collection. " +
    "These referential rules are therefore enforced in the Python service layer before writing."),

  h2("2.6 Validation rules"),
  h3("Database-level (MongoDB $jsonSchema, validationAction = error, validationLevel = strict)"),
  p("Invalid documents are rejected by the server itself, even if they bypass the application. Excerpt from database/validators.py (products):"),
  ...code(excerpt("database/validators.py", "PRODUCTS_SCHEMA = {", "SUPPLIERS_SCHEMA = {")),
  p("The movement schema uses anyOf to express the sign rule (JSON Schema in MongoDB has no if/then):"),
  ...code(excerpt("database/validators.py", "        # IN / OUT must be positive", "SCHEMAS = {")),
  h3("Application-level (Python business rules)"),
  ...bullets([
    "Duplicate identifiers: caught from the unique indexes (DuplicateKeyError) and reported as a clear message.",
    "Supplier must exist before assigning it to a product; product must exist before recording a movement.",
    "Sufficient stock before stock-out (atomic conditional update, see 2.8).",
    "Email and phone format, non-negative price/stock, whole-number quantities, non-blank text.",
    "Product with movement history cannot be deleted; supplier with products cannot be deleted.",
  ]),

  h2("2.7 CRUD operations"),
  ...table(["Operation", "Service function", "PyMongo call"], [
    ["Create product / supplier", "create_product, create_supplier", "insert_one"],
    ["Read / search / filter", "get_product, list_products, list_suppliers", "find_one, find (regex, $expr), distinct"],
    ["Update", "update_product, update_supplier", "update_one with $set"],
    ["Delete (guarded)", "delete_product, delete_supplier", "count_documents check, then delete_one"],
    ["Stock movements", "stock_in, stock_out, adjust_stock", "find_one_and_update ($inc) + insert_one"],
  ], [2500, 3400, 3126]),
  p("Stock quantity is deliberately not editable through product update: it changes only via stock movements, so quantity and history can never diverge. " +
    "Products with movement history cannot be deleted because deleting them would orphan the audit trail and make past stock levels impossible to explain."),

  h2("2.8 PyMongo implementation: atomic stock operations"),
  p("The decrease of stock is performed by one atomic conditional update. MongoDB evaluates the filter and applies $inc as a single operation, " +
    "so two simultaneous stock-outs can never both succeed when only one unit is available:"),
  ...code(excerpt("services/stock_service.py", "def _conditional_update", "def _record")),
  p("Product update and movement insert are made all-or-nothing as follows:"),
  ...bullets([
    [b("Transactions available (replica set / Atlas): "), t("both writes run inside one multi-document transaction (session.with_transaction).")],
    [b("Standalone mongod (no transactions): "), t("the stock update is applied first, then the movement is inserted; if the insert fails the stock change is reversed by an inverse $inc (compensation). If the reversal also fails a StockConsistencyError naming the SKU is raised. The application never reports success unless both writes happened.")],
  ]),
  p("Connection handling (database/connection.py) verifies connectivity with a ping, produces helpful messages (credentials redacted) and closes the client on exit."),

  h2("2.9 Aggregation pipelines"),
  p("All four pipelines run inside MongoDB through collection.aggregate(). Python only displays the returned documents."),
  ...table(["#", "Pipeline", "Collection", "Key operators", "What it reveals"], [
    ["1", "Low-stock products", "products", "$match ($expr), $project, $sort", "Which products need reordering now (qty <= reorder level)."],
    ["2", "Inventory value by category", "products", "$group, $sum, $multiply, $addToSet, $project, $sort",
     "Where money is tied up: units, estimated value and distinct products per category."],
    ["3", "Stock movement by category", "stock_movements", "$lookup, $unwind, $group, $cond, $sum, $sort",
     "Which categories are busiest and how much is received (IN), issued (OUT) and adjusted."],
    ["4", "Supplier inventory summary", "products", "$lookup, $unwind, $group, $multiply, $sort",
     "How much stock and value depend on each supplier."],
  ], [450, 1700, 1650, 2500, 2726]),
  p("Estimated inventory value = quantity_in_stock \u00D7 unit_price, i.e. value at current selling prices, not accounting cost value."),
  h3("Pipeline 1 \u2013 Low-stock products"),
  ...code(excerpt("services/analytics_service.py", "LOW_STOCK_PIPELINE = [", "# Pipeline 2 -")),
  h3("Pipeline 2 \u2013 Inventory value by category"),
  ...code(excerpt("services/analytics_service.py", "INVENTORY_BY_CATEGORY_PIPELINE = [", "# Pipeline 3 -")),
  h3("Pipeline 3 \u2013 Stock movement by category"),
  ...code(excerpt("services/analytics_service.py", "MOVEMENT_BY_CATEGORY_PIPELINE = [", "# Pipeline 4 -")),
  h3("Pipeline 4 \u2013 Supplier inventory summary"),
  ...code(excerpt("services/analytics_service.py", "SUPPLIER_SUMMARY_PIPELINE = [", "# Dashboard totals")),
];

// ---------- 3. Results ----------
const results = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("3. Results"),
  p([t("Status of this chapter: ", { bold: true }),
     t("every result below is a placeholder to be replaced with genuine output from your own run. Do not paste anything that was not actually produced by the program.")]),
  h2("3.1 Connection and collection creation"),
  p("Commands: python -m scripts.init_db and python -m scripts.demo (steps 1-2)."),
  ph("Paste the real console output showing the MongoDB server version, the three collections and validationAction = error."),
  shot(1, "init_db / demo step 1-2 output"),
  shot(2, "MongoDB Compass: collections, Validation tab, Indexes tab (unique sku, supplier_id, movement_id)"),
  h2("3.2 Sample records"),
  p("Command: python -m scripts.seed_data (run twice to demonstrate that no duplicates are created)."),
  ph("Paste the seed output (document counts and the stock-vs-history consistency line) for the first AND the second run."),
  ph("Insert one real sample document from each collection (copy from Compass or the demo output)."),
  shot(3, "seed script output, first and second run"),
  shot(4, "sample documents with BSON Date fields in Compass"),
  h2("3.3 CRUD outputs"),
  p("Command: python -m scripts.demo (steps 3-5): insert and retrieve a temporary product, update it, delete it, and the refusal to delete a product that has movement history."),
  ph("Paste the real output of demo steps 3, 4 and 5."),
  shot(5, "CRUD demonstration output"),
  h2("3.4 Validation test results"),
  p("MongoDB's own rejection of an invalid document (demo step 6) and the automated tests."),
  ph("Paste the real WriteError (code 121) output from demo step 6, and the duplicate-SKU message."),
  ph("Paste the real pytest summary line, e.g. 'N passed, M skipped'. If any tests were skipped, state why (for example, transaction tests skip on a standalone mongod)."),
  ...table(["Test file", "Covers", "Result (fill in after running)"], [
    ["tests/test_validation.py", "Python validators; MongoDB $jsonSchema rejection; duplicate SKU; unique indexes", "[PLACEHOLDER]"],
    ["tests/test_crud.py", "Connection; product and supplier CRUD; referential checks; delete rules", "[PLACEHOLDER]"],
    ["tests/test_stock_operations.py", "IN, OUT, insufficient stock, adjustments, concurrency, compensation, consistency", "[PLACEHOLDER]"],
    ["tests/test_analytics.py", "Four pipelines against hand-calculated values; dashboard; seed idempotency", "[PLACEHOLDER]"],
  ], [2700, 4326, 2000]),
  shot(6, "MongoDB rejecting an invalid document (WriteError 121)"),
  shot(7, "pytest -v summary"),
  h2("3.5 Stock operation results"),
  ph("Paste the real output of demo steps 7, 8 and 9 (stock IN, valid OUT, rejected OUT with 'Stock unchanged')."),
  shot(8, "stock IN / OUT / rejected OUT in the Streamlit Stock Operations page"),
  h2("3.6 Aggregation outputs"),
  ph("Pipeline 1 output (low-stock products) \u2013 paste the real table."),
  ph("Pipeline 2 output (inventory value by category) \u2013 paste the real table."),
  ph("Pipeline 3 output (stock movement by category) \u2013 paste the real table."),
  ph("Pipeline 4 output (supplier inventory summary) \u2013 paste the real table."),
  shot(9, "demo step 10 aggregation outputs"),
  h2("3.7 Interpretation of analytics"),
  p("Use your real numbers to complete the interpretation. The guide below explains what each pipeline is designed to reveal; add your actual observations in the placeholders."),
  ...bullets([
    [b("Low-stock report: "), t("lists every product at or below its reorder level, lowest stock first, so purchasing can act on the most urgent items. A zero-stock product indicates lost sales risk.")],
    [b("Inventory value by category: "), t("shows which categories hold the most estimated value at selling prices. A category with large value but few units is a high-priced line; the opposite indicates cheap, high-volume goods.")],
    [b("Movement by category: "), t("compares received (IN) with issued (OUT) quantities. OUT much greater than IN means the category is being depleted; large negative adjustments point to damage or loss that deserves investigation.")],
    [b("Supplier summary: "), t("shows how concentrated stock value is across suppliers; heavy dependence on one supplier is a supply-chain risk.")],
  ]),
  ph("Write 3-5 sentences interpreting YOUR actual output (which category is highest, which products are low, which supplier dominates)."),
  h2("3.8 Application screenshots"),
  shot(10, "Streamlit Dashboard"),
  shot(11, "Product Management (search/filter, add, edit, delete-blocked message)"),
  shot(12, "Supplier Management"),
  shot(13, "Analytics page with pipeline expanders"),
];

// ---------- 4/5 ----------
const conclusion = [
  h1("4. Conclusion"),
  p("The project implements a Retail Inventory & Stock Analytics application whose design uses MongoDB as the real persistence layer " +
    "and PyMongo for every database operation. Three collections model current state (products), reference data (suppliers) and an " +
    "append-only audit trail (stock_movements). Data quality is protected at two levels: $jsonSchema validators that make the database " +
    "itself reject invalid documents, and Python business rules for rules that a single-document schema cannot express, notably references between collections."),
  p("Stock integrity is protected by an atomic conditional update that prevents negative stock even under concurrent requests, combined with a " +
    "transaction (or, on a standalone server, a documented compensation strategy) so that stock and history are never reported as updated unless both writes succeed. " +
    "Four aggregation pipelines compute low-stock lists, inventory value, movement summaries and supplier summaries inside the database."),
  ph("State the genuine outcome of your test run (for example: 'all N executed tests passed; M tests were skipped because ...') and any limitations you observed."),
  p("Possible future work: user authentication, purchase orders, Decimal128 prices and cost-based valuation, time-series reporting of movements, and alerts for low stock."),
  h1("5. References"),
  ...bullets([
    "MongoDB Documentation \u2013 MongoDB Manual. https://www.mongodb.com/docs/manual/",
    "MongoDB Documentation \u2013 Schema Validation. https://www.mongodb.com/docs/manual/core/schema-validation/",
    "MongoDB Documentation \u2013 Aggregation. https://www.mongodb.com/docs/manual/aggregation/",
    "MongoDB Documentation \u2013 Transactions. https://www.mongodb.com/docs/manual/core/transactions/",
    "MongoDB Documentation \u2013 $lookup (aggregation stage). https://www.mongodb.com/docs/manual/reference/operator/aggregation/lookup/",
    "PyMongo Documentation. https://pymongo.readthedocs.io/en/stable/",
  ]),
];

// ---------- document ----------
const doc = new Document({
  creator: "Student", title: "Retail Inventory & Stock Analytics",
  features: { updateFields: true }, // Word offers to refresh the Table of Contents on open
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 34, bold: true, font: FONT, color: "1F3864" },
        paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: FONT, color: "2F5496" },
        paragraph: { spacing: { before: 260, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: FONT, color: "404040" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [
    { properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
      children: cover },
    { properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [t("Retail Inventory & Stock Analytics \u2013 Page ", { size: 18, color: "7F7F7F" }),
          new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: "7F7F7F" })] })] }) },
      children: [
        new Paragraph({ children: [t("Table of Contents", { size: 34, bold: true, color: "1F3864" })], spacing: { after: 200 } }),
        new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" }),
        new Paragraph({ children: [new PageBreak()] }),
        ...intro, ...methods, ...results, ...conclusion,
      ] },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  const out = path.join(__dirname, "project_report.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote", out, buf.length, "bytes");
});
