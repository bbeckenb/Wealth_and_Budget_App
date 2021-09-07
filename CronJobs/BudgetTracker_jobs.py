from models import BudgetTracker

def scheduled_budget_tracker_jobs(plaid_inst, twilio_inst):
    """Gets amount spent information for all Accounts related to BudgetTrackers from Plaid, notifies users scheduled to be notified using twilio"""
    BudgetTracker.scheduled_daily_refresh_budgettrackers(plaid_inst)
    BudgetTracker.scheduled_daily_send_bt_notifications(twilio_inst)