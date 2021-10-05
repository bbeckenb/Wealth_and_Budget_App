from database.database import db
from models.Account import Account
from models.PlaidClient import PlaidClient

class UserFinancialInstitute(db.Model):
    """Model links Users to financial institutions as 'Items' (in Plaid API vocabulary) represents UserFinancialInstitute (UFI) instances in ORM (SQLAlchemy)
    -User is parent in one:many relationship
    -Accounts are children in one:many relationship"""
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
    
    @classmethod
    def create_new_UFI(cls, name:str, user_id:int, item_id:str, access_token:str, url:str, primary_color:str, logo:str):
        """generates, adds it to database, returns new UFI instance"""
        new_UFI = UserFinancialInstitute(
                                        name=name, 
                                        user_id=user_id, #g.user.id
                                        item_id=item_id,
                                        plaid_access_token=access_token,
                                        url=url,
                                        primary_color=primary_color,
                                        logo=logo

                  )
        db.session.add(new_UFI)
        db.session.commit()
        return new_UFI
   
    def delete_UFI(self, plaid_user_type:str) -> str:
        """Takes in MyPlaid class instance to be able to request information from the Plaid API. Sends plaid access token for UFI to Plaid server to eliminate it as a viable token, 
        deletes UFI instance from database. Returns response from Plaid server"""
        plaid_inst = PlaidClient(plaid_user_type)
        plaid_deletion_response = plaid_inst.close_out_UFI_access_key_with_Plaid(self.plaid_access_token)
        db.session.delete(self)
        db.session.commit()
        return plaid_deletion_response
        
    def populate_UFI_accounts(self, plaid_user_type:str):
        """Takes in MyPlaid class instance to be able to request information from the Plaid API. Makes call to plaid server to retrieve account information related to specified UFI.
        Properly harvests information from accounts based on type/subtype, creates Account class instances for all and enteres them into the database"""
        plaid_inst = PlaidClient(plaid_user_type)
        accounts = plaid_inst.get_UFI_Account_balances_from_Plaid(self.plaid_access_token)
        for account in accounts:
            budget_trackable = False
            if str(account['type']) == 'depository':
                available=account['balances']['available']
                current=account['balances']['current']
                limit=account['balances']['limit']
                if str(account['subtype']) in ['checking', 'paypal']:
                    budget_trackable = True
            elif str(account['type']) == 'credit':
                current=account['balances']['current']
                limit=account['balances']['limit']
                available=limit - current
                budget_trackable = True
            elif str(account['type']) in ['loan', 'investment']:
                available=account['balances']['available']
                current=account['balances']['current']
                limit=account['balances']['limit']
            if available:
                available = round(available, 2)
            if current:
                current = round(current, 2)
            if limit:
                limit = round(limit, 2)
            if current:             
                new_Account = Account(
                    name=account['name'],
                    UFI_id=self.id,
                    available=available,
                    current=current,
                    limit=limit,
                    type=str(account['type']),
                    subtype=str(account['subtype']),
                    account_id=str(account['account_id']),
                    budget_trackable=budget_trackable
                )
                db.session.add(new_Account)
                db.session.commit()

    def update_accounts_of_UFI(self, plaid_user_type:str):
        """Takes in MyPlaid class instance to be able to request information from the Plaid API. Grabs most up-to-date account balances
        from Plaid server for specified UFI, updates information in database"""
        account_ids=[]
        for account in self.accounts:
            account_ids.append(account.account_id)
        plaid_inst = PlaidClient(plaid_user_type)
        accounts = plaid_inst.get_UFI_specified_Account_balances_from_Plaid(account_ids, self.plaid_access_token)
        for account in accounts:
            if str(account['type']) == 'depository':
                available=account['balances']['available']
                current=account['balances']['current']
                limit=account['balances']['limit']
            elif str(account['type']) == 'credit':
                current=account['balances']['current']
                limit=account['balances']['limit']
                available=limit - current
            elif str(account['type']) in ['loan', 'investment']:
                available=account['balances']['available']
                current=account['balances']['current']
                limit=account['balances']['limit']    
            if available:
                available = round(available, 2)
            if current:
                current = round(current, 2)
            if limit:
                limit = round(limit, 2)
            update_account = Account.query.filter_by(account_id=account['account_id']).first()
            update_account.name = account['name']
            update_account.available = available
            update_account.current = current
            update_account.limit = limit
            db.session.add(update_account)
            db.session.commit()

    def aggregate_account_balances(self, with_loans:bool=False) -> float:
        """For specified UFI, sums all account balances, handles accounts of type 'depository', 'credit', 'investment', and 'loan'.
        Ignores loan balances based on input boolean"""
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
        return round(aggregated_balance, 2)

        