from sqlalchemy import Column, Integer, BigInteger, String, Float, Numeric, ForeignKey, DateTime, Date, Text
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    email_verified_at = Column(DateTime, nullable=True)
    password = Column(String, nullable=False)
    remember_token = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    last_session = Column(DateTime, nullable=True)
    is_connected = Column(Integer, nullable=True)
    api_token = Column(String, nullable=True)

    customer = relationship("Customer", back_populates="user", uselist=False)
    logins = relationship("UserLogin", back_populates="user")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(BigInteger, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    birth_date = Column(Date, nullable=True)
    identity_document = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="customer")
    purchases = relationship("Purchase", back_populates="customer")

    orders = relationship("Order", back_populates="customer")


class Company(Base):
    __tablename__ = "companies"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    company_products = relationship("CompanyProduct", back_populates="company")


class Product(Base):
    __tablename__ = "products"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    company_products = relationship("CompanyProduct", back_populates="product")


class CompanyProduct(Base):
    __tablename__ = "company_product"

    id = Column(BigInteger, primary_key=True, index=True)
    company_id = Column(BigInteger, ForeignKey("companies.id"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.id"), nullable=False)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="company_products")
    product = relationship("Product", back_populates="company_products")
    prices = relationship("CompanyProductPrice", back_populates="company_product")
    purchases = relationship("Purchase", back_populates="company_product")


class CompanyProductPrice(Base):
    __tablename__ = "company_product_prices"

    id = Column(BigInteger, primary_key=True, index=True)
    company_product_id = Column(BigInteger, ForeignKey("company_product.id"), nullable=False)
    price = Column(Numeric, nullable=False)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    company_product = relationship("CompanyProduct", back_populates="prices")


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(BigInteger, primary_key=True, index=True)
    customer_id = Column(BigInteger, ForeignKey("customers.id"), nullable=False)
    company_product_id = Column(BigInteger, ForeignKey("company_product.id"), nullable=False)
    unit_price = Column(Numeric, nullable=True)
    quantity = Column(Integer, nullable=False)
    total = Column(Numeric, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="purchases")
    company_product = relationship("CompanyProduct", back_populates="purchases")

    order_id = Column(BigInteger, ForeignKey("orders.id"), nullable=True)
    order = relationship("Order", back_populates="purchases")


class UserLogin(Base):
    __tablename__ = "user_logins"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    start_connection = Column(DateTime, nullable=True)
    end_connection = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="logins")


class Order(Base):
    __tablename__ = "orders"

    id = Column(BigInteger, primary_key=True, index=True)
    customer_id = Column(BigInteger, ForeignKey("customers.id"), nullable=False)
    total = Column(Numeric, nullable=False, default=0)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="orders")
    purchases = relationship("Purchase", back_populates="order")