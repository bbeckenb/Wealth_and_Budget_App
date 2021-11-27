async function deleteAcct(acctId) {
    try {
      const res = await axios.delete(`/accounts/${acctId}`);
      if (res.data.status === 401) {
        addAlert(res.data.message);
    } else {
      const acctToDelete = $(`#Account-${acctId}`);
      acctToDelete.remove();
      addAlert(res.data.message)
      updateDashboardBalances(res.data.dashboardBalanceNoLoan, res.data.dashboardBalanceWithLoan);
      updatePieChart(res.data);
      updateUFIBalances(res.data); 
    }
    } catch (err) {
      throw err;
    }
  }