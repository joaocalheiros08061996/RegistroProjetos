function aggregateEffortDeviationItems(items) {
  const grouped = new Map();

  for (const item of items) {
    const key = `${item.year}-${String(item.month).padStart(2, "0")}`;
    const current = grouped.get(key) || {
      year: Number(item.year),
      month: Number(item.month),
      monthLabel: item.month_label,
      periodLabel: item.period_label,
      taskCount: 0,
      plannedEffortHours: 0,
      actualEffortHours: 0,
      plannedLaborCost: 0,
      actualLaborCost: 0,
    };

    current.taskCount += Number(item.task_count || 0);
    current.plannedEffortHours += Number(item.planned_effort_hours || 0);
    current.actualEffortHours += Number(item.actual_effort_hours || 0);
    current.plannedLaborCost += Number(item.planned_labor_cost || 0);
    current.actualLaborCost += Number(item.actual_labor_cost || 0);
    grouped.set(key, current);
  }

  return [...grouped.values()]
    .map((item) => ({
      ...item,
      effortDeviationHours: item.actualEffortHours - item.plannedEffortHours,
      laborCostDeviation: item.actualLaborCost - item.plannedLaborCost,
      effortDeviationPercent: item.plannedEffortHours > 0
        ? ((item.actualEffortHours - item.plannedEffortHours) / item.plannedEffortHours) * 100
        : null,
    }))
    .sort((a, b) => {
      if (a.year !== b.year) {
        return a.year - b.year;
      }
      return a.month - b.month;
    });
}

function effortDeviationStatus(value) {
  if (value > 0) {
    return "Acima do estimado";
  }
  if (value < 0) {
    return "Abaixo do estimado";
  }
  return "Dentro do estimado";
}

function effortDeviationColor(value) {
  if (value > 0) {
    return "#EB5757";
  }
  if (value < 0) {
    return "#27AE60";
  }
  return "#F2C94C";
}

function effortDeviationRange(values) {
  const maxAbs = Math.max(1, ...finiteNumbers(values).map((value) => Math.abs(value)));
  return [-maxAbs * 1.25, maxAbs * 1.25];
}

function toEffortDeviationChartPayload(items) {
  const timeUnit = getDashboardTimeUnit();
  const unitLabel = getDashboardTimeUnitLabel(timeUnit);
  const aggregatedItems = aggregateEffortDeviationItems(items);
  const periodLabels = aggregatedItems.map((item) => item.periodLabel);
  const deviationValues = aggregatedItems.map((item) =>
    convertHoursToDashboardUnit(item.effortDeviationHours, timeUnit, DASHBOARD_WORKDAY_HOURS)
  );

  return {
    data: [
      {
        type: "bar",
        name: "Desvio de esforço",
        x: periodLabels,
        y: deviationValues,
        marker: {
          color: deviationValues.map(effortDeviationColor),
          line: {
            color: "#ffffff",
            width: 2,
          },
        },
        text: deviationValues.map((value) =>
          formatSignedDashboardDurationValue(value, timeUnit)
        ),
        textposition: "outside",
        textfont: projectMonthlyTextStyle(),
        cliponaxis: false,
        customdata: aggregatedItems.map((item) => [
          formatSignedDashboardDurationValue(
            convertHoursToDashboardUnit(
              item.effortDeviationHours,
              timeUnit,
              DASHBOARD_WORKDAY_HOURS
            ),
            timeUnit
          ),
          effortDeviationStatus(item.effortDeviationHours),
          formatDashboardDurationValue(
            convertHoursToDashboardUnit(
              item.plannedEffortHours,
              timeUnit,
              DASHBOARD_WORKDAY_HOURS
            ),
            timeUnit
          ),
          formatDashboardDurationValue(
            convertHoursToDashboardUnit(
              item.actualEffortHours,
              timeUnit,
              DASHBOARD_WORKDAY_HOURS
            ),
            timeUnit
          ),
          Number.isFinite(item.effortDeviationPercent)
            ? `${item.effortDeviationPercent.toFixed(1)}%`
            : "-",
          formatMoney(item.plannedLaborCost),
          formatMoney(item.actualLaborCost),
          formatMoney(item.laborCostDeviation),
          item.taskCount,
        ]),
        hovertemplate: "%{x}<br>Desvio: %{customdata[0]} (%{customdata[1]})<br>Planejado: %{customdata[2]}<br>Real: %{customdata[3]}<br>Variação: %{customdata[4]}<br>Mão de obra planejada: %{customdata[5]}<br>Mão de obra real: %{customdata[6]}<br>Desvio em R$: %{customdata[7]}<br>Tarefas: %{customdata[8]}<extra></extra>",
      },
      {
        type: "scatter",
        mode: "lines",
        name: `Referência 0 ${unitLabel}`,
        x: periodLabels,
        y: periodLabels.map(() => 0),
        line: {
          color: "#7F8C8D",
          width: 2,
          dash: "dash",
        },
        hovertemplate: `%{x}<br>Referência sem desvio: 0 ${unitLabel}<extra></extra>`,
      },
    ],
    layout: {
      ...projectMonthlyBaseLayout(
        "Desvio de Esforço por Mês",
        `Desvio (${unitLabel})`
      ),
      bargap: 0.45,
      yaxis: {
        ...projectMonthlyBaseLayout("", `Desvio (${unitLabel})`).yaxis,
        range: effortDeviationRange(deviationValues),
        zeroline: true,
        zerolinecolor: "#7F8C8D",
        zerolinewidth: 2,
      },
      legend: {
        ...projectMonthlyBaseLayout("", `Desvio (${unitLabel})`).legend,
        y: -0.28,
      },
    },
    config: projectMonthlyConfig(),
  };
}

async function loadEffortDeviationData() {
  setFeedback(feedback13El, "Carregando gráfico...");
  showState(empty13El, chart13El, { showEmpty: false, showChart: false });

  const payload = await apiFetch("/dashboard/project-effort-deviation");
  effortDeviationItems = Array.isArray(payload?.items) ? payload.items : [];
  buildEffortDeviationFilterOptions(effortDeviationItems);
  await renderEffortDeviationChart();
}

async function renderEffortDeviationChart() {
  const filteredItems = getFilteredEffortDeviationItems();
  const aggregatedItems = aggregateEffortDeviationItems(filteredItems);

  if (!filteredItems.length || !aggregatedItems.length) {
    setFeedback(feedback13El, "Sem dados de esforço para exibir no filtro atual.");
    showState(empty13El, chart13El, { showEmpty: true, showChart: false });
    return;
  }

  const { data, layout, config } = toEffortDeviationChartPayload(filteredItems);
  await plotVisible(empty13El, chart13El, data, layout, config);

  const totalTasks = filteredItems.reduce(
    (acc, item) => acc + Number(item.task_count || 0),
    0
  );
  setFeedback(
    feedback13El,
    `Gráfico atualizado com ${totalTasks} tarefa(s) em ${aggregatedItems.length} período(s).`
  );
}

function rerenderEffortDeviationChart() {
  renderEffortDeviationChart().catch((err) => {
    const message = err?.message || "Erro ao atualizar gráfico de desvio de esforço.";
    setFeedback(feedback13El, message, "error");
    showState(empty13El, chart13El, { showEmpty: false, showChart: false });
  });
}
