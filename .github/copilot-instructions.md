# Copilot Instructions for POS System

## Project Overview
- This is a modern Point-of-Sale (POS) system built with Python and Tkinter, using a modular architecture for UI, business logic, and data access.
- The main entry point is `pos_system.py`, which initializes the Tkinter app, tabs, and injects dependencies.
- All UI panels are in `modules/` and follow a pattern: `ui_sales.py` (sales, barcode, cart), `ui_management.py` (product CRUD), `ui_report.py` (reporting/stats).
- Styles are centralized in `modules/styles.py` as global variables (not a class). Import style constants directly (e.g., `from modules.styles import COLORS, FONT, FRAME_STYLES, BUTTON_STYLES`).
- Database access is via a `db` object passed to panels, using SQLite (see `modules/database.py`, `models.py`).
- Invoice/receipt printing is handled by `modules/receipt_printer.py` (uses fpdf2, win32print).

## Key Patterns & Conventions
- **UI Construction:** All widget creation must be inside methods (not at class level). Use card-like frames and style constants for a modern look.
- **Barcode Scanning:** Barcode entry auto-focuses and triggers product lookup/add-to-cart on `<Return>`. See `ui_sales.py` for the pattern.
- **Style Usage:** Never instantiate a `Styles` class. Use style constants directly. Example:
  ```python
  from modules.styles import COLORS, FONT, FRAME_STYLES, BUTTON_STYLES
  btn = tk.Button(..., **BUTTON_STYLES['primary'])
  ```
- **Database:** Always use the `db` object passed to panels. Do not create new connections in UI code.
- **Printing:** Use `ReceiptPrinter` for all invoice/receipt output. Do not print directly from UI panels.
- **Error Handling:** Use `messagebox` for user-facing errors. Do not print to console for UI errors.

## Developer Workflows
- **Run the app:**
  ```sh
  python pos_system.py
  ```
- **Dependencies:**
  - Requires: `tkinter`, `fpdf2`, `pywin32` (for Windows printing)
  - Install with:
    ```sh
    pip install fpdf2 pywin32
    ```
- **Database:**
  - Schema is auto-created if missing. See `modules/database.py` for structure.
- **UI Debugging:**
  - If UI fails to load, check for style import errors or widget creation outside methods.

## Integration Points
- **External:**
  - Barcode scanners (input as keyboard events)
  - Windows printers (via win32print)
- **Internal:**
  - All cross-panel communication is via shared `db` and style constants.

## Examples
- See `modules/ui_sales.py` for barcode-to-cart logic and modern UI patterns.
- See `modules/styles.py` for all style variables and usage.
- See `modules/receipt_printer.py` for PDF/print integration.

---

If you are unsure about a pattern or see a style/class import error, check `modules/styles.py` and follow the import pattern above.
