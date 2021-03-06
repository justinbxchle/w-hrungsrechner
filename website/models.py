from website import db, login_manager
from flask_login import UserMixin


#Wird benötigt, um das Benutzerobjekt anhand der in der Sitzung gespeicherten Benutzer-ID neu zu laden (zb für is_authenticated etc)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


#Erstellen der einzelnen Tabels der Datenbank
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    image = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    purchases = db.relationship('Purchase', backref='buyer', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image}')"

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    currency_id = db.Column(db.String(20), db.ForeignKey('currency.id'), nullable=False)

    def __repr__(self):
        return f"Purchase('{self.id}','{self.amount}', '{self.user_id}', '{self.currency_id}')"

class Currency(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rate = db.Column(db.Float, nullable=False) 
    character_id = db.Column(db.Integer, db.ForeignKey('character.id') , nullable=False)
    purchases = db.relationship('Purchase', backref='currency', lazy=True)

    def __repr__(self):
        return f"{self.name}"

class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    character = db.Column(db.String(2), nullable=False)
    currencies = db.relationship('Currency', backref='character', lazy=True)

    def __repr__(self):
        return f"{self.character}"





