import psycopg2
from psycopg2.extras import RealDictCursor
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DB_CONFIG


def get_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)


def get_category_id(slug):
    """Get category ID by slug (ram, gpu, ssd, etc.)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM categories WHERE slug = %s", (slug,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else None


def get_platform_id(name):
    """Get platform ID by name (Shopee, Lazada, etc.)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM platforms WHERE name = %s", (name,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else None


def save_product(product_data):
    """Save or update a product, return product ID"""
    conn = get_connection()
    cursor = conn.cursor()

    # Check if product exists
    cursor.execute("SELECT id FROM products WHERE url = %s", (product_data['url'],))
    existing = cursor.fetchone()

    if existing:
        product_id = existing[0]
        cursor.execute("""
            UPDATE products
            SET name = %s, shop_name = %s, image_url = %s, brand = %s,
                specs = %s, updated_at = %s
            WHERE id = %s
        """, (
            product_data['name'],
            product_data.get('shop_name'),
            product_data.get('image_url'),
            product_data.get('brand'),
            psycopg2.extras.Json(product_data.get('specs', {})),
            datetime.now(),
            product_id
        ))
    else:
        cursor.execute("""
            INSERT INTO products (category_id, platform_id, name, url, shop_name, image_url, brand, specs)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            product_data['category_id'],
            product_data['platform_id'],
            product_data['name'],
            product_data['url'],
            product_data.get('shop_name'),
            product_data.get('image_url'),
            product_data.get('brand'),
            psycopg2.extras.Json(product_data.get('specs', {}))
        ))
        product_id = cursor.fetchone()[0]

    conn.commit()
    cursor.close()
    conn.close()
    return product_id


def save_price(product_id, price_data):
    """Save price history for a product"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO price_history (product_id, price, original_price, discount_percent, stock, sold)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        product_id,
        price_data['price'],
        price_data.get('original_price'),
        price_data.get('discount_percent'),
        price_data.get('stock'),
        price_data.get('sold')
    ))

    conn.commit()
    cursor.close()
    conn.close()


def get_price_history(product_id, limit=30):
    """Get price history for a product"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT price, original_price, discount_percent, scraped_at
        FROM price_history
        WHERE product_id = %s
        ORDER BY scraped_at DESC
        LIMIT %s
    """, (product_id, limit))

    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


def get_all_products(category_slug=None, platform_name=None):
    """Get all products with latest price"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT p.*, c.name as category_name, pl.name as platform_name,
               ph.price as latest_price, ph.scraped_at as last_scraped
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN platforms pl ON p.platform_id = pl.id
        LEFT JOIN LATERAL (
            SELECT price, scraped_at
            FROM price_history
            WHERE product_id = p.id
            ORDER BY scraped_at DESC
            LIMIT 1
        ) ph ON true
        WHERE 1=1
    """
    params = []

    if category_slug:
        query += " AND c.slug = %s"
        params.append(category_slug)
    if platform_name:
        query += " AND pl.name = %s"
        params.append(platform_name)

    query += " ORDER BY p.updated_at DESC"

    cursor.execute(query, params)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results
