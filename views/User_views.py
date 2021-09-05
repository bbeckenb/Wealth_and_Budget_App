from flask import render_template, flash, g, redirect, session
from models import User, db
from forms import SignUpUserForm, LoginForm, UpdateUserForm
from sqlalchemy.exc import IntegrityError

CURR_USER_KEY = "curr_user"

def do_login(user):
    """Log in user."""
    session[CURR_USER_KEY] = user.id

def do_logout():
    """Logout user."""
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]

def add_global_user_to_session():
    """If we're logged in, add curr user to Flask global."""
    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])
    else:
        g.user = None

def render_homepage():
    """If user is not logged in, gives them options to sign up or log in"""
    if g.user:         
        return render_template('user_home.html')
    return render_template('no_user_home.html')

def signup_user():
    """Displays form for a new user to enter their information
        -If a user is in session and tries to access the page, it sends them to home
        -If a user does not enter all required information, it recycles the form with proper error messages
        -If a user does enter required information but the username they want is taken, it recycles the form with proper error messages
        -If a user does enter required information, it enters a new user into the database and sends a user to their dashboard
    """
    if g.user:
        flash("Active account already logged in rerouted to home", 'danger')
        return redirect('/')
    form = SignUpUserForm()
    if form.validate_on_submit():
        try:
            new_user = User.signup(
                username=form.username.data,
                password=form.password.data,
                phone_number=form.phone_number.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data
            )
            db.session.commit()
        except:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form) 
        do_login(new_user)
        return redirect('/')
    else:
        return render_template('users/signup.html', form=form) 

def login_user():
    """Handle user login. Makes sure if an existing user is not in the session and logs in
        -It successfully adds their info and displays it on home
        -it loads the user into the session
        -Makes sure if a user is in the session and tries to go to login, it redirects home"""
    if g.user:
        flash("Active account already logged in rerouted to home", 'danger')
        return redirect('/')
    form = LoginForm()
    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)
        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")
        flash("Invalid credentials.", 'danger')
    return render_template('users/login.html', form=form)

def logout_user():
    """Handle logout of user. Makes sure if a user is in session, and they logout:
    -they are redirected home with options to sign up or login
    -their user instance is taken out of the session
    -if no user is in ession and they manually attempt to hit /logout
    they are redirected to home with a warning message"""
    if CURR_USER_KEY not in session:
        flash("No user in session", 'danger')
        return redirect('/')
    flash(f"Goodbye, {g.user.username}!", "success")
    do_logout()
    return redirect('/')

def update_user_profile():
    """Update profile for current user.
    -If no user present, reroute home with warning
    -If desired username is taken, recycle form, notify user
    -If password to authorize changes is incorrect, recycle form, notify user
    -If all criteria above satisfied, make desired changes to user, update database, redirect home
    """
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    form = UpdateUserForm(obj=g.user)
    if form.validate_on_submit():
        if User.authenticate(g.user.username, form.password.data):
            try:
                g.user.username = form.username.data or g.user.username
                g.user.phone_number = form.phone_number.data or g.user.phone_number
                g.user.first_name = form.first_name.data or g.user.first_name
                g.user.last_name = form.last_name.data or g.user.last_name
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Username already taken", 'danger')
                return render_template('users/update.html', form=form)   
            flash("Profile successfully updated!", "success")
            return redirect('/')
        else:
            flash("Incorrect password", 'danger')
    return render_template('users/update.html', form=form)

def delete_user_profile():
    """Delete user."""
    if not g.user:
        flash("Access unauthorized.", "danger")
    else:
        user = User.query.get(g.user.id)
        do_logout()
        db.session.delete(user)
        db.session.commit()  
    return redirect("/")