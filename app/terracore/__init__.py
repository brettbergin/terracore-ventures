import os
import boto3
from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_dance.contrib.google import make_google_blueprint
import json
import logging
from flask_session import Session

def get_secret(name):

    env_var = name.split('/')[-1]
    if env_var in os.environ:
        return os.environ[env_var]

    client = boto3.client('secretsmanager')
    value = client.get_secret_value(SecretId=name)['SecretString']
    return value

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or get_secret('terracore/FLASK_SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI') or (
        f"mysql+pymysql://{get_secret('terracore/MYSQL_USER')}:{get_secret('terracore/MYSQL_PASSWORD')}@"
        f"localhost:3306/terracore"
    )
    
    logging.debug(f"SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"[DEBUG] SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_TYPE'] = 'filesystem' 
    app.config['SESSION_PERMANENT'] = False 
    app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    Session(app)

    from .auth import auth_bp
    from .views import main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    google_client_id = get_secret('terracore/GOOGLE_OAUTH_CLIENT_ID')
    google_client_secret = get_secret('terracore/GOOGLE_OAUTH_CLIENT_SECRET')
    
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("flask_dance").setLevel(logging.DEBUG)
    logging.getLogger("oauthlib").setLevel(logging.DEBUG)
    
    google_bp = make_google_blueprint(
        client_id=google_client_id,
        client_secret=google_client_secret,
        scope=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ],
        redirect_to="auth.login"
    )
    
    google_bp.session.params["prompt"] = "select_account"

    app.register_blueprint(google_bp, url_prefix="/auth")

    os.environ['OPENAI_API_KEY'] = get_secret('terracore/OPENAI_API_KEY')
    app.jinja_env.filters['loads'] = json.loads
    return app
