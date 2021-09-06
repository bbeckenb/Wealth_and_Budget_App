from models import MyPlaid, MyTwilio
from CronJobs.UFI_jobs import scheduled_daily_refresh_all_accounts
from CronJobs.BudgetTracker_jobs import scheduled_budget_tracker_jobs

plaid_inst = MyPlaid('development')
twilio_inst = MyTwilio()

scheduled_daily_refresh_all_accounts(plaid_inst)
scheduled_budget_tracker_jobs(plaid_inst, twilio_inst)