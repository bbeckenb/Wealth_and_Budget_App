"""UserFinancialInstitution Model tests."""
from unittest import TestCase
import app
from app import app
from database.database import db
from models.User import User
from models.UserFinancialInstitution import UserFinancialInstitute
from models.PlaidClient import PlaidClient
from models.Account import Account

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///test_wealth_and_budget_db'
app.config['SQLALCHEMY_ECHO'] = False
# Disables CSRF on WTForms
app.config['WTF_CSRF_ENABLED'] = False
# Make Flask errors be real errors, rather than HTML pages with error info
app.config['TESTING'] = True
# This is a bit of hack, but don't use Flask DebugToolbar
app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']
app.secret_key = 'test_key'

db.drop_all()
db.create_all()

class UserFinancialInstitutionModelTestCase(TestCase):
    """Test Model for UFIs."""

    def setUp(self):
        """Create test client, add sample data."""
        self.client = app.test_client()

        test_user0 = User(  username='harrypotter', 
                            password='HASHED_PASSWORD',
                            phone_number='9999999999',
                            first_name='Harry',
                            last_name='Potter',
                            account_type='sandbox')
        db.session.add(test_user0)
        db.session.commit()

        self.test_user0 = test_user0
        self.plaid_inst = PlaidClient(test_user0.account_type)
        
        test_UFI = UserFinancialInstitute(name='Test_name', 
                                    user_id=test_user0.id,
                                    item_id='test_item_id',
                                    plaid_access_token=self.plaid_inst.createTestUFIToken())
        db.session.add(test_UFI)
        db.session.commit()

        self.test_UFI = test_UFI

    def tearDown(self):
        """Clean up any fouled transaction"""
        Account.query.delete()
        UFIs_to_clean = UserFinancialInstitute.query.all()
        for UFI in UFIs_to_clean:
            UFI.delete_UFI(UFI.user.account_type)
        User.query.delete()

    def test_UserFinancialInstitute_model(self):
        """Does basic model work?"""
        u = UserFinancialInstitute(   
                name='Test_Bank', 
                user_id=self.test_user0.id,
                item_id='test_item_id',
                plaid_access_token=self.plaid_inst.createTestUFIToken(),
                )

        db.session.add(u)
        db.session.commit()
        # Already one instance in from Test Setup
        self.assertEqual(len(UserFinancialInstitute.query.all()), 2)
   
    def test_UFI__repr__(self):
        """Checks what UFI.__repr__ outputs"""
    
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