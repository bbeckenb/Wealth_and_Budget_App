async function deleteAcct(acctId) {
    try {
      const acctToDelete = $(`#Account-${acctId}`);
      acctToDelete.remove();
      const res = await axios.post(`/accounts/${acctId}/delete`);
      addAlert(res.data.message)
      updateDashboardBalances(res.data.dashboardBalanceNoLoan, res.data.dashboardBalanceWithLoan);
      updatePieChart(res.data);
      updateUFIBalances(res.data); 
    } catch (err) {
      throw err;
    }
  }