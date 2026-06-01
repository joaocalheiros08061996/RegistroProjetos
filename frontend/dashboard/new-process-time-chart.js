const NEW_PROCESS_MONTH_OPTIONS = [
  { value: "ALL", label: "Todos" },
  { value: "1", label: "JAN" },
  { value: "2", label: "FEV" },
  { value: "3", label: "MAR" },
  { value: "4", label: "ABR" },
  { value: "5", label: "MAI" },
  { value: "6", label: "JUN" },
  { value: "7", label: "JUL" },
  { value: "8", label: "AGO" },
  { value: "9", label: "SET" },
  { value: "10", label: "OUT" },
  { value: "11", label: "NOV" },
  { value: "12", label: "DEZ" },
];

function formatNewProcessDurationFromDays(value, unit = getDashboardTimeUnit()) {
  return formatDashboardDurationValue(
    convertDaysToDashboardUnit(value, unit),
    unit
  );
}

function buildNewProcessTimeFilterOptions(items) {
  const responsibles = [...new Set(
    items.map((item) => String(item.responsible_label || "").trim())
  )]
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b, "pt-BR"))
    .map((responsible) => ({ value: responsible, label: responsible }));

  const years = [...new Set(items.map((item) => Number(item.year)))]
    .filter((year) => Number.isFinite(year))
    .sort((a, b) => a - b);

  const monthValues = new Set(
    items
      .map((item) => Number(item.month))
      .filter((month) => Number.isFinite(month))
      .map((month) => String(month))
  );
  const months = NEW_PROCESS_MONTH_OPTIONS.filter((option) =>
    option.value === "ALL" || monthValues.has(option.value)
  );

  setSelectOptions(
    newProcessResponsibleFilterEl,
    [
      { value: "ALL", label: "Todos" },
      ...responsibles,
    ],
  );
  setSelectOptions(
    newProcessYearFilterEl,
    [
      { value: "ALL", label: "Todos" },
      ...years.map((year) => ({ value: year, label: String(year) })),
    ],
  );
  setSelectOptions(newProcessMonthFilterEl, months);
}

function getFilteredNewProcessTimeItems() {
  const selectedResponsible = newProcessResponsibleFilterEl.value;
  const selectedYear = newProcessYearFilterEl.value;
  const selectedMonth = newProcessMonthFilterEl.value;

  return newProcessTimeItems.filter((item) => {
    if (
      selectedResponsible !== "ALL"
      && item.responsible_label !== selectedResponsible
    ) {
      return false;
    }
    if (selectedYear !== "ALL" && Number(item.year) !== Number(selectedYear)) {
      return false;
    }
    if (selectedMonth !== "ALL" && Number(item.month) !== Number(selectedMonth)) {
      return false;
    }
    return true;
  });
}

function aggregateNewProcessTimeByPeriod(items) {
  const grouped = new Map();

  for (const item of items) {
    const key = `${item.year}-${String(item.month).padStart(2, "0")}`;
    const current = grouped.get(key) || {
      year: Number(item.year),
      month: Number(item.month),
      periodLabel: item.period_label,
      projectDays: 0,
      routineDays: 0,
    };

    current.projectDays += Number(item.project_days || 0);
    current.routineDays += Number(item.routine_days || 0);
    grouped.set(key, current);
  }

  return [...grouped.values()]
    .map((item) => ({
      ...item,
      totalDays: item.projectDays + item.routineDays,
    }))
    .sort((a, b) => {
      if (a.year !== b.year) {
        return a.year - b.year;
      }
      return a.month - b.month;
    });
}

function toNewProcessTimeChartPayload(items) {
  const timeUnit = getDashboardTimeUnit();
  const unitLabel = getDashboardTimeUnitLabel(timeUnit);
  const aggregatedItems = aggregateNewProcessTimeByPeriod(items);
  const periodLabels = aggregatedItems.map((item) => item.periodLabel);
  const projectValues = aggregatedItems.map((item) =>
    convertDaysToDashboardUnit(item.projectDays, timeUnit)
  );
  const routineValues = aggregatedItems.map((item) =>
    convertDaysToDashboardUnit(item.routineDays, timeUnit)
  );
  const totalValues = aggregatedItems.map((item) =>
    convertDaysToDashboardUnit(item.totalDays, timeUnit)
  );
  const maxValue = Math.max(0, ...totalValues);
  const yAxisMax = maxValue > 0 ? maxValue * 1.22 : 1;

  return {
    data: [
      {
        type: "bar",
        name: "Projetos",
        x: periodLabels,
        y: projectValues,
        marker: projectMonthlyBarStyle("#2F80ED"),
        customdata: aggregatedItems.map((item) => [
          formatNewProcessDurationFromDays(item.projectDays, timeUnit),
          formatNewProcessDurationFromDays(item.totalDays, timeUnit),
        ]),
        hovertemplate: "%{x}<br>Projetos: %{customdata[0]}<br>Total: %{customdata[1]}<extra></extra>",
      },
      {
        type: "bar",
        name: "Rotina",
        x: periodLabels,
        y: routineValues,
        marker: projectMonthlyBarStyle("#27AE60"),
        customdata: aggregatedItems.map((item) => [
          formatNewProcessDurationFromDays(item.routineDays, timeUnit),
          formatNewProcessDurationFromDays(item.totalDays, timeUnit),
        ]),
        hovertemplate: "%{x}<br>Rotina: %{customdata[0]}<br>Total: %{customdata[1]}<extra></extra>",
      },
      {
        type: "scatter",
        mode: "text",
        name: "Total",
        x: periodLabels,
        y: totalValues,
        text: aggregatedItems.map((item) =>
          formatNewProcessDurationFromDays(item.totalDays, timeUnit)
        ),
        textposition: "top center",
        textfont: projectMonthlyTextStyle(),
        hoverinfo: "skip",
        showlegend: false,
      },
    ],
    layout: {
      ...projectMonthlyBaseLayout(
        "Tempo em Processos Novos por Mês",
        `Tempo (${unitLabel})`
      ),
      barmode: "stack",
      bargap: 0.42,
      yaxis: {
        ...projectMonthlyBaseLayout("", `Tempo (${unitLabel})`).yaxis,
        range: [0, yAxisMax],
        rangemode: "tozero",
      },
      legend: {
        ...projectMonthlyBaseLayout("", `Tempo (${unitLabel})`).legend,
        y: -0.28,
      },
    },
    config: projectMonthlyConfig(),
  };
}

async function loadNewProcessTimeDashboard() {
  setFeedback(feedback14El, "Carregando gráfico...");
  showState(empty14El, chart14El, { showEmpty: false, showChart: false });

  const payload = await apiFetch("/dashboard/new-process-time-by-month");
  newProcessTimeItems = Array.isArray(payload?.items) ? payload.items : [];
  buildNewProcessTimeFilterOptions(newProcessTimeItems);
  await renderNewProcessTimeChart();
}

async function renderNewProcessTimeChart() {
  const filteredItems = getFilteredNewProcessTimeItems();
  const aggregatedItems = aggregateNewProcessTimeByPeriod(filteredItems);

  if (!filteredItems.length || !aggregatedItems.length) {
    setFeedback(feedback14El, "Sem tempo contabilizado para o filtro atual.");
    showState(empty14El, chart14El, { showEmpty: true, showChart: false });
    return;
  }

  const hasVisibleData = aggregatedItems.some((item) => item.totalDays > 0);
  if (!hasVisibleData) {
    setFeedback(feedback14El, "Sem tempo contabilizado para o filtro atual.");
    showState(empty14El, chart14El, { showEmpty: true, showChart: false });
    return;
  }

  const { data, layout, config } = toNewProcessTimeChartPayload(filteredItems);
  await plotVisible(empty14El, chart14El, data, layout, config);
  setFeedback(
    feedback14El,
    `Gráfico atualizado com ${aggregatedItems.length} período(s).`
  );
}

function rerenderNewProcessTimeChart() {
  renderNewProcessTimeChart().catch((err) => {
    const message = err?.message || "Erro ao atualizar gráfico.";
    setFeedback(feedback14El, message, "error");
    showState(empty14El, chart14El, { showEmpty: false, showChart: false });
  });
}

const resizeNewProcessTimeCharts = registerDashboardResize([chart14El]);

setupDashboardTimeUnitFilter(rerenderNewProcessTimeChart);
refreshBtn.addEventListener("click", loadNewProcessTimeDashboard);
addChangeListeners(
  [
    newProcessResponsibleFilterEl,
    newProcessYearFilterEl,
    newProcessMonthFilterEl,
  ],
  rerenderNewProcessTimeChart,
);

loadNewProcessTimeDashboard().then(async () => {
  await waitForFrame();
  resizeNewProcessTimeCharts();
}).catch((err) => {
  const message = err?.message || "Erro ao carregar dashboard.";
  setDashboardLoadError([feedback14El], message);
  showState(empty14El, chart14El, { showEmpty: false, showChart: false });
});
