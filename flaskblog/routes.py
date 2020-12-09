import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from flaskblog import app, db, bcrypt, mail
from flaskblog.forms import (RegistrationForm, LoginForm, UpdateAccountForm,
                             PostForm, RequestResetForm, ResetPasswordForm,CommentForm)
from flaskblog.models import User, Post,Comment,Like
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message


@app.route("/")
@app.route("/home")
def home():
    form = CommentForm()
    page = request.args.get('page', 1, type=int)
    
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    comment =[]
    if current_user.is_authenticated:
        y=[]
        d={}
        for p in posts.items:
            
            comment.append(Comment.query.filter_by(post_id=p.id).order_by(Comment.date_posted.desc()).limit(2).all()) 

            if(Like.query.filter_by(post_id=p.id, user_id=current_user.username).first()!=None):
                y.append(p.id)
            else:
                y.append(None)
            
            count=Like.query.filter_by(post_id=p.id).count()
            if count>0:
                d[p.id]=count
        return render_template('home.html', posts=posts,form=form,comments=comment,y=y,d=d)
    return  render_template('home.html')


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)


def picture(form_post_picture):
    random_hex = secrets.token_hex(25)
    _, f_ext = os.path.splitext(form_post_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/posts', picture_fn)

    output_size = (700, 700)
    j = Image.open(form_post_picture)
    j.thumbnail(output_size)
    j.save(picture_path)

    return picture_fn


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    
    if form.validate_on_submit():
        if form.post_picture.data:
            picture_file = picture(form.post_picture.data)
        else:
            picture_file = None 
        
        post = Post(title=form.title.data, content=form.content.data, author=current_user, image_file= picture_file)
        db.session.add(post)
        db.session.commit()
        
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post',
                           form=form, legend='New Post')


@app.route("/post/<int:post_id>")
def post(post_id):
    form = CommentForm()
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.order_by(Comment.date_posted.desc())
    return render_template('post.html', title=post.title, post=post,comments=comments,form=form)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'warning')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('update_post.html', title='Update Post',
                           form=form, legend='Update Post')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    comment=(Comment.query.filter_by(post_id=post_id).all()) 
    for com in comment:
        db.session.delete(com)
    like=(Like.query.filter_by(post_id=post_id).all()) 
    for com in like:
        db.session.delete(com)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'danger')
    return redirect(url_for('home'))


@app.route("/user/<string:username>")
def user_posts(username):
    form = CommentForm()
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page, per_page=5)
    comment =[]
    y=[]
    d={}
    for p in posts.items:
        print(p.id)
        comment.append(Comment.query.filter_by(post_id=p.id).order_by(Comment.date_posted.desc()).limit(2).all())
        if(Like.query.filter_by(post_id=p.id, user_id=current_user.username).first()!=None):
                y.append(p.id)
        else:
                y.append(None)
            
        count=Like.query.filter_by(post_id=p.id).count()
        if count>0:
                d[p.id]=count
        return render_template('user_posts.html', posts=posts,user=user,form=form,comments=comment,y=y,d=d)
    

@app.route("/my_posts")
def my_posts():
    form = CommentForm()
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=current_user.username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page, per_page=5)
    comment =[]
    y=[]
    d={}
    for p in posts.items:
        print(p.id)
        comment.append(Comment.query.filter_by(post_id=p.id).order_by(Comment.date_posted.desc()).limit(2).all())
        if(Like.query.filter_by(post_id=p.id, user_id=current_user.username).first()!=None):
                y.append(p.id)
        else:
                y.append(None)
            
        count=Like.query.filter_by(post_id=p.id).count()
        if count>0:
                d[p.id]=count
    return render_template('user_posts.html', posts=posts,user=user,form=form,comments=comment,y=y,d=d)
    


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@demo.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)

@app.errorhandler(404)
def error_404(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(403)
def error_403(error):
    return render_template('errors/403.html'), 403


@app.errorhandler(500)
def error_500(error):
    return render_template('errors/500.html'), 500  


@app.route("/comment/<int:post_id>", methods=['POST','GET'])
@login_required
def comment_post(post_id):
    form = CommentForm()

    comments = Comment( comment=form.comments.data, authorc =current_user, post_id=post_id)
    db.session.add(comments)
    db.session.commit()
    post = Post.query.get_or_404(post_id)
    if post.author.username==current_user.username:
        x='your'
    else:
        x=post.author.username +"'s"
    flash('Commented on '+x+' post', 'success')
    return redirect(request.referrer)

@app.route("/like/<int:post_id>", methods=['POST','GET'])
@login_required
def like_post(post_id):

    post = Post.query.get_or_404(post_id)

    if(Like.query.filter_by(post_id=post_id, user_id=current_user.username).first()!=None):
        like=Like.query.filter_by(post_id=post_id, user_id=current_user.username).first()
        db.session.delete(like)
        if post.author.username==current_user.username:
            x='your'
        else:
            x=post.author.username +"'s"
        flash('You unliked '+x+' post', 'success')
    else:
        like = Like( user_id=current_user.username, post_id=post_id)
        db.session.add(like)
        if post.author.username==current_user.username:
            x='your'
        else:
            x=post.author.username +"'s"
        flash('You liked '+x+' post', 'success')
    db.session.commit()
    
    return redirect(request.referrer)


@app.route("/delete_acc", methods=['GET'])
@login_required
def delete():
    user=(User.query.filter_by(id=current_user.id).first()) 
    post = Post.query.filter_by(author=current_user).all()
    for p in post:
        if p.author != current_user:
            abort(403)
        comment=(Comment.query.filter_by(post_id=p.id).all()) 
        for com in comment:
            db.session.delete(com)
        db.session.delete(p)
    like = (Like.query.filter_by(user_id=current_user.username).all())
    for l in like:
        db.session.delete(l)
    comment=(Comment.query.filter_by(authorc=current_user).all()) 
    for com in comment:
        db.session.delete(com)
    db.session.delete(user)
    db.session.commit()
    flash('Your account deleted!', 'danger')
    return redirect(url_for('logout'))