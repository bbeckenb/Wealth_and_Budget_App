async function deleteBudgetTracker(acctId) {
    try {
        const res = await axios.delete(`/accounts/${acctId}/budget-tracker`);
        if (res.data.status === 401) {
            addAlert(res.data.message);
        } else {
            const budgetTrackerContainer = $(`#Account-${acctId}-BudgetTracker`);
            const budgetTrackerCreateBtn = `
            <div class="d-flex justify-content-center">
                <a href="/accounts/${acctId}/budget-tracker/create" class="btn btn-sm btn-outline-success">Create BudgetTracker</a>
            </div>`;
            budgetTrackerContainer.html(budgetTrackerCreateBtn);
            console.log(acctId);
            addAlert(res.data.message);
        }
      } catch (err) {
          throw err;
      }
}