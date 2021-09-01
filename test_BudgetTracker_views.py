"""Account View function tests."""

from unittest import TestCase

from app import app, CURR_USER_KEY, populate_UFI_accounts
from models import db, User, UserFinancialInstitute, Account, BudgetTracker
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.products import Products
from plaid.api import plaid_api
import datetime
from datetime import timedelta
import plaid
import os

PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET') # Note in sandbox env currently
PLAID_ENV = os.getenv('PLAID_ENV')
PLAID_PRODUCTS = os.getenv('PLAID_PRODUCTS', 'transactions').split(',')
PLAID_COUNTRY_CODES = os.getenv('PLAID_COUNTRY_CODES', 'US').split(',')
# Use test database and don't clutter tests with SQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///test_wealth_and_budget_db'
app.config['SQLALCHEMY_ECHO'] = False
# Disables CSRF on WTForms
app.config['WTF_CSRF_ENABLED'] = False

# Make Flask errors be real errors, rather than HTML pages with error info
app.config['TESTING'] = True

# This is a bit of hack, but don't use Flask DebugToolbar
app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']

db.drop_all()
db.create_all()

host = plaid.Environment.Sandbox 

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
client = plaid_api.PlaidApi(api_client)

products = []
for product in PLAID_PRODUCTS:
    products.append(Products(product))

def createTestUFIToken():
        pt_request = SandboxPublicTokenCreateRequest(
                                    institution_id='ins_109508',
                                    initial_products=[Products('transactions')]
                    )
        pt_response = client.sandbox_public_token_create(pt_request)
        # The generated public_token can now be
        # exchanged for an access_token
        exchange_request = ItemPublicTokenExchangeRequest(
                                    public_token=pt_response['public_token']
                            )
        exchange_response = client.item_public_token_exchange(exchange_request)
        
        return exchange_response['access_token']

def delete_plaid_UFI_access_key(UFI_access_key):
    request = ItemRemoveRequest(access_token=UFI_access_key)
    response = client.item_remove(request)
    print(response) 

class UserAccountViewsTestCase(TestCase):
    """Test views for UFIs."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        UserFinancialInstitute.query.delete()
        Account.query.delete()
        BudgetTracker.query.delete()

        self.client = app.test_client()

        # Test User 0 
        test_user0 = User(  username='harrypotter', 
                            password='HASHED_PASSWORD',
                            phone_number='9999999999',
                            first_name='Harry',
                            last_name='Potter')
        db.session.add(test_user0)
        db.session.commit()

        self.test_user0 = test_user0
        
        test_UFI = UserFinancialInstitute(name='Test_name', 
                                    user_id=test_user0.id,
                                    item_id='test_item_id',
                                    plaid_access_token=createTestUFIToken())
        db.session.add(test_UFI)
        db.session.commit()

        self.test_UFI = test_UFI
        
        # Loads test accounts from Plaid API
        populate_UFI_accounts(test_UFI.id)

        test_account = test_UFI.accounts[0]
        self.test_account = test_account

        test_budgettracker = BudgetTracker(
                                            budget_threshold=500,
                                            notification_frequency=5,
                                            next_notification_date=datetime.datetime.today(),
                                            amount_spent=20,
                                            account_id=test_account.id,
                                            user_id=test_user0.id
                                            )
        db.session.add(test_budgettracker)
        db.session.commit()
        self.test_budgettracker = test_budgettracker

    def tearDown(self):
        """Clean up any fouled transaction"""
        User.query.delete()
        UFIs_to_clean = UserFinancialInstitute.query.all()
        for UFI in UFIs_to_clean:
            delete_plaid_UFI_access_key(UFI.plaid_access_key)
        UserFinancialInstitute.query.delete()
        Account.query.delete()
        BudgetTracker.query.delete()


    def test_Account_appears_in_home_with_user(self):
        """makes sure home page:
            -shows accounts eligible for budget tracking
            -the test account the test budget tracker is attached to is eligible, but has a budget tracker attached already so 
            it will have an option to update the budget tracker
            
        """
        amount_spent = self.test_budgettracker.amount_spent
        budget_threshold = self.test_budgettracker.budget_threshold
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id
        
            res = c.get('/')
            html = res.get_data(as_text=True)
            
            self.assertEqual(res.status_code, 200)
            self.assertIn(f'<h6>Budget Tracker Status - Amount Spent: $ {amount_spent} - Monthly Budget: $ {budget_threshold}</h6>', html)
            self.assertIn('/budget-tracker/create" class="btn btn-sm btn-success">Create BudgetTracker</a>', html)
            self.assertNotIn('<p>You have no accounts on record with this institution</p>', html)

    def test_create_budget_tracker_account_DNE(self):
        """Displays form for a user to enter parameters for a budget tracker for their account
        -If the account DNE, 404
        -If a user (in session or not) tries to add a budget tracker for an account they do not own, they are redirected to home with an error message
        -If a user does not enter all required information, it recycles the form with proper error messages
        -If a user does enter required information, it enters a new budget tracker into the database and sends a user to their dashboard
        -If a user tries to create a budgettracker for an account where one exists already, redirect home with error
        """
        """makes sure if Account id is not in database, 404 occurs"""
        # no accounts, account id cannot exist
        Account.query.delete()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id

            res = c.post('/accounts/1/budget-tracker/create', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 404) 

    def test_create_budget_tracker_no_user(self):
        """If no user in session redirect home, flash access unauthorized"""
        account_id = self.test_UFI.accounts[2].id
        with self.client as c:
            with c.session_transaction() as sess:
                if CURR_USER_KEY in sess:
                    del sess[CURR_USER_KEY]

            res = c.post(f'/accounts/{account_id}/budget-tracker/create', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger">Access unauthorized.</div>', html)
    
    def test_create_budget_tracker_bad_user(self):
        """checks to see if the account the budgettracker is being created for is owned by the user in the session"""
        other_user = User(
                        username='ronweasley', 
                        password='HASHED_PASSWORD',
                        phone_number='1999999999',
                        first_name='Ron',
                        last_name='Weasley'
                     )
        db.session.add(other_user)
        db.session.commit()

        other_user_id = other_user.id
        acct_id = self.test_account.id

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = other_user_id

            res = c.post(f'/accounts/{acct_id}/budget-tracker/create', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger">Access unauthorized.</div>', html)
    
    def test_create_budget_tracker_bt_already_exists(self):
        """checks to see if a budget tracker already exists for the requested account
            -if true - redirects home, flashes warning"""
        # test_account already has test_budgettracker tied to it
        account_id = self.test_account.id
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id

            res = c.post(f'/accounts/{account_id}/budget-tracker/create', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger">Budget Tracker already exists for this account.</div>', html)

    def test_create_budget_tracker_ineligible_acct(self):
        """if all criteria are met, a new budgettracker instance is created, entered into the database and user is redirected home"""
        # this account is ineligible for budget tracking
        account_id = self.test_UFI.accounts[1].id
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id
           
            res = c.post(f'/accounts/{account_id}/budget-tracker/create', follow_redirects=True)      
            html = res.get_data(as_text=True)

            
            self.assertIn('<div class="alert alert-danger">Account is not eligible for budget tracking.</div>', html)

    def test_create_budget_tracker_success(self):
        """if all criteria are met, a new budgettracker instance is created, entered into the database and user is redirected home"""
        # There are no budgettrackers now
        BudgetTracker.query.delete()
        # this account has no test_budgettracker tied to it but is eligible
        account_id = self.test_UFI.accounts[3].id
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id
            d={'budget_threshold':30, 'notification_frequency':3}
            res = c.post(f'/accounts/{account_id}/budget-tracker/create', data=d, follow_redirects=True)      
            html = res.get_data(as_text=True)
            
            account = Account.query.get(account_id)
            self.assertIn(f'<h6>Budget Tracker Status - Amount Spent: $ {account.budgettracker[0].amount_spent} - Monthly Budget: $ {account.budgettracker[0].budget_threshold}</h6>', html)

    def test_update_budget_tracker_no_user(self):
        """If no user in session redirect home, flash access unauthorized"""
        account_id = self.test_UFI.accounts[0].id
        with self.client as c:
            with c.session_transaction() as sess:
                if CURR_USER_KEY in sess:
                    del sess[CURR_USER_KEY]

            res = c.post(f'/accounts/{account_id}/budget-tracker/update', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger">Access unauthorized.</div>', html)

    def test_update_budget_tracker_bt_DNE(self):
        """If the budget tracker DNE in the database, redirect home, flash warning"""
        #this account has a budget tracker attached, none of the other test accounts do
        account_id = self.test_UFI.accounts[0].id
        wrong_account_id = account_id+1
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id

            res = c.post(f'/accounts/{wrong_account_id}/budget-tracker/update', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger">Budget Tracker not in database.</div>', html)

    def test_create_budget_tracker_success(self):
        """if all criteria are met, the existing budgettracker instance is updated, and user is redirected home"""
        # this account has test_budgettracker tied to it
        amount_spent = self.test_budgettracker.amount_spent
        budget_threshold = self.test_budgettracker.budget_threshold     
        account_id = self.test_UFI.accounts[0].id

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id
            res = c.get('/')
            html = res.get_data(as_text=True)
            
            self.assertEqual(res.status_code, 200)
            self.assertIn(f'<h6>Budget Tracker Status - Amount Spent: $ {amount_spent} - Monthly Budget: $ {budget_threshold}</h6>', html)
            
            d={'budget_threshold':30, 'notification_frequency':3}
            res = c.post(f'/accounts/{account_id}/budget-tracker/update', data=d, follow_redirects=True)      
            html = res.get_data(as_text=True)
            
            account = Account.query.get(account_id)
            self.assertIn(f'<h6>Budget Tracker Status - Amount Spent: $ {account.budgettracker[0].amount_spent} - Monthly Budget: $ {account.budgettracker[0].budget_threshold}</h6>', html)

    def test_delete_budget_tracker_no_user(self):
        """If no user in session redirect home, flash access unauthorized"""
        account_id = self.test_UFI.accounts[0].id
        with self.client as c:
            with c.session_transaction() as sess:
                if CURR_USER_KEY in sess:
                    del sess[CURR_USER_KEY]

            res = c.post(f'/accounts/{account_id}/budget-tracker/delete', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger">Access unauthorized.</div>', html)

    def test_delete_budget_tracker_bt_DNE(self):
        """If the budget tracker DNE in the database, redirect home, flash warning"""
        #this account has a budget tracker attached, none of the other test accounts do
        account_id = self.test_UFI.accounts[0].id
        wrong_account_id = account_id+1
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id

            res = c.post(f'/accounts/{wrong_account_id}/budget-tracker/delete', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger">Budget Tracker not in database.</div>', html)

    def test_delete_budget_tracker_success(self):
        """If all criteria are met, remove specified budget tracker from database, redirect home"""
        account_id = self.test_UFI.accounts[0].id

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id
        
            res = c.post(f'/accounts/{account_id}/budget-tracker/delete', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertNotIn('<h6>Budget Tracker Status', html)
            self.assertEqual(len(BudgetTracker.query.all()),0)