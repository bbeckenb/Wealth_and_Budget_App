##############################################################################
# Imports
from views.User_views import UserController
from views.BudgetTracker_views import BudgetTrackerController
from views.UFI_views import UFIController
from views.Account_views import AccountController
from views.Plaid_views import PlaidController
from database.database import connect_db
from dotenv import load_dotenv
from flask import Flask
import os
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
@app.route('/exchange_public_token', methods=['POST'])
def exchange_public_token(): 
    return UFIController.get_plaid_access_key_create_UFI()

@app.route('/financial-institutions/<int:UFI_id>/delete', methods=['POST'])
def UFI_delete(UFI_id):
    return UFIController.delete_UFI_instance(UFI_id)

@app.route('/financial-institutions/<int:UFI_id>/accounts/update')
def update_UFI_accounts_on_page(UFI_id):
    return UFIController.update_UFI_Accounts(UFI_id)
##############################################################################
# Accounts
@app.route('/accounts/<int:acct_id>/delete', methods=['POST'])
def delete_account(acct_id):
    return AccountController.delete_specified_account(acct_id)
##############################################################################
# BudgetTracker
@app.route('/accounts/<int:acct_id>/budget-tracker/create', methods=['GET', 'POST'])
def create_budget_tracker(acct_id):
    print(acct_id)
    return BudgetTrackerController.create_new_budget_tracker(acct_id)

@app.route('/accounts/<int:acct_id>/budget-tracker/update', methods=['GET', 'POST'])
def update_budget_tracker(acct_id):
    return BudgetTrackerController.update_existing_budget_tracker(acct_id)

@app.route('/accounts/<int:acct_id>/budget-tracker/delete', methods=['POST'])
def delete_budget_tracker(acct_id):
    return BudgetTrackerController.delete_specified_budget_tracker(acct_id)