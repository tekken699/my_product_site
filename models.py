from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    # Новое поле search_query – по умолчанию пустая строка (можно задать default="", либо реализовать логику заполнения)
    search_query = db.Column(db.String(255), default="")
    price = db.Column(db.Float, nullable=False, default=0.0)
    price_display = db.Column(db.String(64))
    site = db.Column(db.String(64))
    link = db.Column(db.String(256), unique=True, nullable=False)
    img_url = db.Column(db.String(256))
    quantity = db.Column(db.Integer, default=1)
    step = db.Column(db.Integer, default=1)
    availability = db.Column(db.String(128))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "search_query": self.search_query,
            "price": self.price,
            "price_display": self.price_display,
            "site": self.site,
            "link": self.link,
            "img_url": self.img_url,
            "quantity": self.quantity,
            "step": self.step,
            "availability": self.availability,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }

        
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    fio = db.Column(db.String(128))
    phone = db.Column(db.String(30))
    address = db.Column(db.String(256))
    ip = db.Column(db.String(64))
    inn = db.Column(db.String(64))
    
    # Добавленное поле: если True – пользователь является администратором
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
