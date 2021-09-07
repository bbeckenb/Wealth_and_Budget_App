from flask import flash, g, redirect
from plaid.api.plaid_api import PlaidApi
from models import UserFinancialInstitute

def get_plaid_access_key_create_UFI(plaid_inst: PlaidApi):
    """Retrieves public_access_token and UFI information from Plaid server, creates UFI instance, adds it to database"""
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
    new_UFI.populate_UFI_accounts(plaid_inst)
    flash(f"Connection to {new_UFI.name} successfully made, accounts populated!", "success")
    return redirect('/')

def delete_UFI_instance(UFI_id, plaid_inst):
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
    flash(f"Your connection to {UFI_to_del.name} was removed and the access_token is now invalid", 'success')
    UFI_to_del.delete_UFI(plaid_inst)
    return redirect('/')

def update_UFI_Accounts(UFI_id, plaid_inst):
    """Queries database for specific UFI, pullas all accounts related to it, requests most up-to-date balance information, updates Account instance information in database"""
    this_UFI = UserFinancialInstitute.query.get_or_404(UFI_id)
    this_UFI.update_accounts_of_UFI(plaid_inst)
    flash(f"Accounts of {this_UFI.name} updated!", "info")
    return redirect('/')


