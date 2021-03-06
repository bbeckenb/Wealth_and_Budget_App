(async function($) {
    const handler = Plaid.create({
        token: (await $.post('/create_link_token')).link_token,
        onLoad: function() {
        },
        onSuccess: (async function(public_token) {
            async function createUFIandAccounts() {
                try {
                    startLoadScreen();
                    const newUfi = await $.post('/financial-institutions', {
                        public_token: public_token,
                    })
                    const newUFIwithAccounts = await $.post(`/financial-institutions/${newUfi.id}/accounts`);
                    addUFItoPage(newUFIwithAccounts);
                    addAccountsToUFI(newUFIwithAccounts.accounts, newUFIwithAccounts.id);
                    updateDashboardBalances(newUFIwithAccounts.dashboardBalanceNoLoan, newUFIwithAccounts.dashboardBalanceWithLoan);
                    endLoadScreen();
                    addAlert(newUFIwithAccounts.message);
                } catch (err) {
                    console.error('Server problem connecting with Plaid:', err)
                }
            }
        await createUFIandAccounts();
       
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