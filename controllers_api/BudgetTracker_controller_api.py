from flask import g, jsonify
from models.BudgetTracker import BudgetTracker
import logging

class BudgetTrackerControllerAPI:
    """Controller for BudgetTracker views"""      
    def __init__(self):
        pass

    @classmethod
    def delete_specified_budget_tracker(cls, acct_id):
        """Deletes specified account instance from database"""
        if not g.user:
            message = {'message': "Access unauthorized.", 'category': "danger"}
            return jsonify({
                'message': message,
                'status_code': 401
            }), 401
        try:
            specified_bt = BudgetTracker.query.filter_by(user_id=g.user.id, account_id=acct_id).first()
            if not specified_bt:
                message = {'message': "BudgetTracker not in database.", 'category': "danger"}
                return jsonify({
                    'message': message,
                    'status_code': 400
                }), 400
            hold_acct_name = specified_bt.account.name
            specified_bt.delete_budget_tracker()
            message = {'message': f"Budget Tracker for {hold_acct_name} deleted!", 'category': "success"}
            status_code = 200
        except Exception as e:
            logging.error(f'delete_specified_budget_tracker: {e}')
            message = {'message': f"Something went wrong with the server: {e}", 'category': "danger"}
            status_code = 500
        return jsonify({
                        'message': message,
                        'status_code': status_code
                        }), status_code