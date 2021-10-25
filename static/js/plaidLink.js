(async function($) {
    const handler = Plaid.create({
        token: (await $.post('/create_link_token')).link_token,
        onLoad: function() {
        },
        onSuccess: (async function(public_token, metadata) {
        startLoadScreen();
        const newUfiAndAccounts = await $.post('/exchange_public_token', {
            public_token: public_token,
        })
        addUFItoPage(newUfiAndAccounts);
        addAccountsToUFI(newUfiAndAccounts.accounts, newUfiAndAccounts.id);
        updateDashboardBalances(newUfiAndAccounts.dashboardBalanceNoLoan, newUfiAndAccounts.dashboardBalanceWithLoan);
        endLoadScreen();
        }),
        onExit: function(err, metadata) {
        if (err != null) {}
        },
        onEvent: function(eventName, metadata) {
        }
    });

    $('#link-button').on('click', function(e) {
        handler.open();
    });
    })(jQuery);