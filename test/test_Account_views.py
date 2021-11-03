"""Account View function tests."""
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

class UserAccountViewsTestCase(TestCase):
    """Test views for Accounts."""

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

    def tearDown(self):
        """Clean up any fouled transaction"""
        Account.query.delete()
        UFIs_to_clean = UserFinancialInstitute.query.all()
        for UFI in UFIs_to_clean:
            UFI.delete_UFI(UFI.user.account_type)
        User.query.delete()

    def test_Account_appears_in_home_with_user(self):
        """makes sure home page:
            -shows cards for each financial institution where owned accounts are broken down
            -in this scenario test accounts have been loaded in from the Plaid API so we will verify 
            that accounts owned by the test_UFI are being loaded on the home page
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess["curr_user"] = self.test_user0.id
        
            res = c.get('/')
            html = res.get_data(as_text=True)
            
            self.assertEqual(res.status_code, 200)
            self.assertIn('<h5 class="card-title">Test_name</h5>', html)
            self.assertNotIn('<p>You have no accounts on record with this institution</p>', html)

    def test_manual_account_refresh(self):
       """allows user to click a button to auto-refresh all accounts
       refreshes homepage"""
       test_UFI = self.test_UFI
       id = test_UFI.id
       test_user0 = self.test_user0
       expected_output = {
                            'accounts': test_UFI.update_accounts_of_UFI(test_user0.account_type),
                            'id':id,
                            'accountBalNoLoan': test_UFI.aggregate_account_balances(),
                            'accountBalWithLoan': test_UFI.aggregate_account_balances(with_loans=True),
                            'name': test_UFI.name,
                            'userId': test_UFI.user_id,
                            'dashboardBalanceNoLoan': test_user0.aggregate_UFI_balances(),
                            'dashboardBalanceWithLoan': test_user0.aggregate_UFI_balances(with_loans=True),
                            'pieChartData': test_user0.pie_chart_data(),
                            'message': {'message': f"Accounts of {test_UFI.name} updated!", 'category': "info"}
                        }
       with self.client as c:
            with c.session_transaction() as sess:
                sess["curr_user"] = self.test_user0.id
            
            res = c.get(f'/financial-institutions/{id}/accounts/update')
            self.assertEqual(res.status_code, 200)

            data = res.json
            self.assertEqual(data, expected_output)

            


    def test_Account_id_DNE_delete(self):
        """makes sure if Account id is not in database, 404 occurs"""
        # no accounts, account id cannot exist
        Account.query.delete()

        with self.client as c:
            with c.session_transaction() as sess:
                sess["curr_user"] = self.test_user0.id

            res = c.post('/accounts/1/delete', follow_redirects=True)      
            self.assertEqual(res.status_code, 404) 

    def test_Account_no_user(self):
        """if no user in session, redirects home, flashes access unauthorized warning"""
        account_id = self.test_UFI.accounts[0].id
        with self.client as c:
            with c.session_transaction() as sess:
                if "curr_user" in sess:
                    del sess["curr_user"]

            res = c.post(f'/accounts/{account_id}/delete', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger flash">Access unauthorized.</div>', html)

    def test_Account_id_wrong_user(self):
        """if wrong user in session, redirects home, flashes access unauthorized warning"""
        
        account_id = self.test_UFI.accounts[0].id
        wrong_id = self.test_user0.id + 1
        with self.client as c:
            with c.session_transaction() as sess:
                sess["curr_user"] = wrong_id

            res = c.post(f'/accounts/{account_id}/delete', follow_redirects=True)      
            html = res.get_data(as_text=True)

            self.assertIn('<div class="alert alert-danger flash">Access unauthorized.</div>', html)

    def test_Account_delete_success(self):
        """makes sure if proper owner is deleting an existing Account, the instance is taken out of the database access key is deleted"""     
        account_id = self.test_UFI.accounts[0].id
        account_name = self.test_UFI.accounts[0].name
        account_list_length = len(Account.query.all())
        expected_output = {
                            'dashboardBalanceNoLoan': 67942.74,
                            'dashboardBalanceWithLoan': -53621.32,
                            'id': self.test_UFI.id,
                            'message': {'category': 'success', 'message': 'Account Plaid Checking deleted!'},
                            'numAccounts': 8,
                            'pieChartData': "[[\"Institution Name\", \"Amount\"], [\"Test_name\", 67942.74]]",
                            'ufiBalanaceNoLoan': 67942.74,
                            'ufiBalanceWithLoan': -53621.32,
                        }

        with self.client as c:
            with c.session_transaction() as sess:
                sess["curr_user"] = self.test_user0.id

            
            res = c.post(f'/accounts/{account_id}/delete')      
            data = res.json
            self.assertEqual(data, expected_output)
            self.assertEqual(account_list_length-1, len(Account.query.all()))
    


