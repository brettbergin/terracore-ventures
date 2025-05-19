import pytest
from app.terracore.models import User
from flask import url_for

@pytest.fixture
def new_user(app):
    from app.terracore import db
    from app.terracore.models import User
    user = User.query.filter_by(email='testuser@example.com').first()
    if not user:
        user = User(email='testuser@example.com', name='Test User', role='user')
        db.session.add(user)
        db.session.commit()
    return user

@pytest.fixture
def admin_user(app):
    from app.terracore import db
    from app.terracore.models import User
    user = User.query.filter_by(email='admin@example.com').first()
    if not user:
        user = User(email='admin@example.com', name='Admin User', role='admin')
        db.session.add(user)
        db.session.commit()
    return user

@pytest.mark.usefixtures('app')
def test_login_required(client):
    resp = client.get('/prospects', follow_redirects=False)
    assert resp.status_code == 200
    assert b'Login' in resp.data or b'login' in resp.data or b'Terracore Ventures' in resp.data

def test_admin_access(client, admin_user, always_admin_authenticated):
    resp = client.get('/admin')
    assert resp.status_code == 200
    assert b'Admin Dashboard' in resp.data

def test_rbac_standard_user(client, new_user):
    resp = client.get('/admin', follow_redirects=True)
    assert b'Admin access required.' in resp.data 