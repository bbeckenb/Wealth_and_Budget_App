from flask import flash, g, redirect
from models import UserFinancialInstitute

def get_plaid_access_key_create_UFI(plaid_inst):
    access_token, item_id = plaid_inst.exchange_public_token_generate_access_token()
    institution = plaid_inst.get_UFI_info_from_Plaid(access_token)
    print(institution)
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
    this_UFI = UserFinancialInstitute.query.get_or_404(UFI_id)
    this_UFI.update_accounts_of_UFI(plaid_inst)
    return redirect('/')


