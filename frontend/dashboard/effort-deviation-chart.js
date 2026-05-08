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
    };

    current.taskCount += Number(item.task_count || 0);
    current.plannedEffortHours += Number(item.planned_effort_hours || 0);
    current.actualEffortHours += Number(item.actual_effort_hours || 0);
    grouped.set(key, current);
  }

  return [...grouped.values()]
    .map((item) => ({
      ...item,
      effortDeviationHours: item.actualEffortHours - item.plannedEffortHours,
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
  const aggregatedItems = aggregateEffortDeviationItems(items);
  const periodLabels = aggregatedItems.map((item) => item.periodLabel);
  const deviationValues = aggregatedItems.map((item) => item.effortDeviationHours);

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
        text: deviationValues.map(formatSignedHours),
        textposition: "outside",
        textfont: projectMonthlyTextStyle(),
        cliponaxis: false,
        customdata: aggregatedItems.map((item) => [
          formatSignedHours(item.effortDeviationHours),
          effortDeviationStatus(item.effortDeviationHours),
          formatHours(item.plannedEffortHours),
          formatHours(item.actualEffortHours),
          Number.isFinite(item.effortDeviationPercent)
            ? `${item.effortDeviationPercent.toFixed(1)}%`
            : "-",
          item.taskCount,
        ]),
        hovertemplate: "%{x}<br>Desvio: %{customdata[0]} (%{customdata[1]})<br>Planejado: %{customdata[2]}<br>Real: %{customdata[3]}<br>Variação: %{customdata[4]}<br>Tarefas: %{customdata[5]}<extra></extra>",
      },
      {
        type: "scatter",
        mode: "lines",
        name: "Referência 0 h",
        x: periodLabels,
        y: periodLabels.map(() => 0),
        line: {
          color: "#7F8C8D",
          width: 2,
          dash: "dash",
        },
        hovertemplate: "%{x}<br>Referência sem desvio: 0 h<extra></extra>",
      },
    ],
    layout: {
      ...projectMonthlyBaseLayout(
        "Desvio de Esforço por Mês",
        "Desvio (horas)"
      ),
      bargap: 0.45,
      yaxis: {
        ...projectMonthlyBaseLayout("", "Desvio (horas)").yaxis,
        range: effortDeviationRange(deviationValues),
        zeroline: true,
        zerolinecolor: "#7F8C8D",
        zerolinewidth: 2,
      },
      legend: {
        ...projectMonthlyBaseLayout("", "Desvio (horas)").legend,
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
