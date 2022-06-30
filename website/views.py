from flask import Blueprint, render_template, flash, redirect, url_for, request, abort
from flask_login import login_required, current_user
from website.forms import SearchForm, AccountUpdateForm, CurrencyConvertForm, PurchaseForm, DeleteForm, PortfolioForm
from sqlalchemy import func
from website import db, app
from .models import Currency, User, Purchase
import secrets
from PIL import Image
import os
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go
import plotly.io as pio
from datetime import datetime, timedelta
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
@views.route('/activity', methods=['GET', 'POST'])
@login_required
def activity():
    currencies = Currency.query.all()
    form = PurchaseForm()
    form.currency.choices = currencies
    if form.validate_on_submit():
        currency = Currency.query.filter_by(name=form.currency.data).first()
        if form.type.data == 'Sell':
            days = pd.date_range(end = datetime.today(), start = form.date.data.strftime('%Y-%m-%d')).to_pydatetime().tolist()
            for day in days:
                if float(form.amount.data) > Purchase.query.with_entities(func.sum(Purchase.amount)).filter(Purchase.user_id==current_user.id,Purchase.currency_id==currency.id,Purchase.date <= day.strftime('%Y-%m-%d')).scalar():
                    flash('Amount Exceeds Your Deposit Value!', 'danger')
                    return redirect(url_for('views.activity'))
            form.amount.data = form.amount.data * -1
        purchase = Purchase(date=form.date.data, amount=form.amount.data, buyer=current_user, currency=currency, type=form.type.data)
        db.session.add(purchase)
        db.session.commit()
        flash('Purchase has been added!', 'success')
        return redirect(url_for('views.account'))
    return render_template("activity.html", form=form, legend='New Activity')


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
        currency = Currency.query.filter_by(name=form.currency.data).first()
        if form.type.data == 'Sell':
            days = pd.date_range(end = datetime.today(), start = form.date.data.strftime('%Y-%m-%d')).to_pydatetime().tolist()
            for day in days:
                if purchase.amount+float(form.amount.data) > Purchase.query.with_entities(func.sum(Purchase.amount)).filter(Purchase.user_id==current_user.id,Purchase.currency_id==currency.id,Purchase.date <= day.strftime('%Y-%m-%d')).scalar():
                    flash('Amount Exceeds Your Deposit Value!', 'danger')
                    return redirect(url_for('views.update_purchase', purchase_id=purchase.id))
            form.amount.data = form.amount.data * -1
        purchase.date = form.date.data
        purchase.amount = form.amount.data
        purchase.currency = currency
        db.session.commit()
        flash('Purchase has been updated!', 'success')
        return redirect(url_for('views.account'))
    elif request.method == 'GET':
        form.type.data = purchase.type
        form.date.data = purchase.date
        form.amount.data = abs(purchase.amount)
        form.currency.data = purchase.currency.name
    return render_template("activity.html", form=form, legend='New Purchase')

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

@views.route('/portfolio', methods=['GET','POST'])
@login_required
def portfolio():
    labels = []
    values = []
    
    currencies = Currency.query.all()
    purchases = Purchase.query.all()
    form = PortfolioForm()
    amount = 0
    maximum = 0
    chart=False
    
    for currency in currencies:
        form.currency.choices.append(currency)
    if form.validate_on_submit():
        chart = True
        period = int(form.time.data)
        if form.currency.data != 'All':
            currencies = Currency.query.filter_by(name=form.currency.data)
        if period == 7 or period == 30:
            days = pd.date_range(end = datetime.today(), periods = period).to_pydatetime().tolist()
            beginn = Purchase.query.filter(Purchase.date < days[1].strftime('%Y-%m-%d')).all()
            for currency in currencies:
                for purchase in beginn:
                    if purchase.currency == currency and purchase.buyer == current_user:
                        amount += purchase.amount * purchase.currency.rate
            for day in days:
                labels.append(day.strftime('%d %B'))
                for currency in currencies:
                    for purchase in purchases:
                        if purchase.date.strftime('%Y-%m-%d') == day.strftime('%Y-%m-%d') and purchase.buyer == current_user and purchase.currency == currency:    
                            amount += purchase.amount * purchase.currency.rate
                values.append(int(amount))
        elif period == 12 or period == 24:
            days = pd.date_range(end = datetime.today(), periods = period, freq='M').to_pydatetime().tolist()
            beginn = Purchase.query.filter(Purchase.date < days[1].strftime('%Y-%m-%d')).all()
            for currency in currencies:
                for purchase in beginn:
                    if purchase.currency == currency and purchase.buyer == current_user:
                        amount += purchase.amount * purchase.currency.rate
            for day in days:
                labels.append(day.strftime('%B %Y'))
                for currency in currencies:
                    for purchase in purchases:
                        if purchase.date.strftime('%Y-%m') == day.strftime('%Y-%m') and purchase.buyer == current_user and purchase.currency == currency:
                            amount += purchase.amount * purchase.currency.rate
                values.append(int(amount))
        elif period == 1:
            print(0)
            start = Purchase.query.filter_by(user_id=current_user.id).order_by(Purchase.date).first()
            if start == None or start.date.year == datetime.now().year:
                print(1)
                start = datetime.now() - timedelta(days=1095)
            else:
                start = start.date  
                print(2)      
            days = pd.date_range(start=start,end=datetime.today(), freq='A').to_pydatetime().tolist()
            for day in days:
                labels.append(day.strftime('%Y'))
                for currency in currencies:
                    for purchase in purchases:
                        if purchase.date.strftime('%Y') == day.strftime('%Y') and purchase.buyer == current_user and purchase.currency == currency:
                            amount += purchase.amount * currency.rate
                values.append(int(amount))
        if values:
            maximum = max(values) * 1.25
        else:
            maximum = 10
    return render_template("portfolio.html", labels=labels, values=values, form=form, chart=chart, max=maximum)

"""
        if form.time.data == '7' or form.time.data == '30':
            days = pd.date_range(end = datetime.today(), periods = period).to_pydatetime().tolist()
            for day in days:
                id.append(day.strftime('%d %B'))
                for exercise in exercises:
                    for schedule in schedules:
                        if schedule.workout.date.strftime('%Y-%m-%d') == day.strftime('%Y-%m-%d') and schedule.workout.athlete == current_user and schedule.exercise == exercise:
                            if form.type.data == '2':
                                time += schedule.duration * schedule.exercise.kilocalories
                            else:
                                time += schedule.duration
                duration.append(int(time))
                time = 0
        elif form.time.data == '12' or form.time.data == '24':
            days = pd.date_range(end = datetime.today(), periods = period, freq='M').to_pydatetime().tolist()
            for day in days:
                id.append(day.strftime('%B %Y'))
                for exercise in exercises:
                    for schedule in schedules:
                        if schedule.workout.date.strftime('%Y-%m') == day.strftime('%Y-%m') and schedule.workout.athlete == current_user and schedule.exercise == exercise:
                            if form.type.data == '2':
                                time += schedule.duration * schedule.exercise.kilocalories
                            else:
                                time += schedule.duration
                duration.append(int(time))
                time = 0 
        elif form.time.data == '1':  
            start = Workout.query.filter_by(athlete=current_user).order_by(Workout.date).first()
            if start == None:
                start = datetime.now() - timedelta(days=1095)
            else:
                start = start.date        
            days = pd.date_range(start=start,end=datetime.today(), freq='A').to_pydatetime().tolist()
            for day in days:
                id.append(day.strftime('%Y'))
                for exercise in exercises:
                    for schedule in schedules:
                        if schedule.workout.date.strftime('%Y') == day.strftime('%Y') and schedule.workout.athlete == current_user and schedule.exercise == exercise:
                            if form.type.data == '2':
                                time += schedule.duration * schedule.exercise.kilocalories
                            else:
                                time += schedule.duration
                duration.append(int(time))
                time = 0
        maximum = max(duration) + 10
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
