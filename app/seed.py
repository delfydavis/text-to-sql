import os
import random
from datetime import date, timedelta

import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}


CUSTOMERS = [
    "Arun Mathew", "Sarah Wilson", "Daniel Thomas", "Priya Nair",
    "Michael Brown", "Emma Davis", "Rahul Menon", "Olivia Smith",
    "James Wilson", "Ananya Rao", "David Miller", "Sophia Taylor",
    "Vikram Shah", "Emily Johnson", "Adam Clark", "Meera Thomas",
    "Ryan Lewis", "Aisha Khan", "Noah Martin", "Neha Patel",
]

REGIONS = ["North", "South", "East", "West"]

CATEGORIES = [
    "Electronics",
    "Office",
    "Furniture",
    "Accessories",
    "Software",
]

PRODUCTS = [
    ("Laptop Pro", "Electronics", 700, 1000),
    ("Wireless Mouse", "Accessories", 15, 30),
    ("Mechanical Keyboard", "Accessories", 35, 70),
    ("Monitor 27", "Electronics", 180, 300),
    ("USB-C Hub", "Accessories", 25, 50),
    ("Office Chair", "Furniture", 120, 220),
    ("Standing Desk", "Furniture", 200, 350),
    ("Desk Lamp", "Office", 20, 45),
    ("Notebook Pack", "Office", 8, 18),
    ("Cloud Pro License", "Software", 40, 90),
    ("Security Suite", "Software", 50, 120),
    ("Webcam HD", "Electronics", 40, 80),
]


def random_date():
    start = date(2025, 1, 1)
    end = date(2026, 8, 28)
    days = (end - start).days
    return start + timedelta(days=random.randint(0, days))


def seed_database():
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            # Start clean so the seed is reproducible.
            cur.execute("""
                TRUNCATE TABLE
                    order_items,
                    orders,
                    products,
                    categories,
                    customers
                RESTART IDENTITY CASCADE;
            """)

            # Categories
            for category in CATEGORIES:
                cur.execute(
                    "INSERT INTO categories (name) VALUES (%s)",
                    (category,)
                )

            # Customers
            for i, name in enumerate(CUSTOMERS, start=1):
                cur.execute(
                    """
                    INSERT INTO customers
                        (name, email, region, created_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        name,
                        f"customer{i}@example.com",
                        random.choice(REGIONS),
                        random_date(),
                    ),
                )

            # Products
            category_ids = {}
            cur.execute("SELECT id, name FROM categories")
            for category_id, name in cur.fetchall():
                category_ids[name] = category_id

            for name, category, cost, price in PRODUCTS:
                cur.execute(
                    """
                    INSERT INTO products
                        (name, category_id, cost, price)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        name,
                        category_ids[category],
                        cost,
                        price,
                    ),
                )

            # Get generated product IDs
            cur.execute("SELECT id FROM products")
            product_ids = [row[0] for row in cur.fetchall()]

            # Orders
            for _ in range(500):
                customer_id = random.randint(1, len(CUSTOMERS))
                order_date = random_date()
                status = random.choice(
                    ["completed", "completed", "completed", "cancelled"]
                )

                cur.execute(
                    """
                    INSERT INTO orders
                        (customer_id, order_date, status)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (customer_id, order_date, status),
                )

                order_id = cur.fetchone()[0]

                # 1–4 products per order
                for product_id in random.sample(
                    product_ids,
                    random.randint(1, min(4, len(product_ids)))
                ):
                    quantity = random.randint(1, 5)

                    cur.execute(
                        "SELECT price FROM products WHERE id = %s",
                        (product_id,),
                    )
                    unit_price = cur.fetchone()[0]

                    cur.execute(
                        """
                        INSERT INTO order_items
                            (order_id, product_id, quantity, unit_price)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            order_id,
                            product_id,
                            quantity,
                            unit_price,
                        ),
                    )

        conn.commit()

    print("Database seeded successfully.")


if __name__ == "__main__":
    seed_database()