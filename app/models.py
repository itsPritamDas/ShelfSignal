from datetime import date
from .extensions import db


class Product(db.Model):
    __tablename__ = "products"

    product_id = db.Column(db.String(32), primary_key=True)
    product_name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(80), nullable=False, default="Uncategorised")
    default_price = db.Column(db.Float, nullable=False, default=0.0)


class Inventory(db.Model):
    __tablename__ = "inventory"
    __table_args__ = (db.UniqueConstraint("product_id", "store_id", name="uq_inventory_product_store"),)

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(32), db.ForeignKey("products.product_id"), nullable=False)
    store_id = db.Column(db.String(32), nullable=False)
    current_stock = db.Column(db.Integer, nullable=False, default=0)
    lead_time_days = db.Column(db.Integer, nullable=False, default=3)
    safety_stock_days = db.Column(db.Integer, nullable=False, default=3)

    product = db.relationship("Product", backref=db.backref("inventory_rows", lazy=True))


class SalesRecord(db.Model):
    __tablename__ = "sales_records"
    __table_args__ = (
        db.UniqueConstraint("sale_date", "store_id", "product_id", name="uq_sales_date_store_product"),
        db.Index("ix_sales_product_store_date", "product_id", "store_id", "sale_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    sale_date = db.Column(db.Date, nullable=False, index=True)
    store_id = db.Column(db.String(32), nullable=False, index=True)
    product_id = db.Column(db.String(32), db.ForeignKey("products.product_id"), nullable=False, index=True)
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    promotion = db.Column(db.Boolean, nullable=False, default=False)
    holiday = db.Column(db.Boolean, nullable=False, default=False)
    sales_units = db.Column(db.Integer, nullable=False)

    product = db.relationship("Product", backref=db.backref("sales_records", lazy=True))
