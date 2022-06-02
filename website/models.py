from website import db, login_manager
from flask_login import UserMixin
from datetime import datetime


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    image = db.Column(db.String(20), nullable=False, default='default.jpg')
    bio = db.Column(db.String(150))
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref='post_author', lazy=True)
    comments = db.relationship('Comment', backref='comment_author', lazy=True)
    ratings = db.relationship('Rating', backref='rater', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image}')"

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(30), nullable=False)
    posts = db.relationship('Post', backref='overname', lazy=True)

    def __repr__(self):
        return f"{self.term}"

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ratings = db.relationship('Rating', backref='rated', lazy=True)
    comments = db.relationship('Comment', backref='post', lazy=True)
    
    def __repr__(self):
        return f"Post('{self.title}', '{self.date}', '{self.overname}', '{self.user_id}')"

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rate = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    def __repr__(self):
        return f"Rating('{self.rate}')"

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    
    def __repr__(self):
        return f"Comment('{self.content}')"
    

