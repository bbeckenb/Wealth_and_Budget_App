"""Wealth and Budgeting application."""

from flask import Flask, jsonify, redirect, render_template, flash, session, g
from flask import request
from flask_crontab import Crontab
# from flask_debugtoolbar import DebugToolbarExtension
import os
from twilio.rest import Client as TwilioClient
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.accounts_balance_get_request_options import AccountsBalanceGetRequestOptions
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
import plaid
from plaid.model.products import Products
from plaid.api import plaid_api
import datetime
from datetime import timedelta
import time

import json
import base64
from forms import SignUpUserForm, LoginForm, UpdateUserForm, CreateBudgetTrackerForm, UpdateBudgetTrackerForm
from models import db, connect_db, User, UserFinancialInstitute, Account, BudgetTracker
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
load_dotenv()

CURR_USER_KEY = "curr_user"

app = Flask(__name__)
crontab = Crontab(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///wealth_and_budget_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

connect_db(app)
db.create_all()

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET') # Note in sandbox env currently
PLAID_ENV = os.getenv('PLAID_ENV')
PLAID_PRODUCTS = os.getenv('PLAID_PRODUCTS', 'transactions').split(',')
PLAID_COUNTRY_CODES = os.getenv('PLAID_COUNTRY_CODES', 'US').split(',')
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
# debug = DebugToolbarExtension(app)
host = plaid.Environment.Sandbox #need to change back to Development

##############################################################################
#Plaid Link process functions to get access keys and ids of Items (user's financial institutions)
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
plaid_client = plaid_api.PlaidApi(api_client)

products = []
for product in PLAID_PRODUCTS:
    products.append(Products(product))

access_token = None
item_id = None

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
        response = plaid_client.link_token_create(request)
        return jsonify(response.to_dict())
    except plaid.ApiException as e:
        return json.loads(e.body)

@app.route('/exchange_public_token', methods=['POST'])
def exchange_public_token(): #controller function
    global access_token
    public_token = request.form['public_token']
    req = ItemPublicTokenExchangeRequest(
      public_token=public_token
    )
    response = plaid_client.item_public_token_exchange(req)
    access_token = response['access_token']
    item_id = response['item_id']
    # new_UFI = UserFinancialInstitute()
    print(response)
    """
    {'access_token': 'access-sandbox-55edc404-25ae-46fd-b035-99273b14e944',
    'item_id': 'epkBXEmbMauwGamwQzWoU3N3z99memHLArwr9',
    'request_id': 'rQW08eW2YJ2JMBm'}
    Flow to get to Accts:
        1. /item/get Use client_id, secret, access_token to get institution_id
        2. /institutions/get_by_id Use client_id, secret, institution_id, country_codes (US) WILL give us Name of institution, Logo!!!
        
    """
    name = get_UFI_info()
    new_UFI = UserFinancialInstitute(
                                    name=name, 
                                    user_id=g.user.id,
                                    item_id=item_id,
                                    plaid_access_token=access_token
              )
    db.session.add(new_UFI)
    db.session.commit()
    # new_UFI.populate_UFI_accounts()
    populate_UFI_accounts(new_UFI.id) #EDIT UFI
    return redirect('/') #jsonify(response.to_dict())

##############################################################################
# UFI CRUD and functions

# UFI MODEL
def get_UFI_info():
    """retrieves institution name to create UFI instance (website, logo, and color also a possibility for customization)"""
    item_request = ItemGetRequest(access_token=access_token)
    item_response = plaid_client.item_get(item_request)
    institution_request = InstitutionsGetByIdRequest(
        institution_id=item_response['item']['institution_id'],
        country_codes=list(map(lambda x: CountryCode(x), PLAID_COUNTRY_CODES))
    )
    institution_response = plaid_client.institutions_get_by_id(institution_request)
    print(item_response.to_dict()) #delete
    print(institution_response.to_dict()) #delete
    name = institution_response['institution']['name']
    return name

@app.route('/financial-institutions/<int:UFI_id>/delete', methods=['POST'])
def UFI_delete(UFI_id):
    """Deletes specified instance of UFI from database
        If:
        -no user or wrong user present, redirect home, flash warning
        -UFI_id DNE, 404   
    """
    UFI_to_del = UserFinancialInstitute.query.get_or_404(UFI_id)
    UFI_owner_id = UFI_to_del.user_id

    if not g.user or UFI_owner_id != g.user.id:
        flash("Access unauthorized.", 'danger')
        return redirect('/')
    delete_plaid_UFI_access_key(UFI_to_del.plaid_access_token)
    flash(f"Your connection to {UFI_to_del.name} was removed and the access_token is now invalid", 'success')

    db.session.delete(UFI_to_del)
    db.session.commit()
    return redirect('/')

# UFI MODEL
def delete_plaid_UFI_access_key(UFI_access_key):
    request = ItemRemoveRequest(access_token=UFI_access_key)
    response = plaid_client.item_remove(request)
    print(response) #DELETE
    

# @app.route('/financial-institutions/<int:UFI_id>/accounts/populate')
##############################################################################
# Accounts CRUD and functions

# UFI MODEL
def populate_UFI_accounts(UFI_id):
    curr_UFI = UserFinancialInstitute.query.get_or_404(UFI_id)
    request = AccountsBalanceGetRequest(access_token=curr_UFI.plaid_access_token)
    response = plaid_client.accounts_balance_get(request)
    accounts = response['accounts']
    # print(accounts)
    for account in accounts:
        budget_trackable = False
        # print(str(account['type']))
        if str(account['type']) == 'depository':
            available=account['balances']['available']
            current=account['balances']['current']
            limit=account['balances']['limit']
            if str(account['subtype']) in ['checking', 'paypal']:
                budget_trackable = True
        elif str(account['type']) == 'credit':
            current=account['balances']['current']
            limit=account['balances']['limit']
            available=limit - current
            budget_trackable = True
        elif str(account['type']) in ['loan', 'investment']:
            available=account['balances']['available']
            current=account['balances']['current']
            limit=account['balances']['limit']

        if current:             
            new_Account = Account(
                name=account['name'],
                UFI_id=UFI_id,
                available=available,
                current=current,
                limit=limit,
                type=str(account['type']),
                subtype=str(account['subtype']),
                account_id=str(account['account_id']),
                budget_trackable=budget_trackable
            )
            db.session.add(new_Account)
            db.session.commit()

# UFI MODEL
def update_accounts_of_UFI(UFI_id):
    UFI=UserFinancialInstitute.query.get_or_404(UFI_id)
    account_ids=[]
    for account in UFI.accounts:
        account_ids.append(account.account_id)
    request = AccountsBalanceGetRequest(access_token=UFI.plaid_access_token,
                                        options=AccountsBalanceGetRequestOptions(
                                                account_ids=account_ids
                                                )
              )
    response = plaid_client.accounts_balance_get(request)
    accounts = response['accounts']
    # print(accounts)
    for account in accounts:
        if str(account['type']) == 'depository':
            available=account['balances']['available']
            current=account['balances']['current']
            limit=account['balances']['limit']
        elif str(account['type']) == 'credit':
            current=account['balances']['current']
            limit=account['balances']['limit']
            available=limit - current
        elif str(account['type']) in ['loan', 'investment']:
            available=account['balances']['available']
            current=account['balances']['current']
            limit=account['balances']['limit']
            
        update_account = Account.query.filter_by(account_id=account['account_id']).first()
        update_account.name = account['name']
        update_account.available = available
        update_account.current = current
        update_account.limit = limit
        
        db.session.add(update_account)
        db.session.commit()

# ACCOUNT MODEL
def get_amount_spent_for_account(account, start, end):
    access_token=account.UFI.plaid_access_token
    request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start.date(),
            end_date=end.date(),
            options=TransactionsGetRequestOptions(account_ids=[account.account_id])
    )
    response = plaid_client.transactions_get(request)
    transactions = response['transactions']
    print(transactions)
    omit_categories = ["Transfer", "Credit Card", "Deposit", "Payment"]
    amount_spent=0
    for transaction in transactions:
        category_allowed=True
        for category in transaction['category']:
            if category in omit_categories:
                category_allowed=False
        if category_allowed and transaction['amount'] > 0:
            print(transaction['category'])
            amount_spent+=transaction['amount']
    return round(amount_spent,2)
    

@app.route('/financial-institutions/<int:UFI_id>/accounts/update')
def update_UFI_accounts_on_page(UFI_id):
    update_accounts_of_UFI(UFI_id)
    return redirect('/')

@app.route('/accounts/<int:acct_id>/delete', methods=['POST'])
def delete_account(acct_id):
    acct_to_delete = Account.query.get_or_404(acct_id)
    UFI = acct_to_delete.UFI
    acct_owner_id = UFI.user_id

    if not g.user or acct_owner_id != g.user.id:
        flash("Access unauthorized.", 'danger')
        return redirect('/')
    
    db.session.delete(acct_to_delete)
    db.session.commit()
    return redirect('/')

##############################################################################
# BudgetTracker CRUD and functions
@app.route('/accounts/<int:acct_id>/budget-tracker/create', methods=['GET', 'POST'])
def create_budget_tracker(acct_id):
    """Displays form for a user to enter parameters for a budget tracker for their account
        -If the account DNE, 404
        -If a user (in session or not) tries to add a budget tracker for an account they do not own, they are redirected to home with an error message
        -If a user does not enter all required information, it recycles the form with proper error messages
        -If a user does enter required information, it enters a new budget tracker into the database and sends a user to their dashboard
        -If a user tries to create a budgettracker for an account where one exists already, redirect home with error
    """
    specified_acct = Account.query.get_or_404(acct_id)
    UFI_of_acct = specified_acct.UFI
    if not g.user or UFI_of_acct not in g.user.UFIs:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    if specified_acct.budgettracker:
        flash("Budget Tracker already exists for this account.", "danger")
        return redirect("/")
    form = CreateBudgetTrackerForm()
    if form.validate_on_submit():
        try:
            today_date = datetime.datetime.today()
            if today_date.day == 1:
                amount_spent = 0
            else:
                amount_spent = get_amount_spent_for_account(specified_acct, today_date.replace(day=1), today_date)
            new_budget_tracker = BudgetTracker(
                                                budget_threshold=form.budget_threshold.data,
                                                notification_frequency=form.notification_frequency.data,
                                                next_notification_date=(today_date+timedelta(days=form.notification_frequency.data)),
                                                amount_spent=amount_spent,
                                                account_id=specified_acct.id,
                                                user_id=g.user.id
                                              )
            db.session.add(new_budget_tracker)
            db.session.commit()
        except:
            flash("database error", 'danger') #DELETE
            return render_template('budget_tracker/create.html', form=form, account=specified_acct) 
        return redirect('/')
    else:
        return render_template('budget_tracker/create.html', form=form, account=specified_acct) 

@app.route('/accounts/<int:acct_id>/budget-tracker/update', methods=['GET', 'POST'])
def update_budget_tracker(acct_id):
    """
    Displays form for a user to enter parameters for a budget tracker for their account
        -If the budget tracker DNE, 404
        -If a user (in session or not) tries to update a budget tracker they do not own, they are redirected to home with an error message
        -If a user does not enter all required information, it recycles the form with proper error messages
        -If a user does enter required information, it updates the budget tracker instance in the database and sends a user to their dashboard
        -If a user tries to create a budgettracker for an account where one exists already, redirect home with error
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    specified_bt = BudgetTracker.query.filter_by(user_id=g.user.id, account_id=acct_id).first()

    if not specified_bt:
        flash("Budget Tracker not in database.", "danger")
        return redirect("/")
   
    form = UpdateBudgetTrackerForm()

    if form.validate_on_submit():
        try:
            specified_bt.budget_threshold=form.budget_threshold.data
            specified_bt.notification_frequency=form.notification_frequency.data
            db.session.add(specified_bt)
            db.session.commit()
        except:
            flash("database error", 'danger') #DELETE
            return render_template('budget_tracker/update.html', form=form, account=specified_bt.account) 
        return redirect('/')
    else:
        return render_template('budget_tracker/update.html', form=form, account=specified_bt.account) 

@app.route('/accounts/<int:acct_id>/budget-tracker/delete', methods=['POST'])
def delete_budget_tracker(acct_id):
    if not g.user:
        flash("Access unauthorized.", 'danger')
        return redirect('/')
    
    specified_bt = BudgetTracker.query.filter_by(user_id=g.user.id, account_id=acct_id).first()
    
    if not specified_bt:
        flash("Budget Tracker not in database.", "danger")
        return redirect("/")

    db.session.delete(specified_bt)
    db.session.commit()
    return redirect('/')

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

@app.route('/')
def homepage():
    """If user is not logged in, gives them options to sign up or log in"""
    if g.user:         

        return render_template('user_home.html')
    return render_template('no_user_home.html')

@app.route('/signup', methods=['GET', 'POST'])
def user_new_signup():
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
            user = User.signup(
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

        do_login(user)

        return redirect('/')

    else:
        return render_template('users/signup.html', form=form) 

@app.route('/login', methods=["GET", "POST"])
def login():
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

@app.route('/logout')
def logout():
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

@app.route('/users/update-profile', methods=["GET", "POST"])
def update_profile():
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

@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
    else:
        user = User.query.get(g.user.id)
        do_logout()
        db.session.delete(user)
        db.session.commit()
        
    return redirect("/")

##############################################################################
# Twilio Send Text Function
# Find your Account SID and Auth Token at twilio.com/console
# and set the environment variables. See http://twil.io/secure

twilio_number = os.getenv('TWILIO_NUM')
twilio_client = TwilioClient(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))

def send_text(phone_number, msg):
    phone_number='+1'+phone_number
    twilio_client.api.account.messages.create(to=phone_number, from_=os.getenv('TWILIO_NUM'), body=msg)

##############################################################################
# Scheduled Jobs
# run 'flask crontab add' to initialize
# run 'flask crontab remove' to remove
# This will run everyday at 12pm UTC
@crontab.job(minute=0, hour=12)
def scheduled():
    """Run scheduled job"""
    # Refresh accounts
    scheduled_daily_refresh_all_accounts()
    # Update budget tracker amount spent vals
    scheduled_daily_refresh_budgettrackers()
    #Notify users
    scheduled_daily_send_bt_notifications()

# UFI MODEL
def scheduled_daily_refresh_all_accounts():
    UFIs = UserFinancialInstitute.query.all()
    for UFI in UFIs:
        update_accounts_of_UFI(UFI.id)

# BT MODEL
def scheduled_daily_refresh_budgettrackers():
    budgettrackers = BudgetTracker.query.all()
    for bt in budgettrackers:
        today_date = datetime.datetime.today()
        if today_date.day == 1:
            amount_spent = 0
        else:
            amount_spent = get_amount_spent_for_account(bt.account, today_date.replace(day=1), today_date)
        bt.amount_spent = amount_spent
        db.session.add(bt)
        db.session.commit()

# BT MODEL
def scheduled_daily_send_bt_notifications():
    """Grabs all budget trackers scheduled to send notifications to their users, sends mobile text"""
    bt_scheduled_for_notif = BudgetTracker.find_all_scheduled_today()
    for bt in bt_scheduled_for_notif:
        phone_number = bt.user.phone_number
        msg = f'BudgetTracker for {bt.account.name}\nYou have spent ${bt.amount_spent} of your ${bt.budget_threshold} budget threshold.'
        send_text(phone_number,msg)
        bt.update_next_notify_date()