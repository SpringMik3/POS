import sqlite3
from pathlib import Path

from modules.app_paths import configure_app_logging, get_database_path
from modules.app_logger import get_logger
from modules.backup_service import BackupService


logger = get_logger(__name__)

class Database:
    def __init__(self, db_name=None):
        configure_app_logging()
        self.db_path = self._resolve_database_path(db_name)
        logger.info("Using database path: %s", self.db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self.cursor = self.conn.cursor()
        self._had_existing_schema = self._has_existing_schema()
        try:
            self.init_database()
        except Exception:
            logger.exception("Database initialization or migration failed: %s", self.db_path)
            raise

    def _resolve_database_path(self, db_name):
        if db_name is None:
            return get_database_path()

        db_path = Path(db_name)
        if db_path.is_absolute():
            return db_path

        return get_database_path(db_path.name)

    def _has_existing_schema(self):
        self.cursor.execute(
            '''
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table'
              AND name IN ('products', 'transactions', 'transaction_items')
            '''
        )
        return self.cursor.fetchone()[0] > 0

    def init_database(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                barcode TEXT UNIQUE,
                price REAL NOT NULL,
                stock INTEGER NOT NULL,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subtotal_amount REAL DEFAULT 0,
                discount_percent REAL DEFAULT 0,
                discount_amount REAL DEFAULT 0,
                total_amount REAL NOT NULL,
                payment_method TEXT,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transaction_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER,
                product_id INTEGER,
                product_name TEXT,
                quantity INTEGER,
                price REAL,
                subtotal REAL,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        self._ensure_inventory_movements_table()
        self._migrate_transactions_discount_columns()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS payment_settings (
            id INTEGER PRIMARY KEY CHECK(id=1), bank TEXT, account TEXT, name TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS delivery_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, items TEXT NOT NULL,
            subtotal REAL NOT NULL, discount REAL NOT NULL, total REAL NOT NULL,
            fee REAL NOT NULL DEFAULT 0, recipient TEXT NOT NULL, phone TEXT NOT NULL,
            address TEXT NOT NULL, carrier TEXT, tracking TEXT, note TEXT,
            status TEXT NOT NULL DEFAULT 'Chờ giao', transaction_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        self.conn.commit()

        from modules.customer_returns_schema import migrate
        if self._had_existing_schema and 'refund_of' not in {r[1] for r in self.conn.execute('PRAGMA table_info(transactions)')}:
            BackupService(self.db_path).backup_database(reason='before_customer_returns')
        migrate(self.conn)

    def _ensure_inventory_movements_table(self):
        self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='inventory_movements'"
        )
        table_exists = self.cursor.fetchone() is not None

        if not table_exists and self._had_existing_schema:
            try:
                backup_path = BackupService(self.db_path).backup_database(reason="before_inventory_migration")
                logger.info("Pre-inventory-migration backup created: %s", backup_path)
            except Exception:
                logger.exception("Pre-inventory-migration backup failed for database: %s", self.db_path)
                raise

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL CHECK (movement_type IN ('SALE', 'IMPORT', 'ADJUSTMENT')),
                quantity_change INTEGER NOT NULL,
                stock_before INTEGER NOT NULL,
                stock_after INTEGER NOT NULL,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_inventory_movements_product_created
            ON inventory_movements(product_id, created_at)
        ''')

    def _migrate_transactions_discount_columns(self):
        self.cursor.execute('PRAGMA table_info(transactions)')
        existing_columns = {row[1] for row in self.cursor.fetchall()}

        columns_to_add = {
            'subtotal_amount': 'REAL DEFAULT 0',
            'discount_percent': 'REAL DEFAULT 0',
            'discount_amount': 'REAL DEFAULT 0',
        }

        missing_columns = set(columns_to_add) - existing_columns
        if missing_columns and self.db_path.exists():
            try:
                backup_path = BackupService(self.db_path).backup_database(reason="before_migration")
                logger.info("Pre-migration backup created: %s", backup_path)
            except Exception:
                logger.exception("Pre-migration backup failed for database: %s", self.db_path)
                raise

        added_columns = set()
        for column_name, column_definition in columns_to_add.items():
            if column_name not in existing_columns:
                self.cursor.execute(f'ALTER TABLE transactions ADD COLUMN {column_name} {column_definition}')
                added_columns.add(column_name)

        if 'subtotal_amount' in added_columns:
            self.cursor.execute('''
                UPDATE transactions
                SET subtotal_amount = total_amount
                WHERE subtotal_amount IS NULL OR subtotal_amount = 0
            ''')
        else:
            self.cursor.execute('''
                UPDATE transactions
                SET subtotal_amount = total_amount
                WHERE subtotal_amount IS NULL
                   OR (subtotal_amount = 0 AND total_amount != 0)
            ''')

        self.cursor.execute('''
            UPDATE transactions
            SET discount_percent = 0
            WHERE discount_percent IS NULL
        ''')
        self.cursor.execute('''
            UPDATE transactions
            SET discount_amount = 0
            WHERE discount_amount IS NULL
        ''')

    def add_sample_data(self):
        sample_products = [
            ('Nước ngọt Coca Cola', '8934673123456', 12000, 50, 'Đồ uống'),
            ('Mì gói Hảo Hảo', '8936036012345', 3500, 100, 'Thực phẩm khô'),
            ('Bánh Oreo', '8936036054321', 25000, 30, 'Bánh kẹo'),
            ('Nước suối Lavie', '8934590123456', 5000, 80, 'Đồ uống'),
            ('Sữa tươi Vinamilk', '8934673567890', 32000, 40, 'Sữa'),
            ('Dầu ăn Simply', '8936036098765', 45000, 25, 'Gia vị'),
            ('Trứng gà (10 quả)', '0000000000001', 35000, 50, 'Thực phẩm tươi'),
            ('Mì tôm Omachi', '8936036023456', 5500, 60, 'Thực phẩm khô'),
        ]
        self.cursor.executemany('''
            INSERT INTO products (name, barcode, price, stock, category)
            VALUES (?, ?, ?, ?, ?)
        ''', sample_products)
        self.conn.commit()

    def close(self):
        self.conn.close()
