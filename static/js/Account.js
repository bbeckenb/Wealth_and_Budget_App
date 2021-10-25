

async function deleteAcct(acctId) {
    try {
      const acctToDelete = $(`#Account-${acctId}`);
      acctToDelete.remove();
      const res = await axios.post(`/accounts/${acctId}/delete`);
      updateDashboardBalances(res.data.dashboardBalanceNoLoan, res.data.dashboardBalanceWithLoan);
      updatePieChart(res.data);
      updateUFIBalances(res.data.ufiBalanaceNoLoan, res.data.ufiBalanceWithLoan, res.data.id) 
    } catch (err) {
      throw err;
    }
  }