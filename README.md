Title - CashView: Pull in and view your financial data in one place! - https://wealth-and-budget.herokuapp.com/

Description:
This website acts as a personal finance dashboard. Powered by the Plaid API (https://plaid.com/docs/api/), it allows users to make a profile and pull financial data from all of their financial institutions into one place. The app itself aggregates balances from all of the user's accounts, displaying their overall worth (with and without loans). It also uses graphics to illustrate the breakdown of the user's financial institutions and what percentage of their overall wealth is in each. Below the dashboard there is an account-level breakdown of each financial institution listed that displays the individual balances based on account type.

Features:
1. Full CRUD on all resources (User, UserFinancialInstitution, Account, BudgetTracker)
2. User password encryption through Bcrypt for authentication
3. Capability to securely pull financial institutions into application through Plaid 
4. Displays aggregated information of all financial institutions for quick view, aggregate of all accounts at singular financial institution, and more granular breakdown of each account
5. Displays graphical 3D pie-chart breakdown of where a user's wealth is
6. Capability to create a customized BudgetTracker with desired budget threshold and notification frequency for eligible accounts (type: credit or sub-type: checking)
7. Scheduled auto-update of all accounts, grabbing the most recent account balance information daily
8. Scheduled auto-notification SMS with most up to date 'amount spent' out of 'budget threshold' for users for budget tracking through Plaid and Twilio

Standard User Flow:
1. User signs-up or logs in
2. User views dashboard where they:
    - add their financial institution/s
    - create/update BudgetTrackers for desired accounts
    - update their user profile information 
    - logout or delete profile

APIs integrated:
Plaid - https://plaid.com/docs/api/versioning/
Twilio - https://www.twilio.com/docs

Stack:
    Front-end: HTML, CSS, JavaScript
    Back-end: Python, Flask, SQLAlchemy
    Database: Postgres