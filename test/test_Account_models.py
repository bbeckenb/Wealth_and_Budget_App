"""Account Model tests."""
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

class UserAccountModelTestCase(TestCase):
    """Test methods for Account model."""

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

    def test_Account_model(self):
        """Does basic model work?"""
        num_accts = len(Account.query.all())
        u = Account(name='n1', 
                    UFI_id=self.test_UFI.id, 
                    available=10, current=10, 
                    limit=None, type='depository', 
                    subtype='checking', 
                    account_id='X', 
                    budget_trackable=True)

        db.session.add(u)
        db.session.commit()
        # Already one instance in from Test Setup
        self.assertEqual(num_accts+1, len(Account.query.all()))

    def test_user__repr__(self):
        """Checks what User.__repr__ outputs"""
        u = self.test_UFI.accounts[0]

        self.assertEqual(repr(self.test_UFI.accounts[0]), f"<Account name={u.name} id={u.id} UFI_id={u.UFI_id} available={u.available} current={u.current} limit={u.limit}>")

    # def get_amount_spent_for_account(account, start, end)