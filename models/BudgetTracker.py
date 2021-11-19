from database.database import db
from sqlalchemy import func
from models.TwilioClient import TwilioClient
import datetime
from datetime import timedelta, date


class BudgetTracker(db.Model):
    """Model to represent BudgetTracker instances in ORM (SQLAlchemy)
    -User is parent in one:many relationship
    -one:one relationship with Accounts"""
    __tablename__ = 'budget_trackers'
    account_id = db.Column(db.Integer,
                        db.ForeignKey('accounts.id', ondelete='CASCADE'),
                        nullable=False, primary_key=True)
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id', ondelete='CASCADE'),
                        nullable=False, primary_key=True)
    budget_threshold = db.Column(db.Float,
                                nullable=False)
    notification_frequency = db.Column(db.Integer,
                                        nullable=False,
                                        default=5)
    next_notification_date = db.Column(db.DateTime, 
                                        nullable=False)
    amount_spent = db.Column(db.Float,
                             nullable=False,
                             default=0)
    
    def __repr__(self):
        u=self
        return f"<BudgetTracker account_id={u.account_id} user_id={u.user_id} notification_freq={u.notification_frequency} next_notification_date={u.next_notification_date}>"

    @classmethod
    def find_all_scheduled_today(cls) -> list:
        """filters budgettrackers by 'next_notification_date', all budget trackers 
            with a 'next_notification_date' equal to that day will be returned"""
        return cls.query.filter(func.date(cls.next_notification_date) == date.today()).all()

    @classmethod
    def scheduled_daily_refresh_budgettrackers(cls):
        """Takes in MyPlaid class instance to be able to request information from the Plaid API.
        For every BudgetTracker, the function queries the Plaid server for the most up-to-date 
        'amount spent' information for the associated account. This information is updated for 
        each budget tracker in the database"""
        budgettrackers = cls.query.all()
        for bt in budgettrackers:
            today_date = datetime.datetime.today()
            if today_date.day == 1:
                amount_spent = 0
            else:
                amount_spent = bt.account.get_amount_spent_for_account(today_date.replace(day=1), today_date, bt.user.account_type)
            bt.amount_spent = amount_spent
            db.session.add(bt)
            db.session.commit()
    
    @classmethod
    def scheduled_daily_send_bt_notifications(cls):
        """Searches database for BudgetTracker instances due to notify their users.
        Pulls phone number from associated User instances, utilizes Twilio client represented by twilio_inst
        to send text to the users. Based on notification frequency requested by each individual User, associated 
        'next_notification_dates' are updated on each budget tracker"""
        bt_scheduled_for_notif = cls.find_all_scheduled_today()
        twilio_inst = TwilioClient()
        for bt in bt_scheduled_for_notif:
            if bt.user.account_type == 'development':
                phone_number = bt.user.phone_number
                msg = f'BudgetTracker for {bt.account.name}\nYou have spent ${bt.amount_spent} of your ${bt.budget_threshold} budget threshold.'
                twilio_inst.send_text(phone_number,msg)
            bt.update_next_notify_date()

    def update_amount_spent(self, plaid_user_type:str):
        """Takes in MyPlaid class instance to be able to request information from the Plaid API. 
        Gets amount spent for associated Account of specified BudgetTracker, updates 'amount_spent' 
        on BudgetTracker and updates value in database"""
        today_date = datetime.datetime.today()
        if today_date.day == 1:
            amount_spent = 0
        else:
            amount_spent = self.account.get_amount_spent_for_account(today_date.replace(day=1), today_date, plaid_user_type)
        self.amount_spent = amount_spent
        db.session.add(self)
        db.session.commit()
    
    def update_next_notify_date(self):
        """Based on notification frequency requested by User, associated 
            'next_notification_date' is updated on specified budget tracker and the database is updated"""
        self.next_notification_date = self.next_notification_date + timedelta(days=self.notification_frequency)
        db.session.add(self)
        db.session.commit()

    def pretty_print_next_notify_date(self) -> str:
        """Formats 'next_notification_date' in a cleaner more prentable fashion -> 'month-day-year'"""
        return f"{self.next_notification_date.month}-{self.next_notification_date.day}-{self.next_notification_date.year}"

    def delete_budget_tracker(self):
        """Deletes BudgetTracker instance from database"""
        db.session.delete(self)
        db.session.commit()