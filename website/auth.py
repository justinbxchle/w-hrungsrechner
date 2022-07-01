from flask import Blueprint, render_template, flash, redirect, url_for, request
from .forms import RegistrationForm, LoginForm
from website import db, bcrypt
from .models import User
from flask_login import login_user, current_user, login_required, logout_user

auth = Blueprint('auth',__name__)

#Registrierung
@auth.route("/register", methods=['GET', 'POST'])
def register():
    #Wenn der Benutzer schon eingelogged ist wird er wieder zurückgeschickt
    if current_user.is_authenticated:
        return redirect(url_for('views.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        #Das Password wird gehasht mit Bcrypt (Blowfish Algorithmus)
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        #hashed_password = bcrypt.hashpw(form.password.data.encode('utf-8'), bcrypt.gensalt())
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account created!', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html', form=form)

#Login
@auth.route("/login", methods=['GET', 'POST'])
def login():
    #Wenn der Benutzer schon eingelogged ist wird er wieder zurückgeschickt
    if current_user.is_authenticated:
        return redirect(url_for('views.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        #Überprüfung ob der User existiert und ob das passwort mit dem gehashten passwort zusammenpasst
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            #User wird eingeloggt
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            #Wollte der User vorher auf eine andere Seite wird er dort hingeschickt, wenn nicht wird er zur Hompage geschickt 
            return redirect(next_page) if next_page else redirect(url_for('views.home'))
        else:
            flash('User not found! Please check your email and/or password', 'danger')
    return render_template('login.html', form=form)

#Logout
@auth.route("/logout")
@login_required
def logout():
    #User wird ausgeloggt
    logout_user()
    return redirect(url_for('auth.login'))