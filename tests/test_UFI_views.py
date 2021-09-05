"""UserFinancialInstitution View function tests."""

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

class UserFinancialInstitutionViewTestCase(TestCase):
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

    def tearDown(self):
        """Clean up any fouled transaction"""
        User.query.delete()
        UFIs_to_clean = UserFinancialInstitute.query.all()
        for UFI in UFIs_to_clean:
            delete_plaid_UFI_access_key(UFI.plaid_access_key)
        UserFinancialInstitute.query.delete()
        Account.query.delete()

    def test_UFI_appears_in_home_with_user(self):
        """makes sure home page:
            -shows dashboard of overall wealth
            -shows mini-dashboards of individual financial institutions
                -mini dashboards are links that let users click to item page
            -allow user to log out
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id
        
            res = c.get('/')
            html = res.get_data(as_text=True)
            
            self.assertEqual(res.status_code, 200)
            self.assertIn('<h5 class="card-title">Test_name</h5>', html)

    def test_UFI_delete_bad_user(self):
        """makes sure if user is not present or does not have ownership of UFI
            -is redirected home
            -warning is flashed"""

        user = User.signup(  username='harrypotter1', 
                            password='HASHED_PASSWORD',
                            phone_number='999-999-9999',
                            first_name='Harry',
                            last_name='Potter')
        db.session.commit()

        not_owner_id = user.id

        UFI_id = self.test_UFI.id
        with self.client as c:
            with c.session_transaction() as sess:
                if CURR_USER_KEY in sess:
                    del sess[CURR_USER_KEY]

            res = c.post(f'/financial-institutions/{UFI_id}/delete', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger">Access unauthorized.</div>', html)

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = not_owner_id
            
            res = c.post(f'/financial-institutions/{UFI_id}/delete', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger">Access unauthorized.</div>', html)

    def test_UFI_id_DNE_delete(self):
        """makes sure if UFI id is not in database, 404 occurs"""

        UFI_id = self.test_UFI.id + 1

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id

            res = c.post(f'/financial-institutions/{UFI_id}/delete', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 404)      

    def test_UFI_delete_success(self):
        """makes sure if proper owner is deleting an existing UFI, the instance is taken out of the database access key is deleted"""     
        id = self.test_UFI.id
       
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id

            res = c.get('/')
            html = res.get_data(as_text=True)
            self.assertIn('<h5 class="card-title">Test_name</h5>', html)
            
            res = c.post(f'/financial-institutions/{id}/delete')      
            html = res.get_data(as_text=True)
            self.assertNotIn('<h5 class="card-title">Test_name</h5>', html)
            self.assertEqual(len(UserFinancialInstitute.query.all()), 0)