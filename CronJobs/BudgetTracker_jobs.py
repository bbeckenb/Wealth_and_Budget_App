from models.BudgetTracker import BudgetTracker
import logging

def scheduled_budget_tracker_jobs():
    """Gets amount spent information for all Accounts related to BudgetTrackers from Plaid, notifies users scheduled to be notified using twilio"""
    try:
        BudgetTracker.scheduled_daily_refresh_budgettrackers()
        BudgetTracker.scheduled_daily_send_bt_notifications()
    except Exception as e:
        logging.error(f'scheduled_budget_tracker_jobs: {e}') 