from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, FloatField, DateField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange
from flask_login import current_user
from .models import User

#Erstellen der Formulare

#Account
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=5)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    #Überprüfung und Weitergabe des Erros wenn der Username und/oder die Email schon vergeben ist
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already taken.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class AccountUpdateForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    picture = FileField('Change Profile Picture', validators=[FileAllowed(['jpg','png'])])
    submit = SubmitField('Change Settings')

    #Überprüfung und Weitergabe des Erros wenn der Username und/oder die Email schon vergeben ist
    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Username already taken.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Email already taken.')


class CurrencyConvertForm(FlaskForm):
    input = SelectField('From', validators=[DataRequired()])
    output = SelectField('To', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    submit = SubmitField('Convert')

class PurchaseForm(FlaskForm):
    type = SelectField('Type', choices=[('Buy'),('Sell')])
    currency = SelectField('Currency', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=1)])
    date = DateField('Date', validators=[DataRequired()])
    submit = SubmitField('Submit')

class DeleteForm(FlaskForm):
    submit = SubmitField('Delete')

class PortfolioForm(FlaskForm):
    currency = SelectField('', choices=[('All')])
    time = SelectField('', choices=[('7','1 Week'),('30','1 Month'),('12','1 Year'),('24','2 Years'),('1','Max')])
    submit = SubmitField('Submit')