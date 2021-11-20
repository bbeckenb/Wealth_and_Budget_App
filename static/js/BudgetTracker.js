async function deleteBudgetTracker(acctId) {
    try {
        const budgetTrackerContainer = $(`#Account-${acctId}-BudgetTracker`);
        const budgetTrackerCreateBtn = `
        <div class="d-flex justify-content-center">
            <a href="/accounts/${acctId}/budget-tracker/create" class="btn btn-sm btn-outline-success">Create BudgetTracker</a>
        </div>`;
        budgetTrackerContainer.html(budgetTrackerCreateBtn);
        console.log(acctId);
        const res = await axios.delete(`/accounts/${acctId}/budget-tracker`);
        addAlert(res.data.message);
      } catch (err) {
          throw err;
      }
}