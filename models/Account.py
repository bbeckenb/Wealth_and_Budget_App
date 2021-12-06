from database.database import db
from models.PlaidClient import PlaidClient
import datetime

class Account(db.Model):
    """Model to represent Account instances in ORM (SQLAlchemy)
    -UFI is parent in one:many relationship
    -one:one relationship with BudgetTrackers"""

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
    current = db.Column(db.Float)
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

    def get_amount_spent_for_account(self, start:datetime, end:datetime, plaid_user_type:str) -> float:
        """Takes in MyPlaid class instance to be able to request information from the Plaid API. 
        Grabs transaction information for specified account from Plaid API between requested 'start' and 'end' dates. 
        Adds costs of transactions and returns the sum"""
        access_token=self.UFI.plaid_access_token
        plaid_inst = PlaidClient(plaid_user_type)
        transactions = plaid_inst.get_Account_transactions_from_Plaid(access_token, start, end, self.account_id)
        omit_categories = ["Transfer", "Credit Card", "Deposit", "Payment"]
        amount_spent=0
        for transaction in transactions:
            category_allowed=True
            for category in transaction['category']:
                if category in omit_categories:
                    category_allowed=False
            if category_allowed and transaction['amount'] > 0:
                print(transaction['category'])
                amount_spent+=transaction['amount']
        return round(amount_spent,2)

    def delete_Account(self):
        """Deletes account instance from the database"""
        db.session.delete(self)
        db.session.commit()