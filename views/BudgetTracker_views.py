from flask import render_template, flash, g, redirect
from models import BudgetTracker, Account, db
from forms import CreateBudgetTrackerForm, UpdateBudgetTrackerForm
import datetime
from datetime import timedelta

def create_new_budget_tracker(acct_id, plaid_inst):
    """Displays form for a user to enter parameters for a budget tracker for their account
        -If the account DNE, 404
        -If a user (in session or not) tries to add a budget tracker for an account they do not own, they are redirected to home with an error message
        -If a user does not enter all required information, it recycles the form with proper error messages
        -If a user does enter required information, it enters a new budget tracker into the database and sends a user to their dashboard
        -If a user tries to create a budgettracker for an account where one exists already, redirect home with error
    """
    specified_acct = Account.query.get_or_404(acct_id)
    UFI_of_acct = specified_acct.UFI
    if not g.user or UFI_of_acct not in g.user.UFIs:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    if not specified_acct.budget_trackable:
        flash("Account is not eligible for budget tracking.", "danger")
        return redirect("/")
    if specified_acct.budgettracker:
        flash("Budget Tracker already exists for this account.", "danger")
        return redirect("/")
    form = CreateBudgetTrackerForm()
    if form.validate_on_submit():
        today_date = datetime.datetime.today()
        if today_date.day == 1:
            amount_spent = 0
        else:
            amount_spent = specified_acct.get_amount_spent_for_account(today_date.replace(day=1), today_date, plaid_inst)
        try:
            new_budget_tracker = BudgetTracker(
                                                budget_threshold=form.budget_threshold.data,
                                                notification_frequency=form.notification_frequency.data,
                                                next_notification_date=(today_date+timedelta(days=form.notification_frequency.data)),
                                                amount_spent=amount_spent,
                                                account_id=specified_acct.id,
                                                user_id=g.user.id
                                                )
            db.session.add(new_budget_tracker)
            db.session.commit()
            flash(f"Budget Tracker for {specified_acct.name} created!", "success")
        except:
            flash("database error", 'danger') #DELETE
            return render_template('budget_tracker/create.html', form=form, account=specified_acct) 
        return redirect('/')
    else:
        return render_template('budget_tracker/create.html', form=form, account=specified_acct) 

def update_existing_budget_tracker(acct_id):
    """
    Displays form for a user to enter parameters for a budget tracker for their account
        -If the budget tracker DNE, 404
        -If a user (in session or not) tries to update a budget tracker they do not own, they are redirected to home with an error message
        -If a user does not enter all required information, it recycles the form with proper error messages
        -If a user does enter required information, it updates the budget tracker instance in the database and sends a user to their dashboard
        -If a user tries to create a budgettracker for an account where one exists already, redirect home with error
    """
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    specified_bt = BudgetTracker.query.filter_by(user_id=g.user.id, account_id=acct_id).first()
    if not specified_bt:
        flash("Budget Tracker not in database.", "danger")
        return redirect("/")
    form = UpdateBudgetTrackerForm()
    if form.validate_on_submit():
        try:
            today_date = datetime.datetime.today()
            specified_bt.budget_threshold=form.budget_threshold.data
            specified_bt.notification_frequency=form.notification_frequency.data
            specified_bt.next_notification_date=(today_date+timedelta(days=form.notification_frequency.data))
            db.session.add(specified_bt)
            db.session.commit()
            flash(f"Budget Tracker for {specified_bt.account.name} updated!", "info")
        except:
            flash("database error", 'danger') #DELETE
            return render_template('budget_tracker/update.html', form=form, account=specified_bt.account) 
        return redirect('/')
    else:
        return render_template('budget_tracker/update.html', form=form, account=specified_bt.account) 

def delete_specified_budget_tracker(acct_id):
    """Deletes specified account instance from database"""
    if not g.user:
        flash("Access unauthorized.", 'danger')
        return redirect('/')
    specified_bt = BudgetTracker.query.filter_by(user_id=g.user.id, account_id=acct_id).first()
    if not specified_bt:
        flash("Budget Tracker not in database.", "danger")
        return redirect("/")
    flash(f"Budget Tracker for {specified_bt.account.name} deleted!", "success")
    specified_bt.delete_budget_tracker()
    return redirect('/')