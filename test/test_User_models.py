from unittest import TestCase
import app
from app import app
from database.database import db
from models.User import User
from models.UserFinancialInstitution import UserFinancialInstitute
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