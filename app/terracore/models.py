from . import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255))
    role = db.Column(db.String(32), default='user')  # 'admin' or 'user'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    display_name = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(32), nullable=True)
    avatar_url = db.Column(db.String(512), nullable=True)

    def __repr__(self):
        return f'<User {self.email}>'

class Prospect(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zillow_url = db.Column(db.String(512), unique=True, nullable=False)
    address = db.Column(db.String(255))
    data = db.Column(db.JSON)  # Cached ChatGPT/analysis data
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    raw_data = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default='pending')

    def __repr__(self):
        return f'<Prospect {self.zillow_url}>'

class Partner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

class FinancialAssumptions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_ratio = db.Column(db.Float, default=0.35)
    interest_rate = db.Column(db.Float, default=0.07)
    down_payment = db.Column(db.Float, default=0.20)
    appreciation_rate = db.Column(db.Float, default=0.03)
    years = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    prospect_id = db.Column(db.Integer, db.ForeignKey('prospect.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prospect_id = db.Column(db.Integer, db.ForeignKey('prospect.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(64))
    target = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text, nullable=True) 