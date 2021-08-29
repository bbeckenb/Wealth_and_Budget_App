"""User View function tests."""

from unittest import TestCase

from flask import Flask, session, g
from app import app, CURR_USER_KEY
from models import db, User, UserFinancialInstitute, Account

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

class UserViewTestCase(TestCase):
    """Test views for messages."""

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

    def tearDown(self):
        """Clean up any fouled transaction"""
        User.query.delete()
        UserFinancialInstitute.query.delete()
        Account.query.delete()

    def test_home_without_user(self):
        """makes sure home page:
            -asks user to sign up/ login
        """
        with app.test_client() as client:
            res = client.get('/')
            html = res.get_data(as_text=True)
            
            self.assertEqual(res.status_code, 200)
            self.assertIn('Sign up here!</a>', html)
            self.assertIn('Log in</a>', html)

    # def test_home_with_user(self):
    #     """makes sure home page:
    #         -shows dashboard of overall wealth
    #         -shows mini-dashboards of individual financial institutions
    #             -mini dashboards are links that let users click to item page
    #         -allow user to log out
    #     """
    #     with app.test_client() as client:
    #         res = client.get('/')
    #         html = res.get_data(as_text=True)
            
    #         self.assertEqual(res.status_code, 200)
    #         self.assertIn('Sign up here!</a>', html)
    #         self.assertIn('Log in</a>', html)

    def test_signup_form_renders(self):
        """Make sure new user who enters required fields in sign up forms can be entered in database"""
        
        with self.client as c:
            with c.session_transaction() as sess:
                if CURR_USER_KEY in sess:
                    del sess[CURR_USER_KEY]

        with app.test_client() as client:    
            res = client.get('/signup')
            html = res.get_data(as_text=True)
            
            self.assertEqual(res.status_code, 200)
            self.assertIn('</form>', html)
            self.assertIn('<button class="btn btn-primary btn-lg">Register</button>', html)
        
    def test_signup_add_user_success(self):
        """Make sure new user who enters required fields in sign up forms 
        can be entered in database
        -redirects to user dashboard"""
        username = self.test_user0.username

        with self.client as c:
            with c.session_transaction() as sess:
                if CURR_USER_KEY in sess:
                    del sess[CURR_USER_KEY]
        d = {'username': username,
            'password':'HASHED_PASSWORD',
            'phone_number': '9991234567',
            'first_name': 'Hagrid',
            'last_name': 'Bagrid'}
        res = c.post(f"/signup", data=d, follow_redirects=True)
        html = res.get_data(as_text=True) 

        self.assertEqual(len(User.query.all()), 1) 
        self.assertIn('Username already taken', html)
    
    def test_signup_same_username_form_scenario(self):
        """Makes sure if new user requests same username existing in database
        -form is recycled
        -they are aware of same username scenario"""
        with self.client as c:
            with c.session_transaction() as sess:
                if CURR_USER_KEY in sess:
                    del sess[CURR_USER_KEY]
        d = {'username': 'hagrid1',
            'password':'HASHED_PASSWORD',
            'phone_number': '9991234567',
            'first_name': 'Hagrid',
            'last_name': 'Bagrid'}
        res = c.post(f"/signup", data=d, follow_redirects=True)
        html = res.get_data(as_text=True) 

        self.assertEqual(len(User.query.all()), 2) 
        self.assertIn('hagrid1 Dashboard</h1>', html)

    def test_signup_form_redirects_home_with_user(self):
        """Make sure if a user is in the session and tries to go to signup, it redirects home"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id
            # tests when a user is in session
   
            res = c.get('/signup')
            
            self.assertEqual(res.status_code, 302)

    def test_login_attempt_of_user_in_session_redirects(self):
        """Make sure if a user is in the session and tries to go to login, it redirects home"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id
            # tests when a user is in session
   
            res = c.get('/login')
            html = res.get_data(as_text=True)
            
            self.assertEqual(res.status_code, 302)

    def test_login_of_existing_user(self):
        """Makes sure if an existing user is not in the session and logs in
            -It successfully adds their info and displays it on home
            -it loads the user into the session"""
        user = User.signup(  username='harrypotter1', 
                            password='HASHED_PASSWORD',
                            phone_number='999-999-9999',
                            first_name='Harry',
                            last_name='Potter')
        db.session.commit()
        # tests when a user is in session
        d = {'username': user.username, 'password':'HASHED_PASSWORD'}

   
        with app.test_client() as client:
            res = client.post('/login', data=d, follow_redirects=True)
            html = res.get_data(as_text=True)
        
        self.assertIn('harrypotter1 Dashboard', html)
        # self.assertEqual(user.id, g.user.id) #NOT SURE HOW TO TEST USER WHO LOGS IN IS IN SESSION, WILL COME BACK

    def test_logout_no_user_in_session(self):
        """Makes sure if no user is in ession and they manually attempt to hit /logout
        they are redirected to home with a warning message"""
        with app.test_client() as client:
            res = client.get('/logout', follow_redirects=True)
            html = res.get_data(as_text=True)
        self.assertIn('No user in session', html)

    def test_logout_wit_user_in_session(self):
        """Makes sure if a user is in session, and they logout:
            -they are redirected home with options to sign up or login
            -their user instance is taken out of the session"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id
        
            res = c.get('/logout', follow_redirects=True)
            html = res.get_data(as_text=True)
        
        self.assertIn('Goodbye, harrypotter!', html)
        # self.assertNotIn(CURR_USER_KEY, sess) # Need to finish test by checking what is in session

    def test_update_user_form_render(self):
        """checks that the form to update user renders properly""" 
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id
        
            res = c.get('/users/update-profile', follow_redirects=True)
            html = res.get_data(as_text=True)
        
        self.assertIn('Update</button>', html)

    def test_update_user_form_no_user(self):
        """checks If no user present, reroute home with warning""" 
        with self.client as c:
            with c.session_transaction() as sess:
                if CURR_USER_KEY in sess:
                    del sess[CURR_USER_KEY]
        
            res = c.get('/users/update-profile', follow_redirects=True)
            html = res.get_data(as_text=True)
        
        self.assertIn('Access unauthorized.', html)

    def test_update_user_form_taken_username_scenario(self):
        """If desired username is taken, recycle form, notify user""" 
        user = User.signup( username='harrypotter1', 
                            password='HASHED_PASSWORD',
                            phone_number='9999999999',
                            first_name='Harry',
                            last_name='Potter')
        db.session.commit()

        d = {'username': self.test_user0.username, 
            'phone_number': user.phone_number,
            'password': 'HASHED_PASSWORD'}
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = user.id
        
            res = c.post('/users/update-profile', data=d, follow_redirects=True)
            html = res.get_data(as_text=True)
        
            self.assertIn('Username already taken', html)

    def test_update_user_form_wrong_password_scenario(self):
        """If password to authorize changes is incorrect, recycle form, notify user""" 
        user = User.signup( username='harrypotter1', 
                            password='HASHED_PASSWORD',
                            phone_number='9999999999',
                            first_name='Harry',
                            last_name='Potter')
        db.session.commit()

        d = {'username': 'harrypotter2', 
            'phone_number': user.phone_number,
            'password': 'WRONG_PASSWORD'}
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = user.id
        
            res = c.post('/users/update-profile', data=d, follow_redirects=True)
            html = res.get_data(as_text=True)
        
            self.assertIn('Incorrect password', html)

    def test_update_user_form_success(self):
        """If all form, password, username criteria satisfied, make desired changes to user, update database, redirect home"""
        user = User.signup( username='harrypotter1', 
                            password='HASHED_PASSWORD',
                            phone_number='9999999999',
                            first_name='Harry',
                            last_name='Potter')
        db.session.commit()

        d = {'username': 'harrypotter2', 
            'phone_number': user.phone_number,
            'password': 'HASHED_PASSWORD'}
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = user.id
        
            res = c.post('/users/update-profile', data=d, follow_redirects=True)
            html = res.get_data(as_text=True)
        
            self.assertIn('Profile successfully updated!', html)

    def test_delete_user_user_not_in_session(self):
        
        with self.client as c:
            with c.session_transaction() as sess:
                if CURR_USER_KEY in sess:
                    del sess[CURR_USER_KEY]
            res = c.post(f"/users/delete", follow_redirects=True)
            html = res.get_data(as_text=True)

            self.assertIn(f'<div class="alert alert-danger">Access unauthorized.</div>', html)

    def test_delete_user_success(self):
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.test_user0.id
            res = c.post(f"/users/delete", follow_redirects=True)
            html = res.get_data(as_text=True)

            self.assertEqual(len(User.query.all()), 0) #test_user0 was only user in test db
