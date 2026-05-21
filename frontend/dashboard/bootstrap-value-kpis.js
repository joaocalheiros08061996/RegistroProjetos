async function loadValueKpisDashboard() {
  const jobs = [
    {
      run: loadEarnedValueData,
      feedback: feedback10El,
      empty: empty10El,
      chart: chart10El,
      onError: (message) => {
        setFeedback(feedback11El, message, "error");
        showState(empty11El, chart11El, { showEmpty: false, showChart: false });
        setFeedback(feedback12El, message, "error");
        showState(empty12El, chart12El, { showEmpty: false, showChart: false });
      },
    },
    {
      run: loadEffortDeviationData,
      feedback: feedback13El,
      empty: empty13El,
      chart: chart13El,
    },
  ];

  const results = await Promise.allSettled(jobs.map((job) => job.run()));

  results.forEach((result, index) => {
    if (result.status === "rejected") {
      const message = result.reason?.message || "Erro ao carregar gráfico.";
      setFeedback(jobs[index].feedback, message, "error");
      showState(jobs[index].empty, jobs[index].chart, {
        showEmpty: false,
        showChart: false,
      });
      jobs[index].onError?.(message);
    }
  });
}

const resizeValueKpiCharts = registerDashboardResize([
  chart10El,
  chart11El,
  chart12El,
  chart13El,
]);

refreshBtn.addEventListener("click", loadValueKpisDashboard);
addChangeListeners(
  [
    earnedValueYearFilterEl,
    earnedValueMonthFilterEl,
    earnedValueTypeFilterEl,
    earnedValueUserFilterEl,
  ],
  rerenderEarnedValueChart,
);
addChangeListeners(
  [
    schedulePerformanceYearFilterEl,
    schedulePerformanceMonthFilterEl,
    schedulePerformanceTypeFilterEl,
    schedulePerformanceUserFilterEl,
  ],
  rerenderSchedulePerformanceChart,
);
addChangeListeners(
  [
    costPerformanceYearFilterEl,
    costPerformanceMonthFilterEl,
    costPerformanceTypeFilterEl,
    costPerformanceUserFilterEl,
  ],
  rerenderCostPerformanceChart,
);
addChangeListeners(
  [
    effortDeviationYearFilterEl,
    effortDeviationMonthFilterEl,
    effortDeviationTypeFilterEl,
    effortDeviationUserFilterEl,
  ],
  rerenderEffortDeviationChart,
);

loadValueKpisDashboard().then(async () => {
  await waitForFrame();
  resizeValueKpiCharts();
}).catch((err) => {
  const message = err?.message || "Erro ao carregar dashboard.";
  setDashboardLoadError(
    [feedback10El, feedback11El, feedback12El, feedback13El],
    message,
  );
});
