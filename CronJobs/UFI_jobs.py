from models.UserFinancialInstitution import UserFinancialInstitute

def scheduled_daily_refresh_all_accounts():
    """Gets latest account balance information for all accounts in database from Plaid, updates them in database"""
    UFIs = UserFinancialInstitute.query.all()
    for UFI in UFIs:
        UFI.update_accounts_of_UFI(UFI.user.account_type)