from unittest import TestCase
import app
from app import app
from database.database import db
from models.User import User
from models.UserFinancialInstitution import UserFinancialInstitute
from models.PlaidClient import PlaidClient
from models.Account import Account
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

# Use test database and don't clutter tests with SQL
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

class UserModelTestCase(TestCase):
    """Tests for model for User."""

    def setUp(self):
        """Create test client, add sample data."""
        self.client = app.test_client()

        # Test User 0 
        test_user0 = User(  username='harrypotter', 
                            password='HASHED_PASSWORD',
                            phone_number='9999999999',
                            first_name='Harry',
                            last_name='Potter',
                            account_type='sandbox')
        db.session.add(test_user0)
        db.session.commit()
        self.test_user0 = test_user0

    def tearDown(self):
        """Clean up any fouled transaction"""
        User.query.delete()
        UserFinancialInstitute.query.delete()
        Account.query.delete()

    def test_User_model(self):
        """Does basic model work?"""

        u = User(   
                username='harrypotter1', 
                password='HASHED_PASSWORD',
                phone_number='9999993333',
                first_name='Harrison',
                last_name='Potterson',
                account_type='sandbox'
                )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.UFIs), 0)

    def test_user__repr__(self):
        """Checks what User.__repr__ outputs"""
        self.assertEqual(repr(self.test_user0), "<User username=harrypotter phone_number=9999999999 first_name=Harry last_name=Potter>")

    def test_user_class_signup_method(self):
        """Takes in required User inputs adds a new User instance to SQLAlchemy's staging area"""
        test_user1 = User.signup(
                                username='harrypotter1', 
                                password='HASHED_PASSWORD',
                                phone_number='9999993333',
                                first_name='Harrison',
                                last_name='Potterson',
                                account_type='sandbox'
                                )
        # ID will not be assigned until the new User instance is committed (will be None)
        self.assertIsNone(test_user1.id)

        # but other attributes should be available to check
        self.assertEqual(test_user1.username, 'harrypotter1')
        self.assertEqual(test_user1.phone_number, '9999993333')
        self.assertEqual(test_user1.first_name, 'Harrison')
        self.assertEqual(test_user1.last_name, 'Potterson')

        # Note password will be hashed so we will ensure it is not equivalent to the raw string input for the test user
        self.assertTrue(bcrypt.check_password_hash(test_user1.password, 'HASHED_PASSWORD'))

        # clear test_user1 from the staging area
        db.session.rollback()
        
    def test_user_class_method_authenticate(self):
        """Find user with `username` and `password`.
        This is a class method (call it on the class, not an individual user.)
        It searches for a user whose password hash matches this password
        and, if it finds such a user, returns that user object.
        If can't find matching user (or if password is wrong), returns False.
        """

        test_user1 = User.signup(
                    username='harrypotter1', 
                    password='HASHED_PASSWORD',
                    phone_number='9999993333',
                    first_name='Harrison',
                    last_name='Potterson',
                    account_type='sandbox'
                )
        db.session.commit()

        # Does User.authenticate successfully return a user when given a valid username and password?
        self.assertEqual(User.authenticate(test_user1.username, 'HASHED_PASSWORD'), test_user1)
        
        # Does User.authenticate fail to return a user when the username is invalid?
        self.assertFalse(User.authenticate('nottest_user1_username', 'HASHED_PASSWORD'))

        # Does User.authenticate fail to return a user when the password is invalid?
        self.assertFalse(User.authenticate(test_user1.username, 'notpassword'))

    def test_user_aggregate_UFI_balances(self):
        """Roll up of total wealth of a specified user. For all UserFinancialInstitutions (UFI) 
        instances owned by a specified user, the function aggregates all of the balances from 
        the Account instances owned by the UFI, then returns a sum of all aggregations. Includes 
        or ignores accounts with 'loan' type based on input boolean"""

        # test_user0 currently has no UFIs attached and therefore should have UFI balances of 0
        self.assertEqual(self.test_user0.aggregate_UFI_balances(), 0)

        # adding a UFI with test accounts
        test_UFI = UserFinancialInstitute(name='Test_name', 
                                    user_id=self.test_user0.id,
                                    item_id='test_item_id',
                                    plaid_access_token='test_plaid_access_key')
        db.session.add(test_UFI)
        db.session.commit()

        test_account_1 = Account(name = 'test_acct_1',
                                 UFI_id = test_UFI.id,
                                 available = 100,
                                 current = 20,
                                 limit = None,                  
                                 type = 'depository',
                                 subtype = 'checking',
                                 account_id = 'test_acct_1'
        )
        db.session.add(test_account_1)
        db.session.commit()

        test_account_2 = Account(name = 'test_acct_2',
                                 UFI_id = test_UFI.id,
                                 available = 10,
                                 current = 20,
                                 limit = None,                  
                                 type = 'loan',
                                 subtype = 'student',
                                 account_id = 'test_acct_2'
        )
        db.session.add(test_account_2)
        db.session.commit()

        # this tests with out loans, the second account is type loan, so it will be ignored
        self.assertEqual(self.test_user0.aggregate_UFI_balances(), 100)

        # this tests with loans, the second account is type loan, so it will subtract the current value from the sum
        self.assertEqual(self.test_user0.aggregate_UFI_balances(True), 80)

    def test_user_pie_chart_data(self):
        """Creates a usable dataset for Google Charts pie chart embedded in HTML. Dataset is an 
        array of arrays, each element of the main array contains [name of UFI (str), aggregated balance of its accounts (float)]
        This array is stringified to be stored on the user's HTML page as a string to be reconverted to its original form by javascript."""

        # test_user0 currently has no UFIs attached and therefore should have only the column titles element
        self.assertEqual(self.test_user0.pie_chart_data(), '[["Institution Name", "Amount"]]')

        # adding a UFI with test accounts
        test_UFI = UserFinancialInstitute(name='Test_name', 
                                    user_id=self.test_user0.id,
                                    item_id='test_item_id',
                                    plaid_access_token='test_plaid_access_key')
        db.session.add(test_UFI)
        db.session.commit()

        test_account_1 = Account(name = 'test_acct_1',
                                 UFI_id = test_UFI.id,
                                 available = 100,
                                 current = 20,
                                 limit = None,                  
                                 type = 'depository',
                                 subtype = 'checking',
                                 account_id = 'test_acct_1'
        )
        db.session.add(test_account_1)
        db.session.commit()

        test_account_2 = Account(name = 'test_acct_2',
                                 UFI_id = test_UFI.id,
                                 available = 10,
                                 current = 20,
                                 limit = None,                  
                                 type = 'loan',
                                 subtype = 'student',
                                 account_id = 'test_acct_2'
        )
        db.session.add(test_account_2)
        db.session.commit()

        # this tests with out loans, as it is used in the application. The second account is type loan, so it will be ignored
        self.assertEqual(self.test_user0.pie_chart_data(), '[["Institution Name", "Amount"], ["Test_name", 100.0]]')

    def test_delete_User(self):
        """Deletes specified User instance from the database"""
        # only test_user0 in test db
        self.assertEqual(len(User.query.all()), 1)

        self.test_user0.delete_User()

        self.assertEqual(len(User.query.all()), 0)

        
        