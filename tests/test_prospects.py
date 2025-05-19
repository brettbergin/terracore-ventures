import pytest
from app.terracore.models import User, Prospect

@pytest.fixture
def user(app):
    from app.terracore import db
    from app.terracore.models import User
    user = User.query.filter_by(email='prospectuser@example.com').first()
    if not user:
        user = User(email='prospectuser@example.com', name='Prospect User', role='user')
        db.session.add(user)
        db.session.commit()
    return user

def test_submit_prospect(client, user):
    resp = client.post('/prospects', data={'zillow_url': 'https://zillow.com/123'}, follow_redirects=True)
    assert b'Prospect added!' in resp.data
    from app.terracore.models import Prospect
    assert Prospect.query.filter_by(zillow_url='https://zillow.com/123').first() is not None

def test_duplicate_prospect(client, user):
    from app.terracore import db
    p = Prospect(zillow_url='https://zillow.com/dup', created_by=user.id)
    db.session.add(p)
    db.session.commit()
    resp = client.post('/prospects', data={'zillow_url': 'https://zillow.com/dup'}, follow_redirects=True)
    assert b'This prospect already exists.' in resp.data

def test_filter_prospects(client, user, monkeypatch, app):
    from app.terracore import db
    from app.terracore.models import User
    def get_user():
        with app.app_context():
            return User.query.filter_by(email='prospectuser@example.com').first()
    monkeypatch.setattr('flask_login.utils._get_user', get_user)
    db.session.add(Prospect(zillow_url='https://zillow.com/1', created_by=user.id, address='123 Main'))
    db.session.add(Prospect(zillow_url='https://zillow.com/2', created_by=user.id, address='456 Oak'))
    db.session.commit()
    resp = client.get('/prospects?search=Main')
    assert resp.status_code == 200
    assert b'Main' in resp.data or b'123 Main' in resp.data 