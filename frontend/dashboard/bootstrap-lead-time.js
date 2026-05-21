async function loadLeadTimeDashboard() {
  const jobs = [
    {
      run: renderAvgRealChart,
      feedback: feedbackEl,
      empty: emptyEl,
      chart: chartEl,
    },
    {
      run: renderPlannedVsRealChart,
      feedback: feedback2El,
      empty: empty2El,
      chart: chart2El,
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
    }
  });
}

const resizeLeadTimeCharts = registerDashboardResize([chartEl, chart2El]);

refreshBtn.addEventListener("click", loadLeadTimeDashboard);

loadLeadTimeDashboard().then(async () => {
  await waitForFrame();
  resizeLeadTimeCharts();
}).catch((err) => {
  const message = err?.message || "Erro ao carregar dashboard.";
  setDashboardLoadError([feedbackEl, feedback2El], message);
});
