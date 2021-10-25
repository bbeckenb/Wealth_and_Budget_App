from flask import flash, g, redirect, jsonify
from models.PlaidClient import PlaidClient
from models.UserFinancialInstitution import UserFinancialInstitute
import asyncio

class UFIController:
    """Controller for UFI views"""      
    def __init__(self):
        pass

    @classmethod
    def get_plaid_access_key_create_UFI(cls):
        """Retrieves public_access_token and UFI information from Plaid server, creates UFI instance, adds it to database"""
        try:
            plaid_inst = PlaidClient(g.user.account_type)
            access_token, item_id = plaid_inst.exchange_public_token_generate_access_token()
            institution = plaid_inst.get_UFI_info_from_Plaid(access_token)
            new_UFI = UserFinancialInstitute.create_new_UFI(
                                                            name=institution['name'],
                                                            user_id=g.user.id,
                                                            item_id=item_id,
                                                            access_token=access_token,
                                                            url=institution.get('url', None),
                                                            primary_color=institution.get('primary_color', None),
                                                            logo=institution.get('logo', None)
                                            )
            accounts_out = new_UFI.populate_UFI_accounts(g.user.account_type) 
            flash(f"Connection to {new_UFI.name} successfully made, accounts populated!", "success")
        except:
            flash("Something went wrong when attempting to link this financial institution.", 'danger')
        return jsonify({'accounts': accounts_out,
                        'id':new_UFI.id,
                        'accountBalNoLoan': new_UFI.aggregate_account_balances(),
                        'accountBalWithLoan': new_UFI.aggregate_account_balances(with_loans=True),
                        'name': new_UFI.name,
                        'userId': new_UFI.user_id,
                        'dashboardBalanceNoLoan': g.user.aggregate_UFI_balances(),
                        'dashboardBalanceWithLoan': g.user.aggregate_UFI_balances(with_loans=True),
                        'pieChartData': g.user.pie_chart_data()
                        })
        

    @classmethod
    def delete_UFI_instance(cls, UFI_id):
        """Deletes specified instance of UFI from database
        If:
        -no user or wrong user present, redirect home, flash warning
        -UFI_id DNE, 404   
        """
        UFI_to_del = UserFinancialInstitute.query.get_or_404(UFI_id)
        UFI_owner_id = UFI_to_del.user_id
        if not g.user or UFI_owner_id != g.user.id:
            flash("Access unauthorized.", 'danger')
            return redirect('/')
        holdName = UFI_to_del.name
        try:
            UFI_to_del.delete_UFI(g.user.account_type)
            flash(f"Your connection to {holdName} was removed and the access_token is now invalid", 'success')
        except:
            flash("Something went wrong when delete was attempted.", 'danger')
        return jsonify({'msg': f"UFI {UFI_id} deleted",
                        'dashboardBalanceNoLoan': g.user.aggregate_UFI_balances(),
                        'dashboardBalanceWithLoan': g.user.aggregate_UFI_balances(with_loans=True),
                        'pieChartData': g.user.pie_chart_data()
                        })

    @classmethod
    def update_UFI_Accounts(cls, UFI_id):
        """Queries database for specific UFI, pullas all accounts related to it, requests most up-to-date balance information, updates Account instance information in database"""
        this_UFI = UserFinancialInstitute.query.get_or_404(UFI_id)
        try:
            if (len(this_UFI.accounts) > 0):
                accounts_out = this_UFI.update_accounts_of_UFI(g.user.account_type)
                flash(f"Accounts of {this_UFI.name} updated!", "info")
                payload = {
                            'accounts': accounts_out,
                            'id':this_UFI.id,
                            'accountBalNoLoan': this_UFI.aggregate_account_balances(),
                            'accountBalWithLoan': this_UFI.aggregate_account_balances(with_loans=True),
                            'name': this_UFI.name,
                            'userId': this_UFI.user_id,
                            'dashboardBalanceNoLoan': g.user.aggregate_UFI_balances(),
                            'dashboardBalanceWithLoan': g.user.aggregate_UFI_balances(with_loans=True),
                            'pieChartData': g.user.pie_chart_data()
                        }
            else:
                flash(f"No accounts to update!", "info")
                payload = {'msg': 'No accounts to update!'}
        except:
            flash("Something went wrong when account update was attempted.", 'danger')
        return jsonify(payload)

