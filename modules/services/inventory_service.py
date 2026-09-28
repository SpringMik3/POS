from modules.app_logger import get_logger


logger = get_logger(__name__)


class InventoryService:
    VALID_MOVEMENT_TYPES = {'SALE', 'IMPORT', 'ADJUSTMENT'}

    def __init__(self, conn):
        self.conn = conn

    def get_current_stock(self, product_id):
        """Return current stock for a product id."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT stock FROM products WHERE id = ?', (int(product_id),))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Không tìm thấy sản phẩm ID {product_id}")
        return int(row[0] or 0)

    def record_movement(self, product_id, movement_type, quantity_change, stock_before, stock_after, note=None):
        """Insert an inventory movement row."""
        movement_type = (movement_type or '').upper()
        if movement_type not in self.VALID_MOVEMENT_TYPES:
            raise ValueError(f"Loại biến động tồn kho không hợp lệ: {movement_type}")

        cursor = self.conn.cursor()
        cursor.execute(
            '''
            INSERT INTO inventory_movements (
                product_id,
                movement_type,
                quantity_change,
                stock_before,
                stock_after,
                note
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                int(product_id),
                movement_type,
                int(quantity_change),
                int(stock_before),
                int(stock_after),
                note,
            ),
        )
        return cursor.lastrowid

    def validate_stock_available(self, product_id, quantity, product_name=None):
        """Return current stock or raise when stock cannot cover the quantity."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT stock FROM products WHERE id = ?', (int(product_id),))
        row = cursor.fetchone()

        label = product_name or f'ID {product_id}'
        if not row:
            raise ValueError(f"Không tìm thấy sản phẩm ID {product_id}: {label}")

        current_stock = int(row[0] or 0)
        required_quantity = int(quantity)
        if current_stock < required_quantity:
            raise ValueError(f"Không đủ tồn kho cho {label}. Còn {current_stock} sản phẩm.")

        return current_stock

    def decrease_stock(self, product_id, quantity, product_name=None, commit=False, movement_type=None, note=None):
        """Decrease product stock after a stock validation pass."""
        current_stock = self.validate_stock_available(product_id, quantity, product_name)
        quantity = int(quantity)
        new_stock = current_stock - quantity
        cursor = self.conn.cursor()
        cursor.execute('UPDATE products SET stock = ? WHERE id = ?', (new_stock, int(product_id)))
        if movement_type:
            self.record_movement(
                product_id=product_id,
                movement_type=movement_type,
                quantity_change=-quantity,
                stock_before=current_stock,
                stock_after=new_stock,
                note=note,
            )
        if commit:
            self.conn.commit()
        return new_stock

    def increase_stock(self, product_id, quantity, note=None, commit=True):
        """Increase stock for an import movement."""
        try:
            quantity = int(str(quantity).strip())
        except (TypeError, ValueError) as exc:
            raise ValueError("Số lượng nhập kho phải là số nguyên.") from exc

        if quantity <= 0:
            raise ValueError("Số lượng nhập kho phải lớn hơn 0.")

        stock_before = self.get_current_stock(product_id)
        stock_after = stock_before + quantity
        cursor = self.conn.cursor()
        cursor.execute('UPDATE products SET stock = ? WHERE id = ?', (stock_after, int(product_id)))
        self.record_movement(
            product_id=product_id,
            movement_type='IMPORT',
            quantity_change=quantity,
            stock_before=stock_before,
            stock_after=stock_after,
            note=note,
        )
        if commit:
            self.conn.commit()
        return stock_after

    def record_adjustment(self, product_id, stock_before, stock_after, note=None):
        """Record a manual stock adjustment when the stock value changes."""
        quantity_change = int(stock_after) - int(stock_before)
        if quantity_change == 0:
            return None
        return self.record_movement(
            product_id=product_id,
            movement_type='ADJUSTMENT',
            quantity_change=quantity_change,
            stock_before=stock_before,
            stock_after=stock_after,
            note=note,
        )

    def get_low_stock_products(self, threshold=10, limit=50):
        """Return products below the configured stock threshold."""
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            SELECT name, stock
            FROM products
            WHERE stock < ?
            ORDER BY stock ASC, name ASC
            LIMIT ?
            ''',
            (int(threshold), int(limit)),
        )
        return [{'name': name, 'stock': stock or 0} for name, stock in cursor.fetchall()]

    def get_movements(self, product_id=None, limit=100):
        """Return recent inventory movements, optionally filtered by product."""
        cursor = self.conn.cursor()
        query = '''
            SELECT
                im.id,
                im.product_id,
                COALESCE(p.name, '') AS product_name,
                im.movement_type,
                im.quantity_change,
                im.stock_before,
                im.stock_after,
                COALESCE(im.note, '') AS note,
                im.created_at
            FROM inventory_movements im
            LEFT JOIN products p ON p.id = im.product_id
        '''
        params = []

        if product_id is not None:
            query += ' WHERE im.product_id = ?'
            params.append(int(product_id))

        query += ' ORDER BY im.created_at DESC, im.id DESC LIMIT ?'
        params.append(int(limit))
        cursor.execute(query, tuple(params))

        return [
            {
                'id': movement_id,
                'product_id': item_product_id,
                'product_name': product_name,
                'movement_type': movement_type,
                'quantity_change': quantity_change,
                'stock_before': stock_before,
                'stock_after': stock_after,
                'note': note,
                'created_at': created_at,
            }
            for (
                movement_id,
                item_product_id,
                product_name,
                movement_type,
                quantity_change,
                stock_before,
                stock_after,
                note,
                created_at,
            ) in cursor.fetchall()
        ]
