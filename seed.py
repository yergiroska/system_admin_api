from faker import Faker
from app.database import SessionLocal
from app.models import User, Customer, Company, Product, CompanyProduct, CompanyProductPrice, Purchase
from datetime import datetime, timedelta
import random
import string

fake = Faker('es_ES')
db = SessionLocal()

def random_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=60))

def seed_companies(n=20):
    companies = []
    for _ in range(n):
        company = Company(
            name=fake.company(),
            description=fake.catch_phrase(),
            image_url=None,
            created_at=fake.date_time_this_year(),
            updated_at=datetime.now(),
        )
        db.add(company)
    db.commit()
    companies = db.query(Company).all()
    print(f"✅ {len(companies)} empresas creadas")
    return companies


def seed_products(n=50):
    productos = [
        "Harina", "Arroz", "Aceite", "Azúcar", "Sal", "Leche", "Mantequilla",
        "Huevos", "Pan", "Pasta", "Tomate", "Cebolla", "Ajo", "Pollo", "Carne",
        "Pescado", "Jabón", "Shampoo", "Papel higiénico", "Detergente",
        "Café", "Té", "Jugo", "Refresco", "Agua", "Cerveza", "Vino",
        "Galletas", "Chocolate", "Yogur", "Queso", "Jamón", "Atún",
        "Lentejas", "Garbanzos", "Frijoles", "Avena", "Maíz", "Sopa",
        "Mayonesa", "Ketchup", "Mostaza", "Vinagre", "Pimienta", "Oregano",
        "Papel aluminio", "Bolsas", "Escoba", "Trapeador", "Esponja"
    ]
    for nombre in productos[:n]:
        product = Product(
            name=nombre,
            description=fake.sentence(nb_words=6),
            image_url=None,
            created_at=fake.date_time_this_year(),
            updated_at=datetime.now(),
        )
        db.add(product)
    db.commit()
    products = db.query(Product).all()
    print(f"✅ {len(products)} productos creados")
    return products


def seed_company_products(companies, products):
    pairs = set()
    company_products = []
    for company in companies:
        selected = random.sample(products, k=random.randint(5, 15))
        for product in selected:
            pair = (company.id, product.id)
            if pair not in pairs:
                pairs.add(pair)
                cp = CompanyProduct(
                    company_id=company.id,
                    product_id=product.id,
                    created_at=fake.date_time_this_year(),
                    updated_at=datetime.now(),
                )
                db.add(cp)
    db.commit()
    company_products = db.query(CompanyProduct).all()
    print(f"✅ {len(company_products)} relaciones empresa-producto creadas")
    return company_products


def seed_prices(company_products):
    for cp in company_products:
        # Cada producto tiene entre 3 y 8 cambios de precio en el tiempo
        num_prices = random.randint(3, 8)
        base_price = round(random.uniform(0.5, 50.0), 2)
        for i in range(num_prices):
            variation = round(random.uniform(-0.1, 0.15), 2)
            price = round(base_price * (1 + variation), 2)
            cpp = CompanyProductPrice(
                company_product_id=cp.id,
                price=price,
                created_at=datetime.now() - timedelta(days=(num_prices - i) * 30),
                updated_at=datetime.now(),
            )
            db.add(cpp)
            base_price = price
    db.commit()
    total = db.query(CompanyProductPrice).count()
    print(f"✅ {total} precios creados")


def seed_users_and_customers(n=100):
    users = []
    for _ in range(n):
        user = User(
            name=fake.name(),
            email=fake.unique.email(),
            password='hashed_password',
            api_token=random_token(),
            created_at=fake.date_time_this_year(),
            updated_at=datetime.now(),
        )
        db.add(user)
        db.flush()

        customer = Customer(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            birth_date=fake.date_of_birth(minimum_age=18, maximum_age=70),
            identity_document=fake.nif(),
            user_id=user.id,
            created_at=fake.date_time_this_year(),
            updated_at=datetime.now(),
        )
        db.add(customer)
        users.append(user)
    db.commit()
    customers = db.query(Customer).all()
    print(f"✅ {len(customers)} clientes creados")
    return customers


def seed_purchases(customers, company_products, n=500):
    for _ in range(n):
        customer = random.choice(customers)
        cp = random.choice(company_products)

        last_price = (
            db.query(CompanyProductPrice)
            .filter(CompanyProductPrice.company_product_id == cp.id)
            .order_by(CompanyProductPrice.created_at.desc())
            .first()
        )
        unit_price = float(last_price.price) if last_price else round(random.uniform(1, 50), 2)
        quantity = random.randint(1, 20)

        purchase = Purchase(
            customer_id=customer.id,
            company_product_id=cp.id,
            unit_price=unit_price,
            quantity=quantity,
            total=round(unit_price * quantity, 2),
            created_at=fake.date_time_this_year(),
            updated_at=datetime.now(),
        )
        db.add(purchase)
    db.commit()
    total = db.query(Purchase).count()
    print(f"✅ {total} compras creadas")


if __name__ == "__main__":
    print("🌱 Iniciando seed...")
    companies = seed_companies(20)
    products = seed_products(50)
    company_products = seed_company_products(companies, products)
    seed_prices(company_products)
    customers = seed_users_and_customers(100)
    seed_purchases(customers, company_products, 500)
    print("🎉 Seed completado!")
    db.close()