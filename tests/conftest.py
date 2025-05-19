import pytest
import os
from unittest import mock
from app.terracore import create_app, db
from flask import template_rendered
import functools

@pytest.fixture(scope='session')
def app():
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['SECRET_KEY'] = 'test'
    os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    # Patch get_secret to return dummy values during tests
    with mock.patch('app.terracore.get_secret') as get_secret_mock:
        get_secret_mock.side_effect = lambda name: {
            'terracore/FLASK_SECRET_KEY': 'test',
            'terracore/MYSQL_USER': 'user',
            'terracore/MYSQL_PASSWORD': 'pass',
            'terracore/GOOGLE_OAUTH_CLIENT_ID': 'dummy',
            'terracore/GOOGLE_OAUTH_CLIENT_SECRET': 'dummy',
            'terracore/OPENAI_API_KEY': 'dummy',
        }.get(name, 'dummy')
        app = create_app()
        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture(autouse=True)
def always_authenticated(monkeypatch, app, request):
    from app.terracore.models import User
    def get_user():
        with app.app_context():
            user = User.query.filter_by(email='authtest@example.com').first()
            if not user:
                user = User(email='authtest@example.com', name='Auth Test', role='user')
                from app.terracore import db
                db.session.add(user)
                db.session.commit()
            return user
    monkeypatch.setattr('flask_login.utils._get_user', get_user)

@pytest.fixture
def always_admin_authenticated(monkeypatch, app):
    from app.terracore.models import User
    def get_admin():
        with app.app_context():
            user = User.query.filter_by(email='admin@example.com').first()
            if not user:
                from app.terracore import db
                user = User(email='admin@example.com', name='Admin User', role='admin')
                db.session.add(user)
                db.session.commit()
            return user
    monkeypatch.setattr('flask_login.utils._get_user', get_admin) 