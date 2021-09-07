##############################################################################
# Imports
from views.User_views import render_homepage, add_global_user_to_session, signup_user, login_user, logout_user, update_user_profile, delete_user_profile
from views.BudgetTracker_views import create_new_budget_tracker, update_existing_budget_tracker, delete_specified_budget_tracker
from views.UFI_views import get_plaid_access_key_create_UFI, delete_UFI_instance, update_UFI_Accounts
from views.Account_views import delete_specified_account
from models import connect_db, MyPlaid, MyTwilio
from flask_crontab import Crontab
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
crontab = Crontab(app)
plaid_inst = MyPlaid('sandbox')
twilio_inst = MyTwilio()
##############################################################################
# User
@app.before_request
def add_user_to_g():
    add_global_user_to_session()

@app.route('/')
def homepage():
    return render_homepage()

@app.route('/signup', methods=['GET', 'POST'])
def user_new_signup():
    return signup_user()

@app.route('/login', methods=["GET", "POST"])
def login():
    return login_user()

@app.route('/logout')
def logout():
    return logout_user()

@app.route('/users/update-profile', methods=["GET", "POST"])
def update_profile():
    return update_user_profile()

@app.route('/users/delete', methods=["POST"])
def delete_user():
    return delete_user_profile()
##############################################################################
# Plaid
@app.route('/create_link_token', methods=['POST'])
def create_link_token():
    return plaid_inst.create_plaid_link_token()
##############################################################################
# UFI
@app.route('/exchange_public_token', methods=['POST'])
def exchange_public_token(): 
    return get_plaid_access_key_create_UFI(plaid_inst)

@app.route('/financial-institutions/<int:UFI_id>/delete', methods=['POST'])
def UFI_delete(UFI_id):
    return delete_UFI_instance(UFI_id, plaid_inst)

@app.route('/financial-institutions/<int:UFI_id>/accounts/update')
def update_UFI_accounts_on_page(UFI_id):
    return update_UFI_Accounts(UFI_id, plaid_inst)
##############################################################################
# Accounts CRUD and functions
@app.route('/accounts/<int:acct_id>/delete', methods=['POST'])
def delete_account(acct_id):
    return delete_specified_account(acct_id)
##############################################################################
# BudgetTracker CRUD and functions
@app.route('/accounts/<int:acct_id>/budget-tracker/create', methods=['GET', 'POST'])
def create_budget_tracker(acct_id):
    return create_new_budget_tracker(acct_id, plaid_inst)

@app.route('/accounts/<int:acct_id>/budget-tracker/update', methods=['GET', 'POST'])
def update_budget_tracker(acct_id):
    return update_existing_budget_tracker(acct_id)

@app.route('/accounts/<int:acct_id>/budget-tracker/delete', methods=['POST'])
def delete_budget_tracker(acct_id):
    return delete_specified_budget_tracker(acct_id)
##############################################################################
# CRON Scheduled Jobs For local server
# run 'flask crontab add' to initialize
# run 'flask crontab remove' to remove
# 'crontab -l' to see list of jobs
# 'crontab -e' to manually edit list of jobs, 'esc' :wq 'enter' to leave list
# This will run everyday at 12pm UTC
# @crontab.job(minute=0, hour=12)
# def scheduled_jobs():
#     scheduled_daily_refresh_all_accounts(plaid_inst)
#     scheduled_budget_tracker_jobs(plaid_inst, twilio_inst)