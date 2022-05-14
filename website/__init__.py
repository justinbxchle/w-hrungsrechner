from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils.functions import database_exists
from flask_bcrypt import Bcrypt
from flask_login import LoginManager


def create_database(app):
    if not database_exists('sqlite:///database.db'):
        db.create_all(app=app)



app = Flask(__name__)
app.config['SECRET_KEY'] = '3f3195e5e78966038c3cf51f7561e58e'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
    

from .views import views
from .auth import auth

app.register_blueprint(views, url_prefix='/')
app.register_blueprint(auth, url_prefix='/')

create_database(app)




