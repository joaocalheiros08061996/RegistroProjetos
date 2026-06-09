async function loadRoutineSeriesDashboard() {
  await loadRoutineTotalDaysData();
}

const resizeRoutineSeriesCharts = registerDashboardResize([chart3El]);

setupDashboardTimeUnitFilter(rerenderRoutineTotalDaysChart);
setupRoutineTypeFilterDropdown(rerenderRoutineTotalDaysChart);
refreshBtn.addEventListener("click", loadRoutineSeriesDashboard);
addChangeListeners(
  [
    routineYearFilterEl,
    routineMonthFilterEl,
    routineUserFilterEl,
  ],
  rerenderRoutineTotalDaysChart,
);

loadRoutineSeriesDashboard().then(async () => {
  await waitForFrame();
  resizeRoutineSeriesCharts();
}).catch((err) => {
  const message = err?.message || "Erro ao carregar dashboard.";
  setDashboardLoadError([feedback3El], message);
  showState(empty3El, chart3El, { showEmpty: false, showChart: false });
});
