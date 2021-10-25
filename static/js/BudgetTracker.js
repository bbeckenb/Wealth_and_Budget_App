async function deleteBudgetTracker(acctId) {
    try {
        const budgetTrackerContainer = $(`#Account-${acctId}-BudgetTracker`);
        const budgetTrackerCreateBtn = `
        <div class="d-flex justify-content-center">
            <a href="/accounts/${acctId}/budget-tracker/create" class="btn btn-sm btn-outline-success">Create BudgetTracker</a>
        </div>`;
        budgetTrackerContainer.html(budgetTrackerCreateBtn);
        const res = await axios.post(`/accounts/${acctId}/budget-tracker/delete`);
      } catch (err) {
        throw err;
      }
}