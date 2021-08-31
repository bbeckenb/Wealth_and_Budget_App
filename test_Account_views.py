"""Account View function tests."""

from unittest import TestCase

from app import app, CURR_USER_KEY, populate_UFI_accounts
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
    print(response) 

class UserAccountViewsTestCase(TestCase):
    """Test views for UFIs."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        UserFinancialInstitute.query.delete()
        Account.query.delete()

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

    def tearDown(self):
        """Clean up any fouled transaction"""
        User.query.delete()
        UFIs_to_clean = UserFinancialInstitute.query.all()
        for UFI in UFIs_to_clean:
            delete_plaid_UFI_access_key(UFI.plaid_access_key)
        UserFinancialInstitute.query.delete()
        Account.query.delete()

    def test_Account_appears_in_home_with_user(self):
        """makes sure home page:
            -shows cards for each financial institution where owned accounts are broken down
            -in this scenario test accounts have been loaded in from the Plaid API so we will verify 
            that accounts owned by the test_UFI are being loaded on the home page
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id
        
            res = c.get('/')
            html = res.get_data(as_text=True)
            
            self.assertEqual(res.status_code, 200)
            self.assertIn('<h5 class="card-title">Test_name</h5>', html)
            self.assertNotIn('<p>You have no accounts on record with this institution</p>', html)

    def test_manual_account_refresh(self):
       """allows user to click a button to auto-refresh all accounts
       refreshes homepage"""
       id = self.test_UFI.id
       with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id
            
            res = c.get(f'/financial-institutions/{id}/accounts/update', follow_redirects=True)
            html = res.get_data(as_text=True)
            
            self.assertEqual(res.status_code, 200)
            self.assertIn('<h5 class="card-title">Test_name</h5>', html)
            self.assertNotIn('<p>You have no accounts on record with this institution</p>', html)

    def test_Account_id_DNE_delete(self):
        """makes sure if Account id is not in database, 404 occurs"""
        # no accounts, account id cannot exist
        Account.query.delete()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id

            res = c.post('/accounts/1/delete', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 404) 

    def test_Account_no_user(self):
        """if no user in session, redirects home, flashes access unauthorized warning"""
        account_id = self.test_UFI.accounts[0].id
        with self.client as c:
            with c.session_transaction() as sess:
                if CURR_USER_KEY in sess:
                    del sess[CURR_USER_KEY]

            res = c.post(f'/accounts/{account_id}/delete', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger">Access unauthorized.</div>', html)

    def test_Account_id_wrong_user(self):
        """if wrong user in session, redirects home, flashes access unauthorized warning"""
        
        account_id = self.test_UFI.accounts[0].id
        wrong_id = self.test_user0.id + 1
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = wrong_id

            res = c.post(f'/accounts/{account_id}/delete', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger">Access unauthorized.</div>', html)

    def test_Account_delete_success(self):
        """makes sure if proper owner is deleting an existing Account, the instance is taken out of the database access key is deleted"""     
        account_id = self.test_UFI.accounts[0].id
        account_name = self.test_UFI.accounts[0].name
        account_list_length = len(Account.query.all())

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id

            res = c.get('/')
            html = res.get_data(as_text=True)
            self.assertIn(account_name, html)
            
            res = c.post(f'/accounts/{account_id}/delete')      
            html = res.get_data(as_text=True)
            self.assertNotIn(account_name, html)
            self.assertEqual(account_list_length-1, len(Account.query.all()))
    


