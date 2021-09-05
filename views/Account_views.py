from flask import render_template, flash, g, redirect, session
from models import Account

def delete_specified_account(acct_id):
    acct_to_delete = Account.query.get_or_404(acct_id)
    UFI = acct_to_delete.UFI
    acct_owner_id = UFI.user_id
    if not g.user or acct_owner_id != g.user.id:
        flash("Access unauthorized.", 'danger')
        return redirect('/')
    acct_to_delete.delete_Account()
    return redirect('/')