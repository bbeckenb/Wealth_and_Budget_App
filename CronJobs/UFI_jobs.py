from models import UserFinancialInstitute

def scheduled_daily_refresh_all_accounts(plaid_inst):
    """Gets latest account balance information for all accounts in database from Plaid, updates them in database"""
    UFIs = UserFinancialInstitute.query.all()
    for UFI in UFIs:
        UFI.update_accounts_of_UFI(plaid_inst)