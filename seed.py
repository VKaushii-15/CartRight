from app.db import Base, engine, SessionLocal
from app.models import Product, DiscountCode
import random

Base.metadata.create_all(bind=engine)
db = SessionLocal()

products = [
    Product(name="Blue Hoodie - Medium", description="Cotton blend hoodie", price=1299.0, stock=20),
    Product(name="Blue Hoodie - Large", description="Cotton blend hoodie", price=1299.0, stock=15),
    Product(name="White Sneakers", description="Everyday sneakers", price=2499.0, stock=10),
    Product(name="Black Backpack", description="20L laptop backpack", price=1899.0, stock=8),
    Product(name="Wireless Earbuds", description="Bluetooth 5.0, 20h battery", price=1999.0, stock=25),
    Product(name="Gaming Mouse", description="Ergonomic RGB precise gaming mouse", price=3499.0, stock=12),
    Product(name="Mechanical Keyboard", description="Clicky switches RGB keyboard", price=4599.0, stock=15),
    Product(name="Desk Mat", description="Extra large smooth desk mat", price=699.0, stock=40),
    Product(name="Coffee Mug", description="Minimalist ceramic coffee mug 350ml", price=399.0, stock=50),
    Product(name="Denim Jacket", description="Classic blue denim jacket", price=2199.0, stock=8),
    Product(name="Running Shorts", description="Flexible quick-dry shorts", price=899.0, stock=30),
    Product(name="Yoga Mat", description="Non-slip eco-friendly yoga mat", price=1199.0, stock=22),
]

for p in products:
    exists = db.query(Product).filter(Product.name == p.name).first()
    if not exists:
        db.add(p)

discount_codes = [
    ("SAVE10", 10),
    ("PROMO15", 15),
    ("CART20", 20),
    ("WELCOME25", 25),
    ("FLASH30", 30),
]

# Create some random one-time use codes
for i in range(5):
    random_str = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))
    random_pct = random.choice([10, 15, 20, 25, 30, 40, 50])
    discount_codes.append((f"MYSTERY-{random_str}", random_pct))

for name, percent in discount_codes:
    exists = db.query(DiscountCode).filter(DiscountCode.code == name).first()
    if not exists:
        db.add(DiscountCode(code=name, discount_percent=percent))

db.commit()
print(f"Seeded {len(products)} products and {len(discount_codes)} discount codes.")
db.close()
