from models import UserFinancialInstitute

def scheduled_daily_refresh_all_accounts(plaid_inst):
    UFIs = UserFinancialInstitute.query.all()
    for UFI in UFIs:
        UFI.update_accounts_of_UFI(plaid_inst)