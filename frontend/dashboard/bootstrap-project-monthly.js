async function loadProjectMonthlyDashboard() {
  const jobs = [
    {
      run: loadProjectMonthlyKpisData,
      feedback: projectMonthlyFeedbackEl,
      empty: empty4El,
      chart: chart4El,
      onError: (message) => {
        setFeedback(feedback4El, message, "error");
        setFeedback(feedback5El, message, "error");
        setFeedback(feedback6El, message, "error");
        setFeedback(feedback7El, message, "error");
        showState(empty5El, chart5El, { showEmpty: false, showChart: false });
        showState(empty6El, chart6El, { showEmpty: false, showChart: false });
        showState(empty7El, chart7El, { showEmpty: false, showChart: false });
      },
    },
    {
      run: renderProjectComplexityChart,
      feedback: feedback8El,
      empty: empty8El,
      chart: chart8El,
    },
    {
      run: loadComplexityMonthlyData,
      feedback: feedback9El,
      empty: empty9El,
      chart: chart9El,
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

const resizeProjectMonthlyCharts = registerDashboardResize([
  chart4El,
  chart5El,
  chart6El,
  chart7El,
  chart8El,
  chart9El,
]);

refreshBtn.addEventListener("click", loadProjectMonthlyDashboard);
addChangeListeners(
  [
    projectMonthlyYearFilterEl,
    projectMonthlyMonthFilterEl,
    projectMonthlyTypeFilterEl,
    projectMonthlyUserFilterEl,
  ],
  rerenderProjectMonthlyCharts,
);
addChangeListeners(
  [
    complexityMonthlyYearFilterEl,
    complexityMonthlyMonthFilterEl,
    complexityMonthlyTypeFilterEl,
    complexityMonthlyUserFilterEl,
  ],
  rerenderComplexityMonthlyChart,
);

loadProjectMonthlyDashboard().then(async () => {
  await waitForFrame();
  resizeProjectMonthlyCharts();
}).catch((err) => {
  const message = err?.message || "Erro ao carregar dashboard.";
  setDashboardLoadError(
    [
      projectMonthlyFeedbackEl,
      feedback4El,
      feedback5El,
      feedback6El,
      feedback7El,
      feedback8El,
      feedback9El,
    ],
    message,
  );
});
