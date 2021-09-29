from plaid.model.accounts_balance_get_request_options import AccountsBalanceGetRequestOptions
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.api import plaid_api
from datetime import timedelta, date
import datetime
import time
import plaid
import json
from flask import jsonify, request
import os

class PlaidClient:
    """Class to represent my connection to Plaid and house methods to call their API for this application"""
    def __init__(self, plaid_env='sandbox'):
        self.plaid_client = self.create_plaid_client(plaid_env)
        
    def create_plaid_client(self, environment='sandbox'):
        """Establishes plaid client to enable app to communicate with Plaid server in 'sandbox' or 'development' mode"""
        if environment == 'development':
            host = plaid.Environment.Development 
            secret = os.getenv('PLAID_SECRET')
        else:
            host = plaid.Environment.Sandbox
            secret = '0aae90632ad426c5d97740c670814f' #sandbox key
        configuration = plaid.Configuration(
            host=host,
            api_key={
                'clientId': os.getenv('PLAID_CLIENT_ID'),
                'secret': secret,
                'plaidVersion': '2020-09-14'
            }
        )
        api_client = plaid.ApiClient(configuration)
        plaid_client = plaid_api.PlaidApi(api_client)
        return plaid_client
  
    def get_UFI_info_from_Plaid(self, access_token) -> dict:
            """retrieves institution name, website, logo, and color to create UFI instance"""
            item_request = ItemGetRequest(access_token=access_token)
            item_response = self.plaid_client.item_get(item_request)
            institution_request = InstitutionsGetByIdRequest(
                institution_id=item_response['item']['institution_id'],
                country_codes=list(map(lambda x: CountryCode(x), os.getenv('PLAID_COUNTRY_CODES', 'US').split(',')))
            )
            institution_response = self.plaid_client.institutions_get_by_id(institution_request)
            return institution_response['institution']

    def create_plaid_link_token(self):
        """Stage 1 server side of token passing process for UFI access token security"""
        try:
            products = []
            for product in os.getenv('PLAID_PRODUCTS', 'transactions').split(','):
                products.append(Products(product))
            request = LinkTokenCreateRequest(
                                            products=products,
                                            client_name="W_and_B_app",
                                            country_codes=list(map(lambda x: CountryCode(x), os.getenv('PLAID_COUNTRY_CODES', 'US').split(','))),
                                            language='en',
                                            user=LinkTokenCreateRequestUser(
                                                                            client_user_id=str(time.time())
                                                 )
                      )
            response = self.plaid_client.link_token_create(request)
            return jsonify(response.to_dict())
        except plaid.ApiException as e:
            return json.loads(e.body)

    def exchange_public_token_generate_access_token(self):
        """Stage 2 server side of token passing process for UFI access token security""" 
        public_token = request.form['public_token']
        req = ItemPublicTokenExchangeRequest(
            public_token=public_token
        )
        response = self.plaid_client.item_public_token_exchange(req)
        access_token = response['access_token']
        item_id = response['item_id']
        return access_token, item_id   
    
    def close_out_UFI_access_key_with_Plaid(self, access_token:str) -> dict:
        """Destroys an item's access token on Plaid's server"""
        request = ItemRemoveRequest(access_token=access_token)
        response = self.plaid_client.item_remove(request)
        return response

    def get_UFI_Account_balances_from_Plaid(self, access_token:str) -> dict:
        """Passes a UFI's access token to Plaid Server, retrieves account balances of all Accounts associated with UFI"""
        request = AccountsBalanceGetRequest(access_token=access_token)
        response = self.plaid_client.accounts_balance_get(request)
        accounts = response['accounts']
        return accounts

    def get_UFI_specified_Account_balances_from_Plaid(self, account_ids:list, access_token:str) -> dict:
        """Passes a UFI's access token and specific account IDs to Plaid Server, retrieves account balances for specified Accounts associated with UFI"""
        request = AccountsBalanceGetRequest(
                                            access_token=access_token,
                                            options=AccountsBalanceGetRequestOptions(
                                                                                     account_ids=account_ids
                                                    )
                    )
        response = self.plaid_client.accounts_balance_get(request)
        accounts = response['accounts']
        return accounts

    def get_Account_transactions_from_Plaid(self, access_token:str, start:datetime, end:datetime, account_id:str) -> dict:
        """Passes UFI access token, start date, end date, and specified Account ID to Plaid, retrieves transactions for specified account in date range"""
        request = TransactionsGetRequest(
                                        access_token=access_token,
                                        start_date=start.date(),
                                        end_date=end.date(),
                                        options=TransactionsGetRequestOptions(account_ids=[account_id])
                    )
        response = self.plaid_client.transactions_get(request)
        transactions = response['transactions']
        return transactions

    def createTestUFIToken(self):
        pt_request = SandboxPublicTokenCreateRequest(
                                    institution_id='ins_109508',
                                    initial_products=[Products('transactions')]
                    )
        pt_response = self.plaid_client.sandbox_public_token_create(pt_request)
        # The generated public_token can now be
        # exchanged for an access_token
        exchange_request = ItemPublicTokenExchangeRequest(
                                    public_token=pt_response['public_token']
                            )
        exchange_response = self.plaid_client.item_public_token_exchange(exchange_request)
        return exchange_response['access_token']