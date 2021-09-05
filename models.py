from plaid.model.accounts_balance_get_request_options import AccountsBalanceGetRequestOptions
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.api import plaid_api
from flask_sqlalchemy import SQLAlchemy
from twilio.rest import Client as TwilioClient
from datetime import timedelta, date
from flask import jsonify, request
from flask_bcrypt import Bcrypt
from sqlalchemy import func
import datetime
import plaid
import json
import time
import os

bcrypt = Bcrypt()
db = SQLAlchemy()
# best practice to create function to establish connection and only call it once
def connect_db(app):
    db.app = app
    db.init_app(app)
    db.create_all()
# MODELS GO BELOW
##############################################################################
# User
class User(db.Model):
    """Model for users"""

    __tablename__ = 'users' #specifies table name

    id = db.Column(db.Integer,
                        primary_key=True,
                        autoincrement=True) #serial in sql
    username = db.Column(db.Text, 
                        nullable=False, 
                        unique=True)
    password = db.Column(db.Text,
                        nullable=False)
    phone_number = db.Column(db.String,
                            nullable=False) 
    first_name = db.Column(db.Text,
                        nullable=False)
    last_name = db.Column(db.Text,
                        nullable=False)
    UFIs = db.relationship('UserFinancialInstitute', cascade='all, delete, delete-orphan', backref='user')
    budgettrackers = db.relationship('BudgetTracker', cascade='all, delete, delete-orphan', backref='user')

    def __repr__(self):
        u=self
        return f"<User username={u.username} phone_number={u.phone_number} first_name={u.first_name} last_name={u.last_name}>"

    @classmethod
    def signup(cls, username, password, phone_number, first_name, last_name):
        """Sign up user. Hashes password and adds user to system.
        """
        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')
        user = User(
            username=username,
            password=hashed_pwd,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name
        )
        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username, password):
        """Find user with `username` and `password`.
        This is a class method (call it on the class, not an individual user.)
        It searches for a user whose password hash matches this password
        and, if it finds such a user, returns that user object.
        If can't find matching user (or if password is wrong), returns False.
        """
        user = cls.query.filter_by(username=username).first()
        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user
        return False

    def aggregate_UFI_balances(self, with_loans=False):
        aggregated_balance=0
        for UFI in self.UFIs:
            aggregated_balance += UFI.aggregate_account_balances(with_loans)
        return aggregated_balance

    def pie_chart_data(self):
        UFI_data_array = []
        UFI_data_array.append(['Institution Name', 'Amount'])
        for UFI in self.UFIs:
            UFI_data_array.append([UFI.name, UFI.aggregate_account_balances()])
        return json.dumps(UFI_data_array)

    def delete_User(self):
        db.session.delete(self)
        db.session.commit()
##############################################################################
# UFI
class UserFinancialInstitute(db.Model):
    """Model links Users to financial institutions as 'Items' (in Plaid API vocabulary)"""
    __tablename__ = 'users_financial_institutions'

    id = db.Column(db.Integer,
                        primary_key=True,
                        autoincrement=True) #serial in sql
    name = db.Column(db.String,
                        nullable=False) #SHOULD NAME AND USER ID BOTH BE PK's?
    user_id = db.Column(db.Integer, 
                        db.ForeignKey('users.id', ondelete='CASCADE'), 
                        nullable=False)
    item_id = db.Column(db.String, nullable=False)
    plaid_access_token = db.Column(db.String, nullable=False)
    url=db.Column(db.Text, default=None)
    logo = db.Column(db.Text, default=None) 
    primary_color=db.Column(db.Text, default=None)
    accounts = db.relationship('Account', cascade='all, delete, delete-orphan', backref='UFI')

    def __repr__(self):
        u=self
        return f"<UFI name={u.name} user_id={u.user_id}>"
    
    @classmethod
    def create_new_UFI(cls, name, user_id, item_id, access_token, url, primary_color, logo):
        """generates and returns new UFI"""
        new_UFI = UserFinancialInstitute(
                                        name=name, 
                                        user_id=user_id, #g.user.id
                                        item_id=item_id,
                                        plaid_access_token=access_token,
                                        url=url,
                                        primary_color=primary_color,
                                        logo=logo

                  )
        db.session.add(new_UFI)
        db.session.commit()
        return new_UFI

    def delete_UFI(self, plaid_inst):
        plaid_deletion_response = plaid_inst.close_out_UFI_access_key_with_Plaid(self.plaid_access_token)
        db.session.delete(self)
        db.session.commit()
        return plaid_deletion_response
        
    def populate_UFI_accounts(self, plaid_inst):
        accounts = plaid_inst.get_UFI_Account_balances_from_Plaid(self.plaid_access_token)
        for account in accounts:
            budget_trackable = False
            print(str(account['type']))
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
                    UFI_id=self.id,
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

    def update_accounts_of_UFI(self, plaid_inst):
        account_ids=[]
        for account in self.accounts:
            account_ids.append(account.account_id)
        accounts = plaid_inst.get_UFI_specified_Account_balances_from_Plaid(account_ids, self.plaid_access_token)
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

    def aggregate_account_balances(self, with_loans=False):
        aggregated_balance = 0
        for account in self.accounts:
            if account.type == 'depository':
                if account.available:
                    aggregated_balance += account.available #for savings and checking, this is the most up to date value accounting for outstanding charges that are not fully processed
                else:
                    aggregated_balance += account.current #other 'depository' accounts like money market accounts do not have an 'available' amount so we need to use 'current'
            elif account.type == 'credit':
                aggregated_balance -= account.current #for 'credit' accounts, 'current' is what is owed to the financial institution
            elif account.type == 'investment':
                aggregated_balance += account.current
            elif account.type == 'loan':
                if with_loans:
                    aggregated_balance -= account.current #for 'loan' accounts, the 'current' value representings the outstanding amount still owed for the loan
        return round(aggregated_balance, 2)
##############################################################################
# Account
class Account(db.Model):
    """Model representing associated accounts from a UFI"""
    __tablename__ = 'accounts'
    id = db.Column(db.Integer,
                        primary_key=True,
                        autoincrement=True) #serial in sql
    name = db.Column(db.String,
                        nullable=False)
    UFI_id = db.Column(db.Integer,
                        db.ForeignKey('users_financial_institutions.id', ondelete='CASCADE'),
                        nullable=False)
    available = db.Column(db.Float)
    current = db.Column(db.Float,
                        nullable=False)
    limit = db.Column(db.Float)                   
    type = db.Column(db.Text,
                        nullable=False)
    subtype = db.Column(db.Text,
                        nullable=False)
    account_id=db.Column(db.Text,
                        nullable=False)
    budget_trackable = db.Column(db.Boolean, default=False)
    budgettracker = db.relationship('BudgetTracker', cascade='all, delete, delete-orphan', backref='account')

    def __repr__(self):
        u=self
        return f"<Account name={u.name} id={u.id} UFI_id={u.UFI_id} available={u.available} current={u.current} limit={u.limit}>"

    def get_amount_spent_for_account(self, start, end, plaid_inst):
        access_token=self.UFI.plaid_access_token
        transactions = plaid_inst.get_Account_transactions_from_Plaid(access_token, start, end, self.account_id)
        omit_categories = ["Transfer", "Credit Card", "Deposit", "Payment"]
        amount_spent=0
        for transaction in transactions:
            print(transaction)
            category_allowed=True
            for category in transaction['category']:
                if category in omit_categories:
                    category_allowed=False
            if category_allowed and transaction['amount'] > 0:
                print(transaction['category'])
                amount_spent+=transaction['amount']
        return round(amount_spent, 2)

    def delete_Account(self):
        db.session.delete(self)
        db.session.commit()

##############################################################################
# BT
class BudgetTracker(db.Model):
    """Model representing budget tracker of a specific account"""
    __tablename__ = 'budget_trackers'
    account_id = db.Column(db.Integer,
                        db.ForeignKey('accounts.id', ondelete='CASCADE'),
                        nullable=False, primary_key=True)
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id', ondelete='CASCADE'),
                        nullable=False, primary_key=True)
    budget_threshold = db.Column(db.Float,
                                nullable=False)
    notification_frequency = db.Column(db.Integer,
                                        nullable=False,
                                        default=5)
    next_notification_date = db.Column(db.DateTime, 
                                        nullable=False)
    amount_spent = db.Column(db.Float,
                                    nullable=False,
                                    default=0)
    
    def __repr__(self):
        u=self
        return f"<BudgetTracker account_id={u.account_id} user_id={u.user_id} notification_freq={u.notification_frequency} next_notification_date={u.next_notification_date}>"

    @classmethod
    def find_all_scheduled_today(cls):
        """filters budgettrackers by 'next_notification_date', all budget trackers 
            with a 'next_notification_date' equal to that day will be returned"""
        return cls.query.filter(func.date(cls.next_notification_date) == date.today()).all()

    @classmethod
    def scheduled_daily_refresh_budgettrackers(cls, plaid_inst):
        budgettrackers = cls.query.all()
        for bt in budgettrackers:
            today_date = datetime.datetime.today()
            if today_date.day == 1:
                amount_spent = 0
            else:
                amount_spent = bt.account.get_amount_spent_for_account(today_date.replace(day=1), today_date, plaid_inst)
            bt.amount_spent = amount_spent
            db.session.add(bt)
            db.session.commit()
    
    @classmethod
    def scheduled_daily_send_bt_notifications(cls, twilio_inst):
        """Grabs all budget trackers scheduled to send notifications to their users, sends mobile text"""
        bt_scheduled_for_notif = cls.find_all_scheduled_today()
        for bt in bt_scheduled_for_notif:
            phone_number = bt.user.phone_number
            msg = f'BudgetTracker for {bt.account.name}\nYou have spent ${bt.amount_spent} of your ${bt.budget_threshold} budget threshold.'
            twilio_inst.send_text(phone_number,msg)
            bt.update_next_notify_date()

    def update_amount_spent(self, plaid_inst):
        today_date = datetime.datetime.today()
        if today_date.day == 1:
            amount_spent = 0
        else:
            amount_spent = self.account.get_amount_spent_for_account(today_date.replace(day=1), today_date, plaid_inst)
        self.amount_spent = amount_spent
        db.session.add(self)
        db.session.commit()
    
    def update_next_notify_date(self):
        self.next_notification_date = self.next_notification_date + timedelta(days=self.notification_frequency)
        db.session.add(self)
        db.session.commit()

    def pretty_print_next_notify_date(self):
        return f"{self.next_notification_date.month}-{self.next_notification_date.day}-{self.next_notification_date.year}"

    def delete_budget_tracker(self):
        db.session.delete(self)
        db.session.commit()

##############################################################################
# MyPlaid
class MyPlaid:
    """Class to represent my connection to Plaid and house methods to call their API for this application"""
    def __init__(self, plaid_env='sandbox'):
        self.plaid_client = self.create_plaid_client(plaid_env)
        
    def create_plaid_client(self, environment='sandbox'):
        if environment == 'development':
            host = plaid.Environment.Development 
            secret = os.getenv('PLAID_SECRET')
        else:
            host = plaid.Environment.Sandbox
            secret = '0aae90632ad426c5d97740c670814f' #sandbox key
        configuration = plaid.Configuration(
            host=host,
            api_key={
                'clientId': os.getenv('PLAID_CLIENT_ID'),
                'secret': secret,
                'plaidVersion': '2020-09-14'
            }
        )
        api_client = plaid.ApiClient(configuration)
        plaid_client = plaid_api.PlaidApi(api_client)
        return plaid_client
  
    def get_UFI_info_from_Plaid(self, access_token):
            """retrieves institution name to create UFI instance (website, logo, and color also a possibility for customization)"""
            item_request = ItemGetRequest(access_token=access_token)
            item_response = self.plaid_client.item_get(item_request)
            institution_request = InstitutionsGetByIdRequest(
                institution_id=item_response['item']['institution_id'],
                country_codes=list(map(lambda x: CountryCode(x), os.getenv('PLAID_COUNTRY_CODES', 'US').split(',')))
            )
            institution_response = self.plaid_client.institutions_get_by_id(institution_request)
            return institution_response['institution']
    def create_plaid_link_token(self):
        try:
            products = []
            for product in os.getenv('PLAID_PRODUCTS', 'transactions').split(','):
                products.append(Products(product))
            request = LinkTokenCreateRequest(
                                            products=products,
                                            client_name="W_and_B_app",
                                            country_codes=list(map(lambda x: CountryCode(x), os.getenv('PLAID_COUNTRY_CODES', 'US').split(','))),
                                            language='en',
                                            user=LinkTokenCreateRequestUser(
                                                                            client_user_id=str(time.time())
                                                 )
                      )
            response = self.plaid_client.link_token_create(request)
            return jsonify(response.to_dict())
        except plaid.ApiException as e:
            return json.loads(e.body)

    def exchange_public_token_generate_access_token(self): #controller function
        public_token = request.form['public_token']
        req = ItemPublicTokenExchangeRequest(
            public_token=public_token
        )
        response = self.plaid_client.item_public_token_exchange(req)
        access_token = response['access_token']
        item_id = response['item_id']
        return access_token, item_id   
    
    def close_out_UFI_access_key_with_Plaid(self, access_token):
        request = ItemRemoveRequest(access_token=access_token)
        response = self.plaid_client.item_remove(request)
        return response

    def get_UFI_Account_balances_from_Plaid(self, access_token):
        request = AccountsBalanceGetRequest(access_token=access_token)
        response = self.plaid_client.accounts_balance_get(request)
        accounts = response['accounts']
        return accounts

    def get_UFI_specified_Account_balances_from_Plaid(self, account_ids, access_token):
        request = AccountsBalanceGetRequest(
                                            access_token=access_token,
                                            options=AccountsBalanceGetRequestOptions(
                                                                                        account_ids=account_ids
                                                    )
                    )
        response = self.plaid_client.accounts_balance_get(request)
        accounts = response['accounts']
        return accounts

    def get_Account_transactions_from_Plaid(self, access_token, start, end, account_id):
        request = TransactionsGetRequest(
                                        access_token=access_token,
                                        start_date=start.date(),
                                        end_date=end.date(),
                                        options=TransactionsGetRequestOptions(account_ids=[account_id])
                    )
        response = self.plaid_client.transactions_get(request)
        transactions = response['transactions']
        return transactions

##############################################################################
# MyTwilio
class MyTwilio:
    """Class to represent my connection to Twilio and house methods to call their API for this application"""
    def __init__(self):
        self.twilio_number = os.getenv('TWILIO_NUM')
        self.twilio_client = self.create_Twilio_client()

    def create_Twilio_client(self):
        return TwilioClient(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))

    def send_text(self, phone_number, msg):
        phone_number='+1'+phone_number
        self.twilio_client.api.account.messages.create(to=phone_number, from_=self.twilio_number, body=msg)