
from unicodedata import category
from flask import Blueprint, render_template, flash, redirect, url_for, request, abort
from flask_login import login_required, current_user
from website.forms import AccountUpdateForm, WorkoutForm, AddCategoryForm, FilterPostForm
from website import db, app
from .models import Post, User, Category
import secrets
from PIL import Image
import os


views = Blueprint('views',__name__)


@views.route('/')
@views.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    posts = Post.query.all()
    categories = Category.query
    form = FilterPostForm()
    form.category.choices = categories
    if form.validate_on_submit():
        category = Category.query.filter_by(term=form.category.data).first()
        flash('You Have Filtered Your Feed!', 'success')
        return redirect(url_for('views.filter', category=category))
    return render_template("home.html", posts=posts, form=form)

@views.route('/home/filter=<category>')
@login_required
def filter(category):
    posts = Post.query.all()
    return render_template("filter.html", posts=posts, category=category)

@views.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    categories = Category.query.all()
    form = WorkoutForm()
    form.category.choices = categories
    if form.validate_on_submit():
        category = Category.query.filter_by(term=form.category.data).first()
        post = Post(title=form.title.data, content=form.content.data, overname=category, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Post has been created!', 'success')
        return redirect(url_for('views.accounts', username=current_user.username))
    return render_template("add.html", form=form, legend='New Post')

@views.route('/post/<int:post_id>')
@login_required
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template("post.html", post=post)

@views.route('/post/<int:post_id>/update', methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    categories = Category.query.all()
    form = WorkoutForm()
    form.category.choices = categories
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.overname = form.category.object_data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('views.post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template("add.html", form=form, legend='Update Post')


@views.route('/history')
@login_required
def history():
    posts = Post.query.all()
    return render_template("history.html", posts=posts)


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_filename = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pictures', picture_filename)
    #Resizing the image
    output_size = (300, 500)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    
    return picture_filename
#Methode schreiben zum löschen der alten Bilder, wenn das Bild geändert wird

@views.route('/account/<username>/update', methods=['GET', 'POST'])
@login_required
def update_account(username):
    if username != current_user.username:
        abort(403)
    form = AccountUpdateForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.bio = form.bio.data
        db.session.commit()
        flash('Your account information has been changed!', 'success')
        return redirect(url_for('views.accounts', username=current_user.username))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.bio.data = current_user.bio
    image = url_for('static', filename='profile_pictures/' + current_user.image)
    return render_template("update_account.html", image=image, form=form)

@views.route('/account/<username>', methods=['GET'])
@login_required
def accounts(username):
    user = User.query.filter_by(username = username).first()
    if user:
        image = url_for('static', filename='profile_pictures/' + user.image)
        posts = Post.query.all()
    else:
        abort(404)
    return render_template("accounts.html", user=user, image=image, posts=posts)

"""
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