"""UserFinancialInstitution View function tests."""
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

class UserFinancialInstitutionViewTestCase(TestCase):
    """Test views for UFIs."""

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

    def test_UFI_appears_in_home_with_user(self):
        """makes sure home page:
            -shows dashboard of overall wealth
            -shows mini-dashboards of individual financial institutions
                -mini dashboards are links that let users click to item page
            -allow user to log out
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess["curr_user"] = self.test_user0.id
        
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
                            last_name='Potter',
                            account_type='sandbox')
        db.session.commit()

        not_owner_id = user.id

        UFI_id = self.test_UFI.id
        with self.client as c:
            with c.session_transaction() as sess:
                if "curr_user" in sess:
                    del sess["curr_user"]

            res = c.delete(f'/financial-institutions/{UFI_id}')      
            
            self.assertEqual(res.status_code, 401)

        with self.client as c:
            with c.session_transaction() as sess:
                sess["curr_user"] = not_owner_id
            
            res = c.delete(f'/financial-institutions/{UFI_id}')      

            self.assertEqual(res.status_code, 401)

    def test_UFI_id_DNE_delete(self):
        """makes sure if UFI id is not in database, 404 occurs"""

        UFI_id = self.test_UFI.id + 1

        with self.client as c:
            with c.session_transaction() as sess:
                sess["curr_user"] = self.test_user0.id

            res = c.post(f'/financial-institutions/{UFI_id}/delete', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 404)      

    def test_UFI_delete_success(self):
        """makes sure if proper owner is deleting an existing UFI, the instance is taken out of the database access key is deleted"""     
        id = self.test_UFI.id
       
        with self.client as c:
            with c.session_transaction() as sess:
                sess["curr_user"] = self.test_user0.id

            res = c.get('/')
            html = res.get_data(as_text=True)
            self.assertIn('<h5 class="card-title">Test_name</h5>', html)
            
            res = c.delete(f'/financial-institutions/{id}')   
            res = c.get('/')
            html = res.get_data(as_text=True)   
            self.assertNotIn('<h5 class="card-title">Test_name</h5>', html)
            self.assertEqual(len(UserFinancialInstitute.query.all()), 0)

   