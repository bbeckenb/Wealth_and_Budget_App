async function deleteAcct(acctId) {
    try {
      const acctToDelete = $(`#Account-${acctId}`);
      acctToDelete.remove();
      const res = await axios.delete(`/accounts/${acctId}`);
      addAlert(res.data.message)
      updateDashboardBalances(res.data.dashboardBalanceNoLoan, res.data.dashboardBalanceWithLoan);
      updatePieChart(res.data);
      updateUFIBalances(res.data); 
    } catch (err) {
      throw err;
    }
  }