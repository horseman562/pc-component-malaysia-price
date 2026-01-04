import psycopg2
from psycopg2 import sql
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DB_CONFIG


def create_database():
    """Create the database if it doesn't exist"""
    conn = psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"]
    )
    conn.autocommit = True
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_CONFIG["database"],))
    if not cursor.fetchone():
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(
            sql.Identifier(DB_CONFIG["database"])
        ))
        print(f"Database '{DB_CONFIG['database']}' created!")
    else:
        print(f"Database '{DB_CONFIG['database']}' already exists.")

    cursor.close()
    conn.close()


def create_tables():
    """Create flexible tables for any product tracking"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Categories table (ram, gpu, ssd, cpu, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            slug VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Platforms table (shopee, lazada, idealtech, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS platforms (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            base_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Products table - flexible for any hardware
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            category_id INTEGER REFERENCES categories(id),
            platform_id INTEGER REFERENCES platforms(id),
            name VARCHAR(500) NOT NULL,
            url TEXT UNIQUE NOT NULL,
            shop_name VARCHAR(255),
            image_url TEXT,
            brand VARCHAR(100),
            specs JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Price history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id SERIAL PRIMARY KEY,
            product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
            price DECIMAL(10, 2) NOT NULL,
            original_price DECIMAL(10, 2),
            discount_percent INTEGER,
            stock INTEGER,
            sold INTEGER,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Price alerts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_alerts (
            id SERIAL PRIMARY KEY,
            product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
            target_price DECIMAL(10, 2) NOT NULL,
            is_triggered BOOLEAN DEFAULT FALSE,
            triggered_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Search queries table - track what we're monitoring
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_queries (
            id SERIAL PRIMARY KEY,
            category_id INTEGER REFERENCES categories(id),
            platform_id INTEGER REFERENCES platforms(id),
            keyword VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            last_scraped_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_platform ON products(platform_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_product ON price_history(product_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(scraped_at)")

    conn.commit()

    # Insert default categories
    cursor.execute("""
        INSERT INTO categories (name, slug, description)
        VALUES
            ('RAM', 'ram', 'Memory modules - DDR4, DDR5'),
            ('GPU', 'gpu', 'Graphics cards - NVIDIA, AMD'),
            ('SSD', 'ssd', 'Solid state drives'),
            ('CPU', 'cpu', 'Processors - Intel, AMD'),
            ('Motherboard', 'motherboard', 'Mainboards'),
            ('PSU', 'psu', 'Power supply units')
        ON CONFLICT (slug) DO NOTHING
    """)

    # Insert default platforms
    cursor.execute("""
        INSERT INTO platforms (name, base_url)
        VALUES
            ('Shopee', 'https://shopee.com.my'),
            ('Lazada', 'https://lazada.com.my'),
            ('Ideal Tech', 'https://idealtech.com.my'),
            ('PC Image', 'https://pcimage.com.my')
        ON CONFLICT (name) DO NOTHING
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("Tables created successfully!")


if __name__ == "__main__":
    print("Setting up database...")
    create_database()
    create_tables()
    print("Done!")
