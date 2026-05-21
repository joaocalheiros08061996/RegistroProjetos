function registerDashboardResize(chartElements) {
  const visibleChartElements = chartElements.filter(Boolean);

  function resizeVisibleCharts() {
    for (const targetChartEl of visibleChartElements) {
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

    visibleChartElements.forEach((targetChartEl) => {
      dashboardResizeObserver.observe(targetChartEl.parentElement || targetChartEl);
    });
  }

  if (document.fonts?.ready) {
    document.fonts.ready.then(resizeVisibleCharts).catch(() => {});
  }

  return resizeVisibleCharts;
}

function addChangeListeners(elements, handler) {
  elements.filter(Boolean).forEach((element) => {
    element.addEventListener("change", handler);
  });
}

function setDashboardLoadError(feedbackElements, message) {
  feedbackElements.filter(Boolean).forEach((feedbackElement) => {
    setFeedback(feedbackElement, message, "error");
  });
}
