function toMonthlyLeadTimeChartPayload(items) {
  const aggregatedItems = aggregateProjectMonthlyByPeriod(items)
    .filter((item) => Number.isFinite(item.realAverageDays));
  const graphOneAverage = getGraphOneRealAverageForSelectedTypes();
  const periodLabels = aggregatedItems.map((item) => item.periodLabel);
  const realValues = aggregatedItems.map((item) => item.realAverageDays);
  const referenceValues = Number.isFinite(graphOneAverage)
    ? periodLabels.map(() => graphOneAverage)
    : [];
  const yValues = [...realValues, ...referenceValues];
  const precision = getDaysPrecision(yValues);
  const maxY = Math.max(0, ...finiteNumbers(yValues));
  const yAxisMax = maxY > 0 ? maxY * 1.22 : 1;
  const data = [
    {
      type: "bar",
      name: "Média Lead Time por Mês",
      x: periodLabels,
      y: realValues,
      marker: projectMonthlyBarStyle("#2F80ED"),
      text: realValues.map((value) => formatAdaptiveDays(value, yValues)),
      textposition: "outside",
      textfont: projectMonthlyTextStyle(),
      cliponaxis: false,
      hovertemplate: `%{x}<br>Lead time médio: %{y:.${precision}f} dias<extra></extra>`,
    },
  ];

  if (Number.isFinite(graphOneAverage)) {
    data.push({
      type: "scatter",
      mode: "lines+markers",
      name: "Média Lead Time Real",
      x: periodLabels,
      y: periodLabels.map(() => graphOneAverage),
      line: projectMonthlyLineStyle("#F2994A"),
      marker: projectMonthlyMarkerStyle("#F2994A"),
      hovertemplate: `%{x}<br>Média do Gráfico 1: %{y:.${precision}f} dias<extra></extra>`,
    });
  }

  return {
    data,
    layout: {
      ...projectMonthlyBaseLayout(
        "Lead Time Mensal por Tipo de Projeto",
        "Média de dias reais"
      ),
      barmode: "group",
      bargap: 0.46,
      yaxis: {
        ...projectMonthlyBaseLayout("", "Média de dias reais").yaxis,
        range: [0, yAxisMax],
        rangemode: "tozero",
        tickformat: `.${precision}f`,
      },
    },
    config: projectMonthlyConfig(),
  };
}

function toMonthlyDelayChartPayload(items) {
  const aggregatedItems = aggregateProjectMonthlyByPeriod(items)
    .filter((item) => Number.isFinite(item.delayAverageDays));
  const overallDelayAverage = getOverallDelayAverage(items);
  const periodLabels = aggregatedItems.map((item) => item.periodLabel);
  const data = [
    {
      type: "scatter",
      mode: "lines+markers",
      name: "Média de Atraso por Mês",
      x: periodLabels,
      y: aggregatedItems.map((item) => item.delayAverageDays),
      line: projectMonthlyLineStyle("#2F80ED"),
      marker: projectMonthlyMarkerStyle("#2F80ED"),
      hovertemplate: "%{x}<br>Atraso médio: %{y:.2f} dias<extra></extra>",
    },
  ];

  if (Number.isFinite(overallDelayAverage)) {
    data.push({
      type: "scatter",
      mode: "lines+markers",
      name: "Média de Atraso Médio",
      x: periodLabels,
      y: periodLabels.map(() => overallDelayAverage),
      line: projectMonthlyLineStyle("#F2994A"),
      marker: projectMonthlyMarkerStyle("#F2994A"),
      hovertemplate: "%{x}<br>Média geral de atraso: %{y:.2f} dias<extra></extra>",
    });
  }

  const yValues = data.flatMap((trace) => trace.y || []);

  return {
    data,
    layout: {
      ...projectMonthlyBaseLayout(
        "Atraso Médio Mensal por Tipo de Projeto",
        "Média de dias de atraso"
      ),
      yaxis: {
        ...projectMonthlyBaseLayout("", "Média de dias de atraso").yaxis,
        range: projectMonthlySignedRange(yValues),
        zeroline: true,
        zerolinecolor: "rgba(17, 35, 56, 0.28)",
        zerolinewidth: 1,
      },
    },
    config: projectMonthlyConfig(),
  };
}

function toMonthlyEfficiencyChartPayload(items) {
  const aggregatedItems = aggregateProjectMonthlyByPeriod(items)
    .filter((item) => Number.isFinite(item.efficiency));

  return {
    data: [
      {
        type: "scatter",
        mode: "lines+markers",
        name: "Eficiência média mensal",
        x: aggregatedItems.map((item) => item.periodLabel),
        y: aggregatedItems.map((item) => item.efficiency),
        line: projectMonthlyLineStyle("#2F80ED"),
        marker: projectMonthlyMarkerStyle("#2F80ED"),
        hovertemplate: "%{x}<br>Eficiência: %{y:.1f}%<extra></extra>",
      },
    ],
    layout: {
      ...projectMonthlyBaseLayout(
        "Eficiência Mensal por Tipo de Projeto",
        "Eficiência média"
      ),
      yaxis: {
        ...projectMonthlyBaseLayout("", "Eficiência média").yaxis,
        ticksuffix: "%",
        range: projectMonthlyEfficiencyRange(
          aggregatedItems.map((item) => item.efficiency)
        ),
        rangemode: "tozero",
      },
      showlegend: true,
    },
    config: projectMonthlyConfig(),
  };
}

function toMonthlySlaBreachChartPayload(items) {
  const aggregatedItems = aggregateProjectMonthlyByPeriod(items)
    .filter((item) => Number.isFinite(item.slaRate));

  return {
    data: [
      {
        type: "bar",
        x: aggregatedItems.map((item) => item.periodLabel),
        y: aggregatedItems.map((item) => item.slaRate),
        marker: projectMonthlyBarStyle("#2F80ED"),
        text: aggregatedItems.map((item) => formatPercent(item.slaRate)),
        textposition: "outside",
        textfont: projectMonthlyTextStyle(),
        cliponaxis: false,
        hovertemplate: "%{x}<br>Taxa: %{y:.1f}%<extra></extra>",
        name: "Total",
      },
    ],
    layout: {
      ...projectMonthlyBaseLayout(
        "Taxa de Projetos que Estouram o Prazo",
        "Taxa (%)"
      ),
      yaxis: {
        ...projectMonthlyBaseLayout("", "Taxa (%)").yaxis,
        ticksuffix: "%",
        range: projectMonthlySlaRange(aggregatedItems.map((item) => item.slaRate)),
        rangemode: "tozero",
      },
      showlegend: true,
    },
    config: projectMonthlyConfig(),
  };
}

async function loadProjectMonthlyKpisData() {
  setFeedback(projectMonthlyFeedbackEl, "Carregando gráficos mensais...");
  setFeedback(feedback4El, "");
  setFeedback(feedback5El, "");
  setFeedback(feedback6El, "");
  setFeedback(feedback7El, "");
  showState(empty4El, chart4El, { showEmpty: false, showChart: false });
  showState(empty5El, chart5El, { showEmpty: false, showChart: false });
  showState(empty6El, chart6El, { showEmpty: false, showChart: false });
  showState(empty7El, chart7El, { showEmpty: false, showChart: false });

  const payload = await apiFetch("/dashboard/project-monthly-kpis");
  projectMonthlyItems = Array.isArray(payload?.items) ? payload.items : [];
  if (!avgRealItems.length) {
    const avgRealPayload = await apiFetch("/dashboard/avg-real-days-by-project-type");
    avgRealItems = Array.isArray(avgRealPayload?.items) ? avgRealPayload.items : [];
  }
  buildProjectMonthlyFilterOptions(projectMonthlyItems);
  await renderProjectMonthlyCharts();
}

async function renderChartOrEmpty({
  items,
  chartEl: targetChartEl,
  emptyEl: targetEmptyEl,
  feedbackEl: targetFeedbackEl,
  payloadFactory,
  emptyMessage,
}) {
  if (!items.length) {
    setFeedback(targetFeedbackEl, emptyMessage);
    showState(targetEmptyEl, targetChartEl, { showEmpty: true, showChart: false });
    return;
  }

  const { data, layout, config } = payloadFactory(items);
  const hasVisibleData = data.some((trace) =>
    Array.isArray(trace.y) && trace.y.some((value) => Number.isFinite(value))
  );

  if (!hasVisibleData) {
    setFeedback(targetFeedbackEl, emptyMessage);
    showState(targetEmptyEl, targetChartEl, { showEmpty: true, showChart: false });
    return;
  }

  await plotVisible(targetEmptyEl, targetChartEl, data, layout, config);
  setFeedback(targetFeedbackEl, "");
}

async function renderProjectMonthlyCharts() {
  const filteredItems = getFilteredProjectMonthlyItems();

  setFeedback(
    projectMonthlyFeedbackEl,
    filteredItems.length
      ? `Gráficos mensais atualizados com ${filteredItems.length} combinação(ões).`
      : "Sem dados mensais para o filtro atual."
  );

  await Promise.all([
    renderChartOrEmpty({
      items: filteredItems,
      chartEl: chart4El,
      emptyEl: empty4El,
      feedbackEl: feedback4El,
      payloadFactory: toMonthlyLeadTimeChartPayload,
      emptyMessage: "Sem dados de lead time real para o filtro atual.",
    }),
    renderChartOrEmpty({
      items: filteredItems,
      chartEl: chart5El,
      emptyEl: empty5El,
      feedbackEl: feedback5El,
      payloadFactory: toMonthlyDelayChartPayload,
      emptyMessage: "Sem dados de atraso para o filtro atual.",
    }),
    renderChartOrEmpty({
      items: filteredItems,
      chartEl: chart6El,
      emptyEl: empty6El,
      feedbackEl: feedback6El,
      payloadFactory: toMonthlyEfficiencyChartPayload,
      emptyMessage: "Sem dados de eficiência para o filtro atual.",
    }),
    renderChartOrEmpty({
      items: filteredItems,
      chartEl: chart7El,
      emptyEl: empty7El,
      feedbackEl: feedback7El,
      payloadFactory: toMonthlySlaBreachChartPayload,
      emptyMessage: "Sem dados de estouro de prazo para o filtro atual.",
    }),
  ]);
}

function rerenderProjectMonthlyCharts() {
  renderProjectMonthlyCharts().catch((err) => {
    const message = err?.message || "Erro ao atualizar gráficos mensais.";
    setFeedback(projectMonthlyFeedbackEl, message, "error");
    showState(empty4El, chart4El, { showEmpty: false, showChart: false });
    showState(empty5El, chart5El, { showEmpty: false, showChart: false });
    showState(empty6El, chart6El, { showEmpty: false, showChart: false });
    showState(empty7El, chart7El, { showEmpty: false, showChart: false });
  });
}
