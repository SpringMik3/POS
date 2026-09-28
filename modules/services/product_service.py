import sqlite3

from modules.app_logger import get_logger
from modules.services.inventory_service import InventoryService


logger = get_logger(__name__)


class ProductValidationError(ValueError):
    pass


class DuplicateBarcodeError(ValueError):
    pass


class ProductService:
    def __init__(self, conn):
        self.conn = conn
        self.inventory_service = InventoryService(conn)

    def get_products(self, category='Tat ca'):
        """Return products ordered by name, optionally filtered by category."""
        cursor = self.conn.cursor()
        params = ()
        query = 'SELECT id, name, barcode, price, stock, category FROM products WHERE 1=1'

        if category and category != 'Tat ca' and category != 'Tất cả':
            query += ' AND category = ?'
            params = (category,)

        query += ' ORDER BY name'
        cursor.execute(query, params)
        return cursor.fetchall()

    def search_products(self, search_term='', category='Tat ca'):
        """Search products by name or barcode while preserving category filtering."""
        term = (search_term or '').strip().lower()
        category = category or 'Tat ca'

        if not term:
            return self.get_products(category=category)

        cursor = self.conn.cursor()
        query = '''
            SELECT id, name, barcode, price, stock, category
            FROM products
            WHERE (LOWER(name) LIKE ? OR LOWER(barcode) LIKE ?)
        '''
        params = [f'%{term}%', f'%{term}%']

        if category and category != 'Tat ca' and category != 'Tất cả':
            query += ' AND category = ?'
            params.append(category)

        query += ' ORDER BY name'
        cursor.execute(query, tuple(params))
        return cursor.fetchall()

    def get_product_by_barcode(self, barcode):
        """Return a product tuple for the barcode scanner flow."""
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            SELECT id, name, price, stock
            FROM products
            WHERE barcode = ?
            ''',
            ((barcode or '').strip(),),
        )
        return cursor.fetchone()

    def create_product(self, name, barcode, price, stock, category):
        """Validate and insert a product."""
        data = self.validate_product_input(name, barcode, price, stock, category)
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                '''
                INSERT INTO products (name, barcode, price, stock, category)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (
                    data['name'],
                    data['barcode'] if data['barcode'] else None,
                    data['price'],
                    data['stock'],
                    data['category'],
                ),
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            self.conn.rollback()
            logger.exception("Create product failed because barcode already exists: %s", data['barcode'])
            raise DuplicateBarcodeError("Mã vạch đã tồn tại") from exc

    def update_product(self, product_id, name, barcode, price, stock, category):
        """Validate and update an existing product."""
        data = self.validate_product_input(name, barcode, price, stock, category)
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT stock FROM products WHERE id = ?', (int(product_id),))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Không tìm thấy sản phẩm ID {product_id}")
            stock_before = int(row[0] or 0)

            cursor.execute(
                '''
                UPDATE products
                SET name = ?, barcode = ?, price = ?, stock = ?, category = ?
                WHERE id = ?
                ''',
                (
                    data['name'],
                    data['barcode'] if data['barcode'] else None,
                    data['price'],
                    data['stock'],
                    data['category'],
                    int(product_id),
                ),
            )
            self.inventory_service.record_adjustment(
                product_id=product_id,
                stock_before=stock_before,
                stock_after=data['stock'],
                note='Chỉnh sửa thủ công trong quản lý sản phẩm',
            )
            self.conn.commit()
        except sqlite3.IntegrityError as exc:
            self.conn.rollback()
            logger.exception("Update product failed because barcode already exists: %s", data['barcode'])
            raise DuplicateBarcodeError("Mã vạch đã tồn tại") from exc

    def delete_product(self, product_id):
        """Delete a product by internal id."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM products WHERE id = ?', (int(product_id),))
        self.conn.commit()

    def validate_product_input(self, name, barcode, price, stock, category):
        """Normalize and validate product form values."""
        clean_name = (name or '').strip()
        clean_barcode = (barcode or '').strip()
        clean_category = (category or '').strip()

        if not clean_name:
            raise ProductValidationError("Vui lòng nhập tên sản phẩm!")

        try:
            parsed_price = float(str(price).strip())
        except (TypeError, ValueError) as exc:
            raise ProductValidationError("Giá sản phẩm phải là số!") from exc

        if parsed_price < 0:
            raise ProductValidationError("Giá sản phẩm không được âm!")

        try:
            parsed_stock = int(str(stock).strip())
        except (TypeError, ValueError) as exc:
            raise ProductValidationError("Số lượng phải là số nguyên!") from exc

        if parsed_stock < 0:
            raise ProductValidationError("Số lượng không được âm!")

        return {
            'name': clean_name,
            'barcode': clean_barcode,
            'price': parsed_price,
            'stock': parsed_stock,
            'category': clean_category,
        }

    def product_name_exists(self, name, exclude_id=None):
        """Check duplicate product names without blocking the save flow."""
        cursor = self.conn.cursor()
        query = 'SELECT id FROM products WHERE LOWER(name) = LOWER(?)'
        params = [(name or '').strip()]
        if exclude_id is not None:
            query += ' AND id != ?'
            params.append(int(exclude_id))
        query += ' LIMIT 1'
        cursor.execute(query, tuple(params))
        return cursor.fetchone() is not None

    def get_categories(self):
        """Return product categories for the management filter."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT category FROM products WHERE category IS NOT NULL ORDER BY category')
        return [row[0] for row in cursor.fetchall()]
