##############################################################################
# Imports
from controllers.User_controller import UserController
from controllers.BudgetTracker_controller import BudgetTrackerController
from controllers.Plaid_controller import PlaidController
from controllers.WebAppInfo import WebAppInfoController
from controllers_api.UFI_controller_api import UFIControllerAPI
from controllers_api.Account_controller_api import AccountControllerAPI
from controllers_api.BudgetTracker_controller_api import BudgetTrackerControllerAPI
from database.database import connect_db
from dotenv import load_dotenv
from flask import Flask
import os
import logging, logging.config
import yaml
##############################################################################
# Configurations
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgres:///wealth_and_budget_db').replace("://", "ql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.getenv('SECRET_KEY'))
##############################################################################
# Initializations
load_dotenv()
connect_db(app)
logging.config.dictConfig(yaml.load(open('logging.conf'), Loader=yaml.FullLoader))
##############################################################################
# User
@app.before_request
def add_user_to_g():
    UserController.add_global_user_to_session()

@app.route('/')
def homepage():
    return UserController.render_homepage()

@app.route('/signup', methods=['GET', 'POST'])
def user_new_signup():
    return UserController.signup_user()

@app.route('/login', methods=["GET", "POST"])
def login():
    return UserController.login_user()

@app.route('/logout')
def logout():
    return UserController.logout_user()

@app.route('/users/update-profile', methods=["GET", "POST"])
def update_profile():
    return UserController.update_user_profile()

@app.route('/users/delete', methods=["POST"])
def delete_user():
    return UserController.delete_user_profile()
##############################################################################
# Plaid
@app.route('/create_link_token', methods=['POST'])
def create_link_token():
    return PlaidController.token_gen()
##############################################################################
# UFI
@app.route('/financial-institutions', methods=['POST'])
def exchange_public_token(): 
    return UFIControllerAPI.get_plaid_access_key_create_UFI()

@app.route('/financial-institutions/<int:UFI_id>', methods=['DELETE'])
def UFI_delete(UFI_id):
    return UFIControllerAPI.delete_UFI_instance(UFI_id)

@app.route('/financial-institutions/<int:UFI_id>', methods=['PATCH'])
def update_UFI_accounts_on_page(UFI_id):
    return UFIControllerAPI.update_UFI_Accounts(UFI_id)
##############################################################################
# Accounts
@app.route('/financial-institutions/<int:UFI_id>/accounts', methods=['POST'])
def populate_accounts_of_UFI(UFI_id):
    return AccountControllerAPI.populate_accounts_of_UFI(UFI_id)

@app.route('/accounts/<int:acct_id>', methods=['DELETE'])
def delete_account(acct_id):
    return AccountControllerAPI.delete_specified_account(acct_id)
##############################################################################
# BudgetTracker
@app.route('/accounts/<int:acct_id>/budget-tracker/create', methods=['GET', 'POST'])
def create_budget_tracker(acct_id):
    print(acct_id)
    return BudgetTrackerController.create_new_budget_tracker(acct_id)

@app.route('/accounts/<int:acct_id>/budget-tracker/update', methods=['GET', 'POST'])
def update_budget_tracker(acct_id):
    return BudgetTrackerController.update_existing_budget_tracker(acct_id)

@app.route('/accounts/<int:acct_id>/budget-tracker', methods=['DELETE'])
def delete_budget_tracker(acct_id):
    return BudgetTrackerControllerAPI.delete_specified_budget_tracker(acct_id)

##############################################################################
# WebApp Information
@app.route('/about')
def render_about_page():
    return WebAppInfoController.render_about_page()

# @app.route('/about')
# def render_about_page():
#     return WebAppInfoController.render_dashboard()