"""Account View function tests."""
from unittest import TestCase
import app
from app import app
from database.database import db
from models.User import User
from models.UserFinancialInstitution import UserFinancialInstitute
from models.PlaidClient import PlaidClient
from models.Account import Account
from models.BudgetTracker import BudgetTracker
import datetime

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

class BudgetTrackerViewsTestCase(TestCase):
    """Test views for BudgetTrackers."""

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
        
        # Loads test accounts from Plaid API
        self.test_UFI.populate_UFI_accounts(self.test_UFI.id)

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
        Account.query.delete()
        UFIs_to_clean = UserFinancialInstitute.query.all()
        for UFI in UFIs_to_clean:
            UFI.delete_UFI(UFI.user.account_type)
        User.query.delete()
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
                sess["curr_user"] = self.test_user0.id
        
            res = c.get('/')
            html = res.get_data(as_text=True)
            
            self.assertEqual(res.status_code, 200)
            self.assertIn('BudgetTracker Status:', html)
            self.assertIn('budget-tracker/create" class="btn btn-sm btn-outline-success">Create BudgetTracker</a>', html)
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
                sess["curr_user"] = self.test_user0.id

            res = c.post('/accounts/1/budget-tracker/create', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 404) 

    def test_create_budget_tracker_no_user(self):
        """If no user in session redirect home, flash access unauthorized"""
        account_id = self.test_UFI.accounts[2].id
        with self.client as c:
            with c.session_transaction() as sess:
                if "curr_user" in sess:
                    del sess["curr_user"]

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
                sess["curr_user"] = other_user_id

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
                sess["curr_user"] = self.test_user0.id

            res = c.post(f'/accounts/{account_id}/budget-tracker/create', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger">Budget Tracker already exists for this account.</div>', html)

    def test_create_budget_tracker_ineligible_acct(self):
        """if all criteria are met, a new budgettracker instance is created, entered into the database and user is redirected home"""
        # this account is ineligible for budget tracking
        account_id = self.test_UFI.accounts[1].id
        with self.client as c:
            with c.session_transaction() as sess:
                sess["curr_user"] = self.test_user0.id
           
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
                sess["curr_user"] = self.test_user0.id
            d={'budget_threshold':30, 'notification_frequency':3}
            res = c.post(f'/accounts/{account_id}/budget-tracker/create', data=d, follow_redirects=True)      
            html = res.get_data(as_text=True)
            
            account = Account.query.get(account_id)
            self.assertIn(f'<li class="list-group-item list-group-item-warning">Amount Spent: $ {account.budgettracker[0].amount_spent}</li>', html)

    def test_update_budget_tracker_no_user(self):
        """If no user in session redirect home, flash access unauthorized"""
        account_id = self.test_UFI.accounts[0].id
        with self.client as c:
            with c.session_transaction() as sess:
                if "curr_user" in sess:
                    del sess["curr_user"]

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
                sess["curr_user"] = self.test_user0.id

            res = c.post(f'/accounts/{wrong_account_id}/budget-tracker/update', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger">Budget Tracker not in database.</div>', html)

    def test_update_budget_tracker_success(self):
        """if all criteria are met, the existing budgettracker instance is updated, and user is redirected home"""
        # this account has test_budgettracker tied to it    
        account_id = self.test_UFI.accounts[0].id

        with self.client as c:
            with c.session_transaction() as sess:
                sess["curr_user"] = self.test_user0.id
            res = c.get('/')
            html = res.get_data(as_text=True)
            
            account = Account.query.get(account_id)
            self.assertEqual(res.status_code, 200)
            self.assertIn('Notification Frequency (days): 5', html)
            
            d={'budget_threshold':30, 'notification_frequency':3}
            res = c.post(f'/accounts/{account_id}/budget-tracker/update', data=d, follow_redirects=True)      
            html = res.get_data(as_text=True)
            
            account = Account.query.get(account_id)
            self.assertIn(f'Notification Frequency (days): 3', html)

    def test_delete_budget_tracker_no_user(self):
        """If no user in session redirect home, flash access unauthorized"""
        account_id = self.test_UFI.accounts[0].id
        with self.client as c:
            with c.session_transaction() as sess:
                if "curr_user" in sess:
                    del sess["curr_user"]

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
                sess["curr_user"] = self.test_user0.id

            res = c.post(f'/accounts/{wrong_account_id}/budget-tracker/delete', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger">Budget Tracker not in database.</div>', html)

    def test_delete_budget_tracker_success(self):
        """If all criteria are met, remove specified budget tracker from database, redirect home"""
        account_id = self.test_UFI.accounts[0].id

        with self.client as c:
            with c.session_transaction() as sess:
                sess["curr_user"] = self.test_user0.id
        
            res = c.post(f'/accounts/{account_id}/budget-tracker/delete', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertNotIn('<h6>Budget Tracker Status', html)
            self.assertEqual(len(BudgetTracker.query.all()),0)