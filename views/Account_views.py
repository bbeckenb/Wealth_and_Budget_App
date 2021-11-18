from flask import flash, g, redirect, jsonify
from models.Account import Account
from models.UserFinancialInstitution import UserFinancialInstitute
from datetime import datetime

class AccountController:
    """Controller for Account views"""      
    def __init__(self):
        pass
    
    @classmethod
    def populate_accounts_of_UFI(cls, UFI_id):
        """Populates accounts of specified UFI"""
        UFI = UserFinancialInstitute.query.get_or_404(UFI_id)
        UFI_owner_id = UFI.user_id
        if not g.user or UFI_owner_id != g.user.id:
            flash("Access unauthorized.", 'danger')
            return redirect('/')
        try:
            then = datetime.now()
            print(f'+++++++++++++++++++{datetime.now()}')
            accounts_out = UFI.populate_UFI_accounts(g.user.account_type)
            now = datetime.now()
            print(f'+++++++++++++++++++{datetime.now()}')
            print(f'+++++++++++++++++++{now-then} seconds')
            message = {'message': f"Successfully populated accounts of {UFI.name}!", 'category': "success"}
        except Exception as e:
            message = {'message': f"Something went wrong with the server: {e}", 'category': "danger"}
        return jsonify({'accounts': accounts_out,
                        'id':UFI.id,
                        'accountBalNoLoan': UFI.aggregate_account_balances(),
                        'accountBalWithLoan': UFI.aggregate_account_balances(with_loans=True),
                        'name': UFI.name,
                        'userId': UFI.user_id,
                        'dashboardBalanceNoLoan': g.user.aggregate_UFI_balances(),
                        'dashboardBalanceWithLoan': g.user.aggregate_UFI_balances(with_loans=True),
                        'pieChartData': g.user.pie_chart_data(),
                        'message': message
                        })


    @classmethod
    def delete_specified_account(cls, acct_id):
        """Deletes specified account instance from database"""
        acct_to_delete = Account.query.get_or_404(acct_id)
        UFI = acct_to_delete.UFI
        acct_owner_id = UFI.user_id
        if not g.user or acct_owner_id != g.user.id:
            flash("Access unauthorized.", 'danger')
            return redirect('/')
        try:
            acct_to_delete.delete_Account()
            message = {'message': f"Account {acct_to_delete.name} deleted!", 'category': "success"}
        except Exception as e:
            message = {'message': f"Something went wrong when attempting to delete {acct_to_delete.name}: {e}", 'category': "danger"}
        return jsonify({
                        'dashboardBalanceNoLoan': g.user.aggregate_UFI_balances(),
                        'dashboardBalanceWithLoan': g.user.aggregate_UFI_balances(with_loans=True),
                        'pieChartData': g.user.pie_chart_data(),
                        'id':UFI.id,
                        'numAccounts':len(UFI.accounts),
                        'ufiBalanaceNoLoan': UFI.aggregate_account_balances(),
                        'ufiBalanceWithLoan': UFI.aggregate_account_balances(with_loans=True),
                        'message': message
                        })