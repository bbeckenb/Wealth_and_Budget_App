"""Wealth and Budgeting application."""

from flask import Flask, jsonify, redirect, render_template, flash, session, g
from flask import request
from flask_debugtoolbar import DebugToolbarExtension
import os
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
import plaid
from plaid.model.products import Products
from plaid.api import plaid_api
import base64
import datetime
import json
import time
# from forms import # Forms
from models import db, connect_db, User, UserFinancialInstitute, Account
from dotenv import load_dotenv
load_dotenv()

CURR_USER_KEY = "curr_user"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///wealth_and_budget_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

connect_db(app)
db.create_all()

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET') 
PLAID_ENV = os.getenv('PLAID_ENV')
PLAID_PRODUCTS = os.getenv('PLAID_PRODUCTS', 'transactions').split(',')
PLAID_COUNTRY_CODES = os.getenv('PLAID_COUNTRY_CODES', 'US').split(',')
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
debug = DebugToolbarExtension(app)
host = plaid.Environment.Development

# To call an endpoint you must create a PlaidApi object.
configuration = plaid.Configuration(
    host=host,
    api_key={
        'clientId': PLAID_CLIENT_ID,
        'secret': PLAID_SECRET,
        'plaidVersion': '2020-09-14'
    }
)

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

products = []
for product in PLAID_PRODUCTS:
    products.append(Products(product))

access_token = None
item_id = None

##############################################################################
# User signup/login/logout

@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]

#Example View Functions
@app.route('/')
def homepage():
    if g.user:
        return render_template('')
    return render_template('test_home.html')

@app.route('/create_link_token', methods=['POST'])
def create_link_token():
    try:
        request = LinkTokenCreateRequest(
            products=products,
            client_name="W_and_B_app",
            country_codes=list(map(lambda x: CountryCode(x), PLAID_COUNTRY_CODES)),
            language='en',
            user=LinkTokenCreateRequestUser(
                client_user_id=str(time.time())
            )
        )

        # create link token
        response = client.link_token_create(request)
        return jsonify(response.to_dict())
    except plaid.ApiException as e:
        return json.loads(e.body)

@app.route('/exchange_public_token', methods=['POST'])
def exchange_public_token():
    global access_token
    public_token = request.form['public_token']
    req = ItemPublicTokenExchangeRequest(
      public_token=public_token
    )
    response = client.item_public_token_exchange(req)
    access_token = response['access_token']
    item_id = response['item_id']
    print(response)
    return jsonify(response.to_dict())
# @app.route('/users')
# def users_list():
#     """renders list of users"""
#     users = User.query.order_by(User.last_name, User.first_name).all()
#     return render_template('home.html', users=users)

# @app.route('/users/new', methods=['GET'])
# def create_new_user_landing_page():
#     """landing page for form to create a new user"""

#     return render_template('new_user_form.html')

# @app.route('/users/new', methods=['POST'])
# def create_user():
#     """pulls in client info, creates a new user in the database, displays all users on main user list"""
#     first_name = request.form['first_name']
#     last_name = request.form['last_name']
#     image_url = request.form['image_url']

#     left_blank = False
#     if first_name == '':
#         flash('Please enter a first name to create a profile!', 'error')
#         left_blank = True
#     if last_name == '':
#         left_blank = True
#         flash('Please enter a last name to create a profile!', 'error')
#     if image_url == '':
#         image_url = None
#     if left_blank:
#         return render_template('new_user_form.html')
#     else:
#         new_user = User(first_name=first_name, last_name=last_name, image_url=image_url)
#         db.session.add(new_user)
#         db.session.commit()
#         return redirect('/users')

# @app.route('/users/<int:user_id>', methods=['GET'])
# def show_user(user_id):
#     """shows details about a user"""
#     user = User.query.get_or_404(user_id)
#     posts = Post.query.filter(Post.creator_id == int(user_id))

#     return render_template("details.html", user=user, posts=posts)

# @app.route('/users/<int:user_id>/edit', methods=['GET'])
# def edit_user(user_id):
#     """Gives option to change user attributes or cancel editing"""
#     user = User.query.get_or_404(user_id)

#     return render_template("edit_user.html", user=user)

# @app.route('/users/<int:user_id>/edit', methods=['POST'])
# def commit_edits(user_id):
#     """Pushes desired edits to database then sends updates to client side"""
#     user = User.query.get_or_404(user_id)
#     first_name = request.form['first_name']
#     last_name = request.form['last_name']
#     image_url = request.form['image_url']
#     if image_url != '':
#         user.image_url = image_url
#     if first_name != '':
#         user.first_name = first_name
#     if last_name != '':
#         user.last_name = last_name
    
#     db.session.add(user)
#     db.session.commit()
#     return redirect(f'/users/{user.id}')

# @app.route('/users/<int:user_id>/delete', methods=['POST'])
# def commit_user_delete(user_id):
#     """Pushes desired edits to database then sends updates to client side"""
    
#     user = User.query.get_or_404(user_id)
#     db.session.delete(user)
#     db.session.commit()
    
#     return redirect('/users')