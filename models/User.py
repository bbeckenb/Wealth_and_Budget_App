from database.database import db
from flask_bcrypt import Bcrypt
import json

bcrypt = Bcrypt()

class User(db.Model):
    """Model to represent User instances in ORM (SQLAlchemy)
    -UFIs are children in one:many relationship
    -BudgetTrackers are children in one:many relationship"""

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
    account_type = db.Column(db.String,
                        nullable=False,
                        default='sandbox')
    UFIs = db.relationship('UserFinancialInstitute', cascade='all, delete, delete-orphan', backref='user')
    budgettrackers = db.relationship('BudgetTracker', cascade='all, delete, delete-orphan', backref='user')


    def __repr__(self):
        u=self
        return f"<User username={u.username} phone_number={u.phone_number} first_name={u.first_name} last_name={u.last_name}>"

    @classmethod
    def signup(cls, username:str, password:str, phone_number:str, first_name:str, last_name:str, account_type:str):
        """Sign up user. Hashes password and adds user to database"""
        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')
        user = User(
            username=username,
            password=hashed_pwd,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name,
            account_type=account_type
        )
        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username:str, password:str):
        """Queries database for username, runs password client submitted through 
        the hashing function to ensure it produces the same output as what is stored 
        in database. If the ouput matches, it returns the requested User's instance.
        If it does not produce the same output, the function returns a boolean False"""
        user = cls.query.filter_by(username=username).first()
        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user
        return False

    def aggregate_UFI_balances(self, with_loans:bool=False) -> float:
        """Roll up of total wealth of a specified user. For all UserFinancialInstitutions (UFI) 
        instances owned by a specified user, the function aggregates all of the balances from 
        the Account instances owned by the UFI, then returns a sum of all aggregations. Includes 
        or ignores accounts with 'loan' type based on input boolean"""
        aggregated_balance=0
        for UFI in self.UFIs:
            aggregated_balance += UFI.aggregate_account_balances(with_loans)
        return round(aggregated_balance, 2)

    def pie_chart_data(self) -> str:
        """Creates a usable dataset for Google Charts pie chart embedded in HTML. Dataset is an 
        array of arrays, each element of the main array contains [name of UFI (str), aggregated balance of its accounts (float)]
        This array is stringified to be stored on the user's HTML page as a string to be reconverted to its original form by javascript."""
        UFI_data_array = []
        num_of_accounts = 0
        UFI_data_array.append(['Institution Name', 'Amount'])
        for UFI in self.UFIs:
            num_of_accounts += len(UFI.accounts)
            if UFI.aggregate_account_balances() > 0:
                UFI_data_array.append([UFI.name, UFI.aggregate_account_balances()])
        return False if num_of_accounts==0 or len(UFI_data_array)==1 else json.dumps(UFI_data_array)

    def delete_User(self):
        """Deletes specified User instance from the database"""
        db.session.delete(self)
        db.session.commit()