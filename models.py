from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_bcrypt import Bcrypt
import datetime
from datetime import timedelta, date
import time
db = SQLAlchemy()

bcrypt = Bcrypt()
# best practice to create function to establish connection and only call it once
def connect_db(app):
    db.app = app
    db.init_app(app)


# MODELS GO BELOW
class User(db.Model):
    """Model for users"""

    __tablename__ = 'users' #specifies table name

    id = db.Column(db.Integer,
                        primary_key=True,
                        autoincrement=True) #serial in sql
    username = db.Column(db.Text, 
                        nullable=False, 
                        unique=True)
    password = db.Column(db.Text,
                        nullable=False)
    phone_number = db.Column(db.String,
                            nullable=False)
    
    first_name = db.Column(db.Text,
                        nullable=False)

    last_name = db.Column(db.Text,
                        nullable=False)

    UFIs = db.relationship('UserFinancialInstitute', cascade='all, delete, delete-orphan', backref='user')

    budgettrackers = db.relationship('BudgetTracker', cascade='all, delete, delete-orphan', backref='user')

    @classmethod
    def signup(cls, username, password, phone_number, first_name, last_name):
        """Sign up user.

        Hashes password and adds user to system.
        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')

        user = User(
            username=username,
            password=hashed_pwd,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name
        )

        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username, password):
        """Find user with `username` and `password`.

        This is a class method (call it on the class, not an individual user.)
        It searches for a user whose password hash matches this password
        and, if it finds such a user, returns that user object.

        If can't find matching user (or if password is wrong), returns False.
        """

        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False

    def __repr__(self):
        u=self
        return f"<User username={u.username} phone_number={u.phone_number} first_name={u.first_name} last_name={u.last_name}>"

    def aggregate_UFI_balances(self, with_loans=False):
        aggregated_balance=0
        for UFI in self.UFIs:
            aggregated_balance += UFI.aggregate_account_balances(with_loans)
        return aggregated_balance

class UserFinancialInstitute(db.Model):
    """Model links Users to financial institutions as 'Items' (in Plaid API vocabulary)"""
    __tablename__ = 'users_financial_institutions'

    id = db.Column(db.Integer,
                        primary_key=True,
                        autoincrement=True) #serial in sql
    name = db.Column(db.String,
                        nullable=False) #SHOULD NAME AND USER ID BOTH BE PK's?
    user_id = db.Column(db.Integer, 
                        db.ForeignKey('users.id', ondelete='CASCADE'), 
                        nullable=False)
    item_id = db.Column(db.String, nullable=False)
    plaid_access_token = db.Column(db.String, nullable=False)
    url=db.Column(db.Text, default=None)
    logo = db.Column(db.Text, default=None) 
    primary_color=db.Column(db.Text, default=None)
    accounts = db.relationship('Account', cascade='all, delete, delete-orphan', backref='UFI')


    def __repr__(self):
        u=self
        return f"<UFI name={u.name} user_id={u.user_id}>"
    
    def aggregate_account_balances(self, with_loans=False):
        aggregated_balance = 0
        for account in self.accounts:
            if account.type == 'depository':
                if account.available:
                    aggregated_balance += account.available #for savings and checking, this is the most up to date value accounting for outstanding charges that are not fully processed
                else:
                    aggregated_balance += account.current #other 'depository' accounts like money market accounts do not have an 'available' amount so we need to use 'current'
            elif account.type == 'credit':
                aggregated_balance -= account.current #for 'credit' accounts, 'current' is what is owed to the financial institution
            elif account.type == 'investment':
                aggregated_balance += account.current
            elif account.type == 'loan':
                if with_loans:
                    aggregated_balance -= account.current #for 'loan' accounts, the 'current' value representings the outstanding amount still owed for the loan
        return aggregated_balance

class Account(db.Model):
    """Model representing associated accounts from a UFI"""
    __tablename__ = 'accounts'

    id = db.Column(db.Integer,
                        primary_key=True,
                        autoincrement=True) #serial in sql
    name = db.Column(db.String,
                        nullable=False)
    UFI_id = db.Column(db.Integer,
                        db.ForeignKey('users_financial_institutions.id', ondelete='CASCADE'),
                        nullable=False)
    available = db.Column(db.Float)
    current = db.Column(db.Float,
                        nullable=False)
    limit = db.Column(db.Float)                   
    type = db.Column(db.Text,
                        nullable=False)
    subtype = db.Column(db.Text,
                        nullable=False)
    account_id=db.Column(db.Text,
                        nullable=False)
    budget_trackable = db.Column(db.Boolean, default=False)

    budgettracker = db.relationship('BudgetTracker', cascade='all, delete, delete-orphan', backref='account')

    def __repr__(self):
        u=self
        return f"<Account name={u.name} id={u.id} UFI_id={u.UFI_id} available={u.available} current={u.current} limit={u.limit}>"


class BudgetTracker(db.Model):
    """Model representing budget tracker of a specific account"""
    __tablename__ = 'budget_trackers'

    account_id = db.Column(db.Integer,
                        db.ForeignKey('accounts.id', ondelete='CASCADE'),
                        nullable=False, primary_key=True)
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id', ondelete='CASCADE'),
                        nullable=False, primary_key=True)
    budget_threshold = db.Column(db.Float,
                                nullable=False)
    notification_frequency = db.Column(db.Integer,
                                        nullable=False,
                                        default=5)
    next_notification_date = db.Column(db.DateTime, 
                                        nullable=False)
    amount_spent = db.Column(db.Float,
                                    nullable=False,
                                    default=0)
    
    def __repr__(self):
        u=self
        return f"<BudgetTracker account_id={u.account_id} user_id={u.user_id} notification_freq={u.notification_frequency} next_notification_date={u.next_notification_date}>"

    @classmethod
    def find_all_scheduled_today(cls):
        """filters budgettrackers by 'next_notification_date', all budget trackers 
            with a 'next_notification_date' equal to that day will be returned"""
        return cls.query.filter(func.date(cls.next_notification_date) == date.today()).all()

    # def update_amount_spent(self):
    #     today_date = datetime.datetime.today()
    #     if today_date.day == 1:
    #         amount_spent = 0
    #     else:
    #         amount_spent = get_amount_spent_for_account(self.account, today_date.replace(day=1), today_date)
    #     self.amount_spent = amount_spent
    #     db.session.add(bt)
    #     db.session.commit()
    
    def update_next_notify_date(self):
        self.next_notification_date = self.next_notification_date + timedelta(days=self.notification_frequency)
