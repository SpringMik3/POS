"""Additive migration: keep existing sales and COD records intact."""
def migrate(conn):
    columns = {
        'transactions': {'customer_id': 'INTEGER', 'refund_of': 'INTEGER', 'exchange_for': 'INTEGER', 'reason': 'TEXT'},
        'delivery_orders': {'customer_id': 'INTEGER', 'carrier_fee': 'INTEGER', 'received_amount': 'INTEGER',
                            'settlement_note': 'TEXT', 'settled_at': 'TEXT'},
    }
    with conn:
        for table, additions in columns.items():
            existing = {r[1] for r in conn.execute(f'PRAGMA table_info({table})')}
            for name, kind in additions.items():
                if name not in existing:
                    conn.execute(f'ALTER TABLE {table} ADD COLUMN {name} {kind}')
        conn.execute('''CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT UNIQUE,
            address TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS return_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, refund_id INTEGER NOT NULL,
            original_item_id INTEGER NOT NULL, quantity INTEGER NOT NULL CHECK(quantity>0),
            amount INTEGER NOT NULL CHECK(amount>=0), restock INTEGER NOT NULL CHECK(restock IN (0,1)))''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_return_original ON return_items(original_item_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_transaction_customer ON transactions(customer_id)')
        conn.execute('''CREATE TABLE IF NOT EXISTS order_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL,
            old_status TEXT, new_status TEXT, note TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
