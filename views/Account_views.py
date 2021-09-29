from flask import flash, g, redirect
from models.Account import Account

class AccountController:
    """Controller for Account views"""      
    def __init__(self):
        pass
    
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
            flash(f"Account {acct_to_delete.name} deleted!", "success")
        except:
            flash(f"Something went wrong when attempting to delete {acct_to_delete.name}.", "danger")
        return redirect('/')