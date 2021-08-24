from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

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

    accounts = db.relationship('Account', cascade='all, delete, delete-orphan', backref='UFI')


    def __repr__(self):
        u=self
        return f"<UFI name={u.name} Uid={u.user_id} user_id={u.user_id}>"
    
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
    balance = db.Column(db.Integer,
                        nullable=False)
    budget_lim = db.Column(db.Integer,
                            default=0)
    budget_track = db.Column(db.Boolean, default=False)

    def __repr__(self):
        u=self
        return f"<Account name={u.name} id={u.id} UFI_id={u.UFI_id} balance={u.balance} budget_lim={u.budget_lim} budget_track?={u.budget_track}>"