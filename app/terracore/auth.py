from flask import Blueprint, redirect, url_for, session, flash, make_response, request
from flask_login import login_user, logout_user, current_user, login_required
from flask_dance.contrib.google import google, make_google_blueprint
from . import db, login_manager
from .models import User
import os
import logging

ADMIN_EMAILS = [
    "brettbergin@gmail.com",
    "whitsonjj@gmail.com",
    "whitsonjacob@gmail.com"
]

auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth_bp.route('/login')
def login():
    logging.info("[AUTH_DEBUG] login: current_user.is_authenticated=%s", current_user.is_authenticated)
    logging.info("[AUTH_DEBUG] login: session=%s", dict(session))
    logging.info("[AUTH_DEBUG] login: request.cookies=%s", request.cookies)
    if not google.authorized:
        return redirect(url_for('google.login'))
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.", "danger")
        return redirect(url_for('main.index'))
    info = resp.json()
    email = info["email"]
    avatar_url = info.get("picture")
    user = User.query.filter_by(email=email).first()
    if not user:
        role = 'admin' if email in ADMIN_EMAILS else 'user'
        user = User(email=email, name=info.get("name"), role=role, avatar_url=avatar_url)
        db.session.add(user)
        db.session.commit()
    else:
        # Update avatar_url if changed
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
            db.session.commit()
    login_user(user)
    # Force session to be saved before redirect
    resp = make_response(redirect(url_for('main.index')))
    session.modified = True
    logging.info("[AUTH_DEBUG] login (post-login_user): current_user.is_authenticated=%s", current_user.is_authenticated)
    logging.info("[AUTH_DEBUG] login (post-login_user): session=%s", dict(session))
    logging.info("[AUTH_DEBUG] login (post-login_user): request.cookies=%s", request.cookies)
    return resp

@auth_bp.route('/logout')
@login_required
def logout():
    logging.info("[AUTH_DEBUG] logout (pre): current_user.is_authenticated=%s", current_user.is_authenticated)
    logging.info("[AUTH_DEBUG] logout (pre): session=%s", dict(session))
    logging.info("[AUTH_DEBUG] logout (pre): request.cookies=%s", request.cookies)
    
    logout_user()
    session.clear()
    
    resp = redirect(url_for('main.index'))
    
    logging.info("[AUTH_DEBUG] logout (post): current_user.is_authenticated=%s", current_user.is_authenticated)
    logging.info("[AUTH_DEBUG] logout (post): session=%s", dict(session))
    logging.info("[AUTH_DEBUG] logout (post): request.cookies=%s", request.cookies)
    
    return resp
