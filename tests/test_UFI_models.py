"""UserFinancialInstitution Model tests."""

from unittest import TestCase

from app import app, CURR_USER_KEY
from models import db, User, UserFinancialInstitute, Account
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.products import Products
from plaid.api import plaid_api
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
    print(response) #DELETE

class UserFinancialInstitutionModelTestCase(TestCase):
    """Test Model for UFIs."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        UserFinancialInstitute.query.delete()
        Account.query.delete()

        self.client = app.test_client()

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

    def tearDown(self):
        """Clean up any fouled transaction"""
        User.query.delete()
        UFIs_to_clean = UserFinancialInstitute.query.all()
        for UFI in UFIs_to_clean:
            delete_plaid_UFI_access_key(UFI.plaid_access_key)
        UserFinancialInstitute.query.delete()
        Account.query.delete()

    def test_UserFinancialInstitute_model(self):
        """Does basic model work?"""
        u = UserFinancialInstitute(   
                name='Test_Bank', 
                user_id=self.test_user0.id,
                item_id='test_item_id',
                plaid_access_token=createTestUFIToken(),
                )

        db.session.add(u)
        db.session.commit()
        # Already one instance in from Test Setup
        self.assertEqual(len(UserFinancialInstitute.query.all()), 2)
   
   
    def test_user__repr__(self):
        """Checks what User.__repr__ outputs"""
    
        self.assertEqual(repr(self.test_UFI), f"<UFI name=Test_name user_id={self.test_user0.id}>")

    def test_UFI_aggregate_account_balances(self):
        """makes sure method adds and returns the balances of its accounts:
            -if 'with_loans'=True, subtracts 'current' value of accounts with
            'type' of 'loan'
            -if 'with_loans'=False (Default), account ballances with 'type' of 'loan' are not included in the returned aggregated amount
            -
            """
        depository = Account(name='n1', 
                         UFI_id=self.test_UFI.id, 
                         available=10, current=10, 
                         limit=None, type='depository', 
                         subtype='checking', 
                         account_id='X', 
                         budget_trackable=True)
        db.session.add(depository)
        db.session.commit()
        credit = Account(name='n2', 
                         UFI_id=self.test_UFI.id, 
                         available=None, current=5, 
                         limit=10, type='credit', 
                         subtype='paypal credit', 
                         account_id='Y', 
                         budget_trackable=True)
        db.session.add(credit)
        db.session.commit()
        loan = Account(name='n3', 
                         UFI_id=self.test_UFI.id, 
                         available=None, current=20, 
                         limit=10, type='loan', 
                         subtype='student loan', 
                         account_id='Z', 
                         budget_trackable=False)
        db.session.add(loan)
        db.session.commit()
        
        self.assertEqual(self.test_UFI.aggregate_account_balances(), 5)
        self.assertEqual(self.test_UFI.aggregate_account_balances(with_loans=True), -15)

# get_UFI_info()
# def delete_plaid_UFI_access_key(UFI_access_key)
# def populate_UFI_accounts(UFI_id)
# def update_accounts_of_UFI(UFI_id)
# def scheduled_daily_refresh_all_accounts()