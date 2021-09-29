from CronJobs.UFI_jobs import scheduled_daily_refresh_all_accounts
from CronJobs.BudgetTracker_jobs import scheduled_budget_tracker_jobs
from dotenv import load_dotenv
from app import app
load_dotenv()

with app.app_context():
    scheduled_daily_refresh_all_accounts()
    scheduled_budget_tracker_jobs()