const ufiHolder = $('#UFI-holder');

ufiHolder.on("click", 'button', async function(e) {
    const resource = e.currentTarget.getAttribute('data-resource');
    const action = e.currentTarget.getAttribute('data-action');
    const id = e.currentTarget.getAttribute('data-id');
   
    if (resource === 'UFI') {
      if (action === 'delete') {
        await deleteUFI(id);
      } else if (action === 'update') {
        try {
          const res = await axios.get(`/financial-institutions/${id}/accounts/update`);
          addAccountsToUFI(res.data.accounts, id, update=true);
          updateDashboardBalances(res.data.dashboardBalanceNoLoan, res.data.dashboardBalanceWithLoan);
          updatePieChart(res.data);
        } catch (err) {
          throw err;
        }
      }
    } else if (resource === 'Account') {
        await deleteAcct(id);
    } else if (resource === 'BudgetTracker') {
        await deleteBudgetTracker(id);
    }
})

async function deleteUFI(ufiId) {
  try {
    const res = await axios.post(`/financial-institutions/${ufiId}/delete`);
    const ufiToDelete = $(`#UFI-${ufiId}`);
    ufiToDelete.remove();
    updateDashboardBalances(res.data.dashboardBalanceNoLoan, res.data.dashboardBalanceWithLoan);
    updatePieChart(res.data);
  } catch (err) {
    throw err;
  }
}

async function addUFItoPage(institution) {
  let currentUfiHTML = ufiHolder.html();
  let newUfiHTML = `
      <div id="UFI-${institution.id}" class="col-sm-12 col-md-6">
          <div class="card bg-light mb-3" >                   
              <div class="card-header" style="background-color: #166095; color: white;">
                  <div class="d-flex flex-row">
                      <div class="mr-auto p-2">
                          <h5 class="card-title">${institution.name}</h5>
                      </div>
                      <div class="p-2">
                          <div class="btn-group">
                              <button data-action="update" data-resource="UFI" data-id=${institution.id} class="btn btn-sm btn-primary"><i class="fas fa-sync"></i></button>
                              <button data-action="delete" data-resource="UFI" data-id=${institution.id} class="btn btn-sm btn-danger"><i class="far fa-trash-alt"></i></button>
                          </div>
                      </div>
                  </div>
              </div>
              <div class="card-body">`;
          if (institution.accounts.length == 0) {
              newUfiHTML += '<p>You have no accounts on record with this institution</p>';
          } else {
              newUfiHTML += `
              <div>
                  <ul id="Institution-${institution.id}-balances" class="list-group">`;
              if (institution.accountBalNoLoan > 0) {
                  newUfiHTML += '<li class="list-group-item list-group-item-action list-group-item-success">';
              } else if (institution.accountBalNoLoan === 0) {
                  newUfiHTML += '<li class="list-group-item list-group-item-action list-group-item-dark">';
              } else {
                  newUfiHTML += '<li class="list-group-item list-group-item-action list-group-item-danger">';
              }
              newUfiHTML += `<b>Total Amount <i>(no loans)</i>:</b>  $ ${institution.accountBalNoLoan}</li>`;
              if (institution.accountBalWithLoan > 0) {
                  newUfiHTML += '<li class="list-group-item list-group-item-action list-group-item-success">';
              } else if (institution.accountBalWithLoan == 0) {
                  newUfiHTML += '<li class="list-group-item list-group-item-action list-group-item-dark">';
              } else {
                  newUfiHTML += '<li class="list-group-item list-group-item-action list-group-item-danger">';
              }
              newUfiHTML += `<b>Total Amount:</b> $ ${institution.accountBalWithLoan}
                      </li>
                  </ul>
                  <hr class="my-4">
              </div>
                  <ul id="account-holder-${institution.id}" class="list-group"></ul>
      </div>`
                      }
      currentUfiHTML += newUfiHTML;
      ufiHolder.html(currentUfiHTML);
      updatePieChart(institution);
}

async function addAccountsToUFI(accounts, ufiId, update=false) {
    let ufiAccountHolder = $(`#account-holder-${ufiId}`);
    let currentHTML = ufiAccountHolder.html();
    let newAccountsHTML = '';
   
    if (!accounts || accounts.length == 0) {
        return
    } else {
        for (let idx=0; idx<accounts.length; idx++) {
            newAccountsHTML +=
            `<li id="Account-${accounts[idx].id}" class="list-group-item list-group-item-light">
                <ul class="list-group">
                    <li class="list-group-item list-group-item-primary d-flex justify-content-between align-items-center">
                        <b>${accounts[idx].name}</b><button data-action="delete" data-resource="Account" data-id=${accounts[idx].id} class="btn btn-sm btn-outline-danger"><i class="far fa-trash-alt"></i></button></form>
                    </li>`;
            if (accounts[idx].type == 'credit') {
                newAccountsHTML +=
                    `<li class="list-group-item list-group-item-light d-flex justify-content-between align-items-center">Limit: $ ${accounts[idx].limit}</li>
                    <li class="list-group-item list-group-item-light">Spent: $ ${accounts[idx].current}</li>
                    <li class="list-group-item list-group-item-light">Available: $ ${accounts[idx].limit - accounts[idx].current}</li>`; 
            } else if (accounts[idx].type == 'depository') {
                if (accounts[idx].subtype == 'checking') {
                    newAccountsHTML +=
                        `<li class="list-group-item list-group-item-light">Available: $ ${accounts[idx].available}</li>
                        <li class="list-group-item list-group-item-light">Current: $ ${accounts[idx].current}</li>`;
                } else {
                    newAccountsHTML +=
                        `<li class="list-group-item list-group-item-light">Current: $ ${accounts[idx].current}</li>`;
                }
            } else {
                newAccountsHTML +=
                    `<li class="list-group-item list-group-item-light">Outstanding Balance: $ ${accounts[idx].current}</li>`;
            }
                if (accounts[idx].budget_trackable) {
                    newAccountsHTML +=
                        `<li class="list-group-item list-group-item-light">
                            <div class="d-flex justify-content-center">
                                <a href="/accounts/${accounts[idx].id}/budget-tracker/create" class="btn btn-sm btn-outline-success">Create BudgetTracker</a>
                            </div>
                        </li>`;
                }
                newAccountsHTML += '</ul></li>';
      }
    }
    update ? currentHTML = newAccountsHTML : currentHTML += newAccountsHTML
    ufiAccountHolder.html(currentHTML);
}

function updateUFIBalances(balNoLoan, balWLoan, ufiId) {
  const ufiBal = $(`#Institution-${ufiId}-balances`)
  let htmlStr = '';
  if (balNoLoan > 0) {
    htmlStr += '<li class="list-group-item list-group-item-action list-group-item-success">';
  } else if (balNoLoan === 0) {
    htmlStr += '<li class="list-group-item list-group-item-action list-group-item-dark">';
  } else {
    htmlStr += '<li class="list-group-item list-group-item-action list-group-item-danger">';
  }
  htmlStr += `<b>Total Amount <i>(no loans)</i>:</b>  $ ${balNoLoan}</li>`;
  if (balWLoan > 0) {
    htmlStr += '<li class="list-group-item list-group-item-action list-group-item-success">';
  } else if (balWLoan == 0) {
    htmlStr += '<li class="list-group-item list-group-item-action list-group-item-dark">';
  } else {
    htmlStr += '<li class="list-group-item list-group-item-action list-group-item-danger">';
  }
  htmlStr += `<b>Total Amount:</b> $ ${balWLoan}
        </li>` 
  ufiBal.html(htmlStr);
}