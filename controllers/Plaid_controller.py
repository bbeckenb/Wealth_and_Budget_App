from models.PlaidClient import PlaidClient
from flask import g

class PlaidController:
    """Controller for Plaid views"""      
    def __init__(self):
        pass

    @classmethod
    def token_gen(cls):
        plaid_inst = PlaidClient(g.user.account_type)
        return plaid_inst.create_plaid_link_token()
