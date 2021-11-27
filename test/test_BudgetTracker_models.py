"""BudgetTracker Model tests."""
from unittest import TestCase
import app
from app import app
import datetime
from database.database import db
from models.User import User
from models.UserFinancialInstitution import UserFinancialInstitute
from models.PlaidClient import PlaidClient
from models.Account import Account
from models.BudgetTracker import BudgetTracker

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

class UserBudgetTrackerModelTestCase(TestCase):
    """Test methods for BudgetTracker model."""

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

    def test_BudgetTracker_model(self):
        """Does basic model work?"""
        self.test_budgettracker.delete_budget_tracker()
        num_BTs = len(BudgetTracker.query.all())
        u = BudgetTracker(account_id=self.test_account.id, 
                    user_id=self.test_user0.id, 
                    budget_threshold=45, 
                    notification_frequency=3, 
                    next_notification_date=datetime.datetime.today(),
                    amount_spent=20)

        db.session.add(u)
        db.session.commit()
        # Already one instance in from Test Setup
        self.assertEqual(num_BTs+1, len(BudgetTracker.query.all()))

    def test_BudgetTracker__repr__(self):
        """Checks what BudgetTracker.__repr__ outputs"""
        u = self.test_budgettracker

        self.assertEqual(repr(self.test_budgettracker), f"<BudgetTracker account_id={u.account_id} user_id={u.user_id} notification_freq={u.notification_frequency} next_notification_date={u.next_notification_date}>")

    def test_BudgetTracker_pretty_print(self):
        self.assertEqual(self.test_budgettracker.pretty_print_next_notify_date(), 
        f"{self.test_budgettracker.next_notification_date.month}-{self.test_budgettracker.next_notification_date.day}-{self.test_budgettracker.next_notification_date.year}")

    def test_delete_BudgetTracker(self):
        """Deletes specified BudgetTracker instance from the database"""
        self.test_budgettracker.delete_budget_tracker()
        num_BTs = len(BudgetTracker.query.all())
        u = BudgetTracker(account_id=self.test_account.id, 
                user_id=self.test_user0.id, 
                budget_threshold=45, 
                notification_frequency=3, 
                next_notification_date=datetime.datetime.today(),
                amount_spent=20)

        db.session.add(u)
        db.session.commit()

        self.assertEqual(num_BTs+1, len(BudgetTracker.query.all()))

        u.delete_budget_tracker()

        self.assertEqual(num_BTs, len(BudgetTracker.query.all()))