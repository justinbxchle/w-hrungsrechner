from flask import Blueprint, render_template, flash, redirect, url_for, request, abort
from flask_login import login_required, current_user
from website.forms import AccountUpdateForm, CurrencyConvertForm, PurchaseForm, DeleteForm, PortfolioForm
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

#Homepage
@views.route('/', methods=['GET', 'POST'])
@views.route('/home', methods=['GET','POST'])
@login_required
def home():
    currencies = Currency.query.all()
    return render_template('home.html', currencies=currencies)

#Währungsrechner
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
            #Wenn Inputwährung und Outputwährung gleich sind wird ein Fehler zurück gegeben
            if input == output:
                flash('Choose Two Different Currencies!', 'danger')
                return redirect(url_for('views.converter'))
            #Der Aktuelle Währungskurs wird mithilfe von Yahoo Finance bezogen
            ticker = str(input.identifier + output.identifier + "=X")
            rate = yf.Ticker(ticker).info['regularMarketPrice']
            value = form.amount.data * rate
        except:
            #Wenn keine Verbindung oder das Währungspaar nicht unterstützt werden wird ein Error ausgegeben
            flash('Either Yahoo Finance Does Not Support This Exchange Rate Or No Connection Could Be Established!', 'danger')
            return redirect(url_for('views.converter'))
    return render_template("converter.html", user=user, form=form, rate=rate, Currency=Currency, value=value, legend="Currency Converter")

#Aktivitäten - Devisen Kauf/Verkauf
@views.route('/activity', methods=['GET', 'POST'])
@login_required
def activity():
    currencies = Currency.query.all()
    form = PurchaseForm()
    form.currency.choices = currencies
    if form.validate_on_submit():
        currency = Currency.query.filter_by(name=form.currency.data).first()
        #Wenn Devisen Verkauft werden, wird sichergestellt das zu diesem Zeitpunkt genügend Geld vorhanden ist/war
        if form.type.data == 'Sell':
            days = pd.date_range(end = datetime.today(), start = form.date.data.strftime('%Y-%m-%d')).to_pydatetime().tolist()
            for day in days:
                if float(form.amount.data) > Purchase.query.with_entities(func.sum(Purchase.amount)).filter(Purchase.user_id==current_user.id,Purchase.currency_id==currency.id,Purchase.date <= day.strftime('%Y-%m-%d')).scalar():
                    flash('Amount Exceeds Your Deposit Value!', 'danger')
                    return redirect(url_for('views.activity'))
            form.amount.data = form.amount.data * -1
        #Wenn kein Error entsteht wird der neue Kauf/Verkauf in die Datenbank eingespeichert
        purchase = Purchase(date=form.date.data, amount=form.amount.data, buyer=current_user, currency=currency, type=form.type.data)
        db.session.add(purchase)
        db.session.commit()
        flash('Purchase has been added!', 'success')
        return redirect(url_for('views.account'))
    return render_template("activity.html", form=form, legend='New Activity')

#Update von Kauf/Verkauf
@views.route('/purchase/update/<int:purchase_id>', methods=['GET', 'POST'])
@login_required
def update_purchase(purchase_id):
    currencies = Currency.query.all()
    form = PurchaseForm()
    form.currency.choices = currencies
    #Wenn der gesuchte Kauf nicht vorhanden ist, wird ein 404 Fehler ausgegeben
    purchase = Purchase.query.get_or_404(purchase_id)
    #Wenn ein anderer außer der Käufer zugreifen will, wird ein 403 Fehler ausgegeben
    if purchase.buyer != current_user:
        abort(403)
    if form.validate_on_submit():
        currency = Currency.query.filter_by(name=form.currency.data).first()
        #Wenn Devisen Verkauft werden, wird sichergestellt das zu diesem Zeitpunkt genügend Geld vorhanden ist/war
        if form.type.data == 'Sell':
            days = pd.date_range(end = datetime.today(), start = form.date.data.strftime('%Y-%m-%d')).to_pydatetime().tolist()
            for day in days:
                if purchase.amount+float(form.amount.data) > Purchase.query.with_entities(func.sum(Purchase.amount)).filter(Purchase.user_id==current_user.id,Purchase.currency_id==currency.id,Purchase.date <= day.strftime('%Y-%m-%d')).scalar():
                    flash('Amount Exceeds Your Deposit Value!', 'danger')
                    return redirect(url_for('views.update_purchase', purchase_id=purchase.id))
            form.amount.data = form.amount.data * -1
        #Wenn kein Error entsteht wird der neue Kauf/Verkauf in die Datenbank eingespeichert
        purchase.date = form.date.data
        purchase.amount = form.amount.data
        purchase.currency = currency
        db.session.commit()
        flash('Purchase has been updated!', 'success')
        return redirect(url_for('views.account'))
    #Damit die Änderung besser vorgenommen werden kann werden die bisherigen Daten an das Formular weitergegeben
    elif request.method == 'GET':
        form.type.data = purchase.type
        form.date.data = purchase.date
        form.amount.data = abs(purchase.amount)
        form.currency.data = purchase.currency.name
    return render_template("activity.html", form=form, legend='Update Activity')

#Löschen eines Kaufs/Verkaufs
@views.route('/purchase/delete/<int:purchase_id>', methods=['GET','POST'])
@login_required
def delete_purchase(purchase_id):
    purchases = Purchase.query.all()
    #Wenn der gesuchte Kauf nicht vorhanden ist, wird ein 404 Fehler ausgegeben
    purchase = Purchase.query.get_or_404(purchase_id)
    #Wenn ein anderer außer der Käufer zugreifen will, wird ein 403 Fehler ausgegeben
    if purchase.buyer != current_user:
        abort(403)
    form = DeleteForm()
    #Wenn das Formular gesendet wird, wird der ausgewählte Kauf aus der Datenbank gelöscht
    if form.validate_on_submit():
        db.session.delete(purchase)
        db.session.commit()
        flash('Purchase has been deleted!', 'success')
        return redirect(url_for('views.account', purchases=purchases))
    return render_template('delete.html', purchase=purchase, form=form, purchases=purchases)

#Methode zur Speicherung von Profilbildern
def save_picture(form_picture, old_pic):
    #Ein zufälliger Hex mit 8 Bytes wird generiert
    random_hex = secrets.token_hex(8)
    #Mit der Methode splitext wird der Dateiname ohne Endung und die Dateiendung selbst zurückgegeben
    _, f_ext = os.path.splitext(form_picture.filename)
    #Der neue Dateiname wird zusammengesetzt
    picture_filename = random_hex + f_ext
    #Der volle Dateipfad, indem die Datei gespeichert werden soll, wird hier ermittelt
    picture_path = os.path.join(app.root_path, 'static/profile_pictures', picture_filename)
    #Alte Datei wird gelöscht, außer es handelt sich um das Standartbild
    if old_pic != 'default.jpg':
        os.remove(os.path.join(app.root_path, 'static/profile_pictures', old_pic))
    #Die Bildgröße wird angepasst
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_filename
#Methode schreiben zum löschen der alten Bilder, wenn das Bild geändert wird

#Account
@views.route('/account', methods=['GET'])
@login_required
def account():
    purchases = Purchase.query.order_by(Purchase.date).all()
    return render_template("account.html", purchases=purchases)

#Update Account
@views.route('/account/update', methods=['GET', 'POST'])
@login_required
def update_account():
    form = AccountUpdateForm()
    #Wenn das Formular gesendet wird, werden die Account Daten ausgetauscht und in die Datenbank gespeichert
    if form.validate_on_submit():
        #Wenn ein neues Bild gespeichert werden soll, wird das alte gelöscht und das neue eingespeichert
        if form.picture.data:
            picture_file = save_picture(form.picture.data, current_user.image)
            current_user.image = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account information has been changed!', 'success')
        return redirect(url_for('views.account'))
    #Damit die Änderung besser vorgenommen werden kann werden die bisherigen Daten an das Formular weitergegeben
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template("update_account.html", form=form)

#Dashboard bzw Übersicht
@views.route('/dashboard')
@login_required
def dashboard():
    purchases = Purchase.query.order_by(Purchase.date).all()
    currencies = Currency.query.all()
    return render_template("dashboard.html", purchases=purchases, datetime=datetime, currencies=currencies, Purchase=Purchase, func=func)

#Portfolio Visualisierung
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
    #Hinzufügen aller Währungen in das Dropdown Menü des Formulars
    for currency in currencies:
        form.currency.choices.append(currency)
    if form.validate_on_submit():
        chart = True
        period = int(form.time.data)
        #Wenn die Auswahl "Alle Übungen" nicht gewählt wurde, wird nur duch die Übung gelooped, die ausgewählt wurde
        if form.currency.data != 'All':
            currencies = Currency.query.filter_by(name=form.currency.data)
        #Wenn der Zeitraum auf 1 Woche bzw 1 Monat beschränkt wird, wird dieser Codeteil ausgeführt
        if period == 7 or period == 30:
            #Die Tage in dem ausgewählten Zeitraum werden ermittelt
            days = pd.date_range(end = datetime.today(), periods = period).to_pydatetime().tolist()
            #Die Käufe/Verkäufe, die vor dem Zeitraum liegen werden aufsummiert
            beginn = Purchase.query.filter(Purchase.date < days[0].strftime('%Y-%m-%d')).all()
            for currency in currencies:
                for purchase in beginn:
                    if purchase.currency == currency and purchase.buyer == current_user:
                        amount += purchase.amount * purchase.currency.rate
            #Die Käufe/Verkäufe in dem Zeitraum werden aufsummiert
            #Die Werte der x und y Achse werden gespeichert
            for day in days:
                labels.append(day.strftime('%d %B'))
                for currency in currencies:
                    for purchase in purchases:
                        if purchase.date.strftime('%Y-%m-%d') == day.strftime('%Y-%m-%d') and purchase.buyer == current_user and purchase.currency == currency:    
                            amount += purchase.amount * purchase.currency.rate
                values.append(int(amount))
        #Wenn der Zeitraum auf 1 Jahr bzw 2 Jahre beschränkt wird, wird dieser Codeteil ausgeführt
        elif period == 12 or period == 24:
            #Die Tage in dem ausgewählten Zeitraum werden ermittelt
            days = pd.date_range(end = datetime.today(), periods = period, freq='M').to_pydatetime().tolist()
            #Die Käufe/Verkäufe, die vor dem Zeitraum liegen werden aufsummiert
            beginn = Purchase.query.filter(Purchase.date < days[0].strftime('%Y-%m-%d')).all()
            for currency in currencies:
                for purchase in beginn:
                    if purchase.currency == currency and purchase.buyer == current_user:
                        amount += purchase.amount * purchase.currency.rate
            #Die Käufe/Verkäufe in dem Zeitraum werden aufsummiert
            #Die Werte der x und y Achse werden gespeichert
            for day in days:
                labels.append(day.strftime('%B %Y'))
                for currency in currencies:
                    for purchase in purchases:
                        if purchase.date.strftime('%Y-%m') == day.strftime('%Y-%m') and purchase.buyer == current_user and purchase.currency == currency:
                            amount += purchase.amount * purchase.currency.rate
                values.append(int(amount))
        #Wenn der Zeitraum nicht beschränkt wird, wird dieser Codeteil ausgeführt
        elif period == 1:
            #Das Datum des ersten Kaufs wird ermittelt
            start = Purchase.query.filter_by(user_id=current_user.id).order_by(Purchase.date).first()
            #Wenn es noch kein Kauf gibt oder dieser im selben Jahr liegt, wird ein Zeitraum von 3 Jahren gewählt
            if start == None or start.date.year == datetime.now().year:
                start = datetime.now() - timedelta(days=1095)
            else:
                start = start.date  
            days = pd.date_range(start=start,end=datetime.today(), freq='A').to_pydatetime().tolist()
            #Die Käufe/Verkäufe in dem Zeitraum werden aufsummiert
            #Die Werte der x und y Achse werden gespeichert
            for day in days:
                labels.append(day.strftime('%Y'))
                for currency in currencies:
                    for purchase in purchases:
                        if purchase.date.strftime('%Y') == day.strftime('%Y') and purchase.buyer == current_user and purchase.currency == currency:
                            amount += purchase.amount * currency.rate
                values.append(int(amount))
        #Das Maximum der y-Achse wird ermittelt   
        if values:
            maximum = max(values) * 1.25
        else:
            maximum = 10
    return render_template("portfolio.html", labels=labels, values=values, form=form, chart=chart, max=maximum)

#Methode zum Updaten der Währungskurse 
def UpdateRate():
    currencies = Currency.query.all()
    for currency in currencies:
        rate = yf.Ticker(currency.identifier + 'USD=X').info['regularMarketPrice']
        currency.rate = rate
        db.session.commit()

#Ausführen der Methode "UpdateRate" jede 10 Minuten
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(func=UpdateRate, trigger="interval", minutes=10)
scheduler.start()
