from flask import Blueprint, render_template, flash, redirect, url_for, request, abort
from flask_login import login_required, current_user
from website.forms import SearchForm, AccountUpdateForm, CurrencyConvertForm, PurchaseForm, DeleteForm
from sqlalchemy import func
from website import db, app
from .models import Currency, User, Purchase
import secrets
from PIL import Image
import os
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go
import matplotlib.pyplot as plt
import plotly.io as pio
from datetime import datetime, timedelta
import time
import atexit
from apscheduler.schedulers.background import BackgroundScheduler




views = Blueprint('views',__name__)

@views.context_processor
def base():
    form = SearchForm()
    return dict(form=form)


@views.route('/', methods=['GET', 'POST'])
@views.route('/home', methods=['GET','POST'])
@login_required
def home():
    currencies = Currency.query.all()
    return render_template('home.html', currencies=currencies)

@views.route('/converter', methods=['GET', 'POST'])
def converter():
    currencies = Currency.query.all()
    user = User.query.all()
    form = CurrencyConvertForm()
    form.input.choices = currencies
    form.output.choices = currencies
    rate = ""
    value = ""
    if form.validate_on_submit():
        try:
            input = Currency.query.filter_by(name=form.input.data).first()
            output = Currency.query.filter_by(name=form.output.data).first()
            if input == output:
                flash('Choose Two Different Currencies!', 'danger')
                return redirect(url_for('views.converter'))
            ticker = str(input.identifier + output.identifier + "=X")
            rate = yf.Ticker(ticker).info['regularMarketPrice']
            value = form.amount.data * rate
            
            hist = yf.download(tickers=ticker, period='max', start="2022-06-05", interval="5m")
            fig = go.Figure(data=go.Scatter(x=hist.index,y=hist['Close'], mode='lines'))
            fig.update_layout(
                title= str(input.identifier + "/" + output.identifier)
            )
            pio.write_html(fig, file='website/templates/chart.html', auto_open=False)
        except:
            abort(502)
    return render_template("converter.html", user=user, form=form, rate=rate, Currency=Currency, value=value, legend="Currency Converter")

"""
@views.route('/home/filter=<category>')
@login_required
def filter(category):
    posts = Post.query.all()
    return render_template("filter.html", posts=posts, category=category)

"""
@views.route('/purchase', methods=['GET', 'POST'])
@login_required
def purchase():
    currencies = Currency.query.all()
    form = PurchaseForm()
    form.currency.choices = currencies
    if form.validate_on_submit():
        currency = Currency.query.filter_by(name=form.currency.data).first()
        purchase = Purchase(date=form.date.data, amount=form.amount.data, buyer=current_user, currency=currency)
        db.session.add(purchase)
        db.session.commit()
        flash('Purchase has been added!', 'success')
        return redirect(url_for('views.account'))
    return render_template("add_purchase.html", form=form, legend='New Purchase')


@views.route('/chart')
def chart():
    return render_template("chart.html")

@views.route('/purchase/update/<int:purchase_id>', methods=['GET', 'POST'])
@login_required
def update_purchase(purchase_id):
    currencies = Currency.query.all()
    form = PurchaseForm()
    form.currency.choices = currencies
    purchase = Purchase.query.get_or_404(purchase_id)
    if purchase.buyer != current_user:
        abort(403)
    if form.validate_on_submit():
        purchase.date = form.date.data
        purchase.amount = form.amount.data
        purchase.currency = Currency.query.filter_by(name=form.currency.data).first()
        db.session.commit()
        flash('Purchase has been updated!', 'success')
        return redirect(url_for('views.account'))
    elif request.method == 'GET':
        form.date.data = purchase.date
        form.amount.data = purchase.amount
        form.currency.data = purchase.currency.name
    return render_template("add_purchase.html", form=form, legend='New Purchase')

@views.route('/purchase/delete/<int:purchase_id>', methods=['GET','POST'])
@login_required
def delete_purchase(purchase_id):
    purchases = Purchase.query.all()
    purchase = Purchase.query.get_or_404(purchase_id)
    if purchase.buyer != current_user:
        abort(403)
    form = DeleteForm()
    if form.validate_on_submit():
        db.session.delete(purchase)
        db.session.commit()
        flash('Purchase has been deleted!', 'success')
        return redirect(url_for('views.account', purchases=purchases))
    return render_template('delete.html', purchase=purchase, form=form, purchases=purchases)


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_filename = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pictures', picture_filename)
    #Resizing the image
    output_size = (300, 300)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    
    return picture_filename
#Methode schreiben zum löschen der alten Bilder, wenn das Bild geändert wird

@views.route('/account/update', methods=['GET', 'POST'])
@login_required
def update_account():
    form = AccountUpdateForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account information has been changed!', 'success')
        return redirect(url_for('views.account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    
    return render_template("update_account.html", form=form)

@views.route('/account', methods=['GET'])
@login_required
def account():
    
    purchases = Purchase.query.order_by(Purchase.date).all()
    return render_template("account.html", purchases=purchases)

@views.route('/dashboard')
@login_required
def dashboard():
    purchases = Purchase.query.order_by(Purchase.date).all()
    currencies = Currency.query.all()
    return render_template("dashboard.html", purchases=purchases, datetime=datetime, yf=yf, currencies=currencies, Purchase=Purchase, func=func)
"""
@views.route('/search', methods=['POST'])
@login_required
def search():
    form = SearchForm()
    posts = Post.query
    if form.validate_on_submit():
        search = form.search.data
        posts = posts.filter(Post.title.like('%'+search+'%'))
        posts = posts.order_by(Post.title).all()
        return render_template("search.html", form=form, search=search, posts=posts)
    return "You have to type something"



@views.route('/add_category', methods=['GET', 'POST'])
@login_required
def add_category():
    categories = Category.query.all()
    posts = Post.query.all()
    form = AddCategoryForm()
    if form.validate_on_submit():
        category = Category(term=form.term.data)
        db.session.add(category)
        db.session.commit()
        flash('Cateegory has been created!', 'success')
        return redirect(url_for('views.add_category', user_id=current_user.id))
    return render_template("add_category.html", form=form, legend='New Category', categories=categories, posts=posts)
"""

#Updating Currency Rate every 10min
def UpdateRate():
    currencies = Currency.query.all()
    for currency in currencies:
        rate = yf.Ticker(currency.identifier + 'USD=X').info['regularMarketPrice']
        currency.rate = rate
        db.session.commit()

scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(func=UpdateRate, trigger="interval", minutes=10)
scheduler.start()
