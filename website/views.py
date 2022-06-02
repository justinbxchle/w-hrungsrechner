
from pydoc import render_doc
from unicodedata import category
from flask import Blueprint, render_template, flash, redirect, url_for, request, abort
from flask_login import login_required, current_user
from website.forms import AccountUpdateForm, PostForm, CommentForm, FilterPostForm, SearchForm
from website import db, app
from .models import Post, User, Category, Comment
import secrets
from PIL import Image
import os


views = Blueprint('views',__name__)

@views.context_processor
def base():
    form = SearchForm()
    return dict(form=form)


@views.route('/', methods=['GET', 'POST'])
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
    form = PostForm()
    form.category.choices = categories
    if form.validate_on_submit():
        category = Category.query.filter_by(term=form.category.data).first()
        post = Post(title=form.title.data, content=form.content.data, overname=category, post_author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Post has been created!', 'success')
        return redirect(url_for('views.accounts', username=current_user.username))
    return render_template("add_post.html", form=form, legend='New Post')

@views.route('/add_comment/<int:post_id>', methods=['GET', 'POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, comment_author=current_user, post=post)
        db.session.add(comment)
        db.session.commit()
        flash('Comment has been created!', 'success')
        return redirect(url_for('views.post', post_id=comment.post_id))
    return render_template("add_comment.html", form=form, post=post, legend="New Comment")

@views.route('/update_comment/<int:comment_id>', methods=['GET', 'POST'])
@login_required
def update_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.comment_author != current_user:
        abort(403)
    post = Post.query.filter_by(id=comment.post_id).first()
    form = CommentForm()
    if form.validate_on_submit():
        comment.content = form.content.data
        db.session.commit()
        flash('Your Comment Has Been Updated!', 'success')
        return redirect(url_for('views.post', post_id=comment.post_id))
    elif request.method == 'GET':
        form.content.data = comment.content
    return render_template("add_comment.html", form=form, post=post, legend="Update Comment")


@views.route('/post/<int:post_id>')
@login_required
def post(post_id):
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post.id)
    return render_template("post.html", post=post, comments=comments)

@views.route('/post/<int:post_id>/update', methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.post_author != current_user:
        abort(403)
    categories = Category.query.all()
    form = PostForm()
    form.category.choices = categories
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        overname = Category.query.filter_by(term=form.category.data).first()
        post.overname = overname
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('views.post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template("add_post.html", form=form, legend='Update Post')


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