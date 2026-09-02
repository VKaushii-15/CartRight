from app.db import Base, engine, SessionLocal
from app.models import Product

Base.metadata.create_all(bind=engine)
db = SessionLocal()

products = [
    Product(name="Blue Hoodie - Medium", description="Cotton blend hoodie", price=1299.0, stock=20),
    Product(name="Blue Hoodie - Large", description="Cotton blend hoodie", price=1299.0, stock=15),
    Product(name="White Sneakers", description="Everyday sneakers", price=2499.0, stock=10),
    Product(name="Black Backpack", description="20L laptop backpack", price=1899.0, stock=8),
    Product(name="Wireless Earbuds", description="Bluetooth 5.0, 20h battery", price=1999.0, stock=25),
]

for p in products:
    exists = db.query(Product).filter(Product.name == p.name).first()
    if not exists:
        db.add(p)

db.commit()
print(f"Seeded {len(products)} products (skipping duplicates).")
db.close()
