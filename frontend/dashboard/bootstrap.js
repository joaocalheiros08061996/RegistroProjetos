async function loadDashboard() {
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
    {
      run: loadRoutineTotalDaysData,
      feedback: feedback3El,
      empty: empty3El,
      chart: chart3El,
    },
    {
      run: loadProjectMonthlyKpisData,
      feedback: projectMonthlyFeedbackEl,
      empty: empty4El,
      chart: chart4El,
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

refreshBtn.addEventListener("click", loadDashboard);
routineTypeFilterEl.addEventListener("change", rerenderRoutineTotalDaysChart);
routineYearFilterEl.addEventListener("change", rerenderRoutineTotalDaysChart);
routineMonthFilterEl.addEventListener("change", rerenderRoutineTotalDaysChart);
routineUserFilterEl.addEventListener("change", rerenderRoutineTotalDaysChart);
projectMonthlyYearFilterEl.addEventListener("change", rerenderProjectMonthlyCharts);
projectMonthlyMonthFilterEl.addEventListener("change", rerenderProjectMonthlyCharts);
projectMonthlyTypeFilterEl.addEventListener("change", rerenderProjectMonthlyCharts);
projectMonthlyUserFilterEl.addEventListener("change", rerenderProjectMonthlyCharts);
complexityMonthlyYearFilterEl.addEventListener("change", rerenderComplexityMonthlyChart);
complexityMonthlyMonthFilterEl.addEventListener("change", rerenderComplexityMonthlyChart);
complexityMonthlyTypeFilterEl.addEventListener("change", rerenderComplexityMonthlyChart);
complexityMonthlyUserFilterEl.addEventListener("change", rerenderComplexityMonthlyChart);
earnedValueYearFilterEl.addEventListener("change", rerenderEarnedValueChart);
earnedValueMonthFilterEl.addEventListener("change", rerenderEarnedValueChart);
earnedValueTypeFilterEl.addEventListener("change", rerenderEarnedValueChart);
earnedValueUserFilterEl.addEventListener("change", rerenderEarnedValueChart);
schedulePerformanceYearFilterEl.addEventListener("change", rerenderSchedulePerformanceChart);
schedulePerformanceMonthFilterEl.addEventListener("change", rerenderSchedulePerformanceChart);
schedulePerformanceTypeFilterEl.addEventListener("change", rerenderSchedulePerformanceChart);
schedulePerformanceUserFilterEl.addEventListener("change", rerenderSchedulePerformanceChart);
costPerformanceYearFilterEl.addEventListener("change", rerenderCostPerformanceChart);
costPerformanceMonthFilterEl.addEventListener("change", rerenderCostPerformanceChart);
costPerformanceTypeFilterEl.addEventListener("change", rerenderCostPerformanceChart);
costPerformanceUserFilterEl.addEventListener("change", rerenderCostPerformanceChart);
effortDeviationYearFilterEl.addEventListener("change", rerenderEffortDeviationChart);
effortDeviationMonthFilterEl.addEventListener("change", rerenderEffortDeviationChart);
effortDeviationTypeFilterEl.addEventListener("change", rerenderEffortDeviationChart);
effortDeviationUserFilterEl.addEventListener("change", rerenderEffortDeviationChart);

const chartElements = [
  chartEl,
  chart2El,
  chart3El,
  chart4El,
  chart5El,
  chart6El,
  chart7El,
  chart8El,
  chart9El,
  chart10El,
  chart11El,
  chart12El,
  chart13El,
];

function resizeVisibleCharts() {
  for (const targetChartEl of chartElements) {
    if (!targetChartEl.classList.contains("hidden")) {
      Plotly.Plots.resize(targetChartEl);
    }
  }
}

window.addEventListener("resize", resizeVisibleCharts);

if ("ResizeObserver" in window) {
  const dashboardResizeObserver = new ResizeObserver(() => {
    requestAnimationFrame(resizeVisibleCharts);
  });

  chartElements.forEach((targetChartEl) => {
    dashboardResizeObserver.observe(targetChartEl.parentElement || targetChartEl);
  });
}

if (document.fonts?.ready) {
  document.fonts.ready.then(resizeVisibleCharts).catch(() => {});
}

loadDashboard().then(async () => {
  await waitForFrame();
  resizeVisibleCharts();
}).catch((err) => {
  const message = err?.message || "Erro ao carregar dashboard.";
  setFeedback(feedbackEl, message, "error");
  setFeedback(feedback2El, message, "error");
  setFeedback(feedback3El, message, "error");
  setFeedback(projectMonthlyFeedbackEl, message, "error");
  setFeedback(feedback8El, message, "error");
  setFeedback(feedback9El, message, "error");
  setFeedback(feedback10El, message, "error");
  setFeedback(feedback11El, message, "error");
  setFeedback(feedback12El, message, "error");
  setFeedback(feedback13El, message, "error");
});
