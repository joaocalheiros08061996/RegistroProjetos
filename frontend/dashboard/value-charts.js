function toEarnedValueChartPayload(items) {
  const aggregatedItems = aggregateEarnedValueItems(items);
  const periodLabels = aggregatedItems.map((item) => item.periodLabel);
  const plannedValues = aggregatedItems.map((item) => item.plannedValue);
  const earnedValues = aggregatedItems.map((item) => item.earnedValue);
  const moneyValues = [...plannedValues, ...earnedValues];

  return {
    data: [
      {
        type: "bar",
        name: "Valor Agregado (VA)",
        x: periodLabels,
        y: earnedValues,
        marker: projectMonthlyBarStyle("#27AE60"),
        text: earnedValues.map(formatCompactMoney),
        textposition: "outside",
        textfont: projectMonthlyTextStyle(),
        cliponaxis: false,
        customdata: aggregatedItems.map((item) => [
          formatMoney(item.earnedValue),
          formatMoney(item.plannedValue),
          formatMoney(item.plannedLaborCost),
          item.projectCount,
          item.completedTaskCount,
        ]),
        hovertemplate: "%{x}<br>VA: %{customdata[0]}<br>VP referência: %{customdata[1]}<br>Mão de obra planejada: %{customdata[2]}<br>Projetos: %{customdata[3]}<br>Tarefas concluídas: %{customdata[4]}<extra></extra>",
      },
      {
        type: "scatter",
        mode: "lines+markers",
        name: "Valor Planejado (VP - referência)",
        x: periodLabels,
        y: plannedValues,
        line: {
          ...projectMonthlyLineStyle("#2F80ED"),
          dash: "dash",
        },
        marker: projectMonthlyMarkerStyle("#2F80ED"),
        customdata: aggregatedItems.map((item) => [
          formatMoney(item.earnedValue),
          formatMoney(item.plannedValue),
          formatMoney(item.plannedLaborCost),
          item.projectCount,
          item.completedTaskCount,
        ]),
        hovertemplate: "%{x}<br>VA: %{customdata[0]}<br>VP referência: %{customdata[1]}<br>Mão de obra planejada: %{customdata[2]}<br>Projetos: %{customdata[3]}<br>Tarefas concluídas: %{customdata[4]}<extra></extra>",
      },
    ],
    layout: {
      ...projectMonthlyBaseLayout(
        "Valor Agregado por Mês",
        "Valor (R$)"
      ),
      bargap: 0.42,
      yaxis: {
        ...projectMonthlyBaseLayout("", "Valor (R$)").yaxis,
        range: earnedValueRange(moneyValues),
        tickprefix: "R$ ",
        tickformat: ",.0f",
        rangemode: "tozero",
      },
      legend: {
        ...projectMonthlyBaseLayout("", "Valor (R$)").legend,
        y: -0.28,
      },
    },
    config: projectMonthlyConfig(),
  };
}

function schedulePerformanceStatus(value) {
  if (value < 1) {
    return "Atrasado";
  }
  if (value > 1) {
    return "Adiantado";
  }
  return "No prazo";
}

function schedulePerformanceColor(value) {
  if (value < 1) {
    return "#EB5757";
  }
  if (value > 1) {
    return "#27AE60";
  }
  return "#F2C94C";
}

function getSchedulePerformancePoints(items) {
  return aggregateEarnedValueItems(items)
    .map((item) => {
      const plannedValue = Number(item.plannedValue || 0);
      const earnedValue = Number(item.earnedValue || 0);
      const idp = plannedValue > 0 ? earnedValue / plannedValue : null;

      return {
        ...item,
        idp,
      };
    })
    .filter((item) => Number.isFinite(item.idp));
}

function schedulePerformanceRange(values) {
  const numericValues = finiteNumbers(values);
  const maxValue = Math.max(1, ...numericValues);
  return [0, maxValue > 0 ? maxValue * 1.18 : 1.2];
}

function toSchedulePerformanceChartPayload(items) {
  const points = getSchedulePerformancePoints(items);
  const periodLabels = points.map((item) => item.periodLabel);
  const idpValues = points.map((item) => item.idp);

  return {
    data: [
      {
        type: "scatter",
        mode: "lines+markers+text",
        name: "IDP (VA / VP)",
        x: periodLabels,
        y: idpValues,
        text: idpValues.map(formatIdp),
        textposition: "top center",
        textfont: projectMonthlyTextStyle(),
        line: projectMonthlyLineStyle("#2F80ED"),
        marker: {
          color: idpValues.map(schedulePerformanceColor),
          size: 11,
          line: {
            color: "#ffffff",
            width: 2,
          },
        },
        customdata: points.map((item) => [
          formatIdp(item.idp),
          schedulePerformanceStatus(item.idp),
          formatMoney(item.earnedValue),
          formatMoney(item.plannedValue),
          item.projectCount,
          item.completedTaskCount,
        ]),
        hovertemplate: "%{x}<br>IDP: %{customdata[0]} (%{customdata[1]})<br>VA: %{customdata[2]}<br>VP: %{customdata[3]}<br>Projetos: %{customdata[4]}<br>Tarefas concluídas: %{customdata[5]}<extra></extra>",
      },
      {
        type: "scatter",
        mode: "lines",
        name: "Referência 1.00",
        x: periodLabels,
        y: periodLabels.map(() => 1),
        line: {
          color: "#7F8C8D",
          width: 2,
          dash: "dash",
        },
        hovertemplate: "%{x}<br>Referência de prazo: 1.00<extra></extra>",
      },
    ],
    layout: {
      ...projectMonthlyBaseLayout(
        "Índice de Desempenho de Prazo por Mês",
        "IDP (VA / VP)"
      ),
      yaxis: {
        ...projectMonthlyBaseLayout("", "IDP (VA / VP)").yaxis,
        range: schedulePerformanceRange(idpValues),
        tickformat: ".2f",
        rangemode: "tozero",
      },
      legend: {
        ...projectMonthlyBaseLayout("", "IDP (VA / VP)").legend,
        y: -0.28,
      },
    },
    config: projectMonthlyConfig(),
  };
}

function costPerformanceStatus(value) {
  if (value < 1) {
    return "Acima do orçamento";
  }
  if (value > 1) {
    return "Abaixo do orçamento";
  }
  return "Dentro do orçamento";
}

function costPerformanceColor(value) {
  if (value < 1) {
    return "#EB5757";
  }
  if (value > 1) {
    return "#27AE60";
  }
  return "#F2C94C";
}

function getCostPerformancePoints(items) {
  return aggregateEarnedValueItems(items)
    .map((item) => {
      const actualCost = Number(item.actualCost || item.totalTaskCost || 0);
      const earnedValue = Number(item.earnedValue || 0);
      const idc = actualCost > 0 ? earnedValue / actualCost : null;

      return {
        ...item,
        actualCost,
        idc,
      };
    })
    .filter((item) => Number.isFinite(item.idc));
}

function costPerformanceRange(values) {
  const numericValues = finiteNumbers(values);
  const maxValue = Math.max(1, ...numericValues);
  return [0, maxValue > 0 ? maxValue * 1.18 : 1.2];
}

function toCostPerformanceChartPayload(items) {
  const points = getCostPerformancePoints(items);
  const periodLabels = points.map((item) => item.periodLabel);
  const idcValues = points.map((item) => item.idc);

  return {
    data: [
      {
        type: "bar",
        name: "IDC (VA / Custo Real)",
        x: periodLabels,
        y: idcValues,
        marker: {
          color: idcValues.map(costPerformanceColor),
          line: {
            color: "#ffffff",
            width: 2,
          },
        },
        text: idcValues.map(formatIdp),
        textposition: "outside",
        textfont: projectMonthlyTextStyle(),
        cliponaxis: false,
        customdata: points.map((item) => [
          formatIdp(item.idc),
          costPerformanceStatus(item.idc),
          formatMoney(item.earnedValue),
          formatMoney(item.actualCost),
          formatMoney(item.actualLaborCost),
          item.projectCount,
          item.completedTaskCount,
        ]),
        hovertemplate: "%{x}<br>IDC: %{customdata[0]} (%{customdata[1]})<br>VA: %{customdata[2]}<br>Custo real total: %{customdata[3]}<br>Mão de obra real: %{customdata[4]}<br>Projetos: %{customdata[5]}<br>Tarefas concluídas: %{customdata[6]}<extra></extra>",
      },
      {
        type: "scatter",
        mode: "lines",
        name: "Referência 1.00",
        x: periodLabels,
        y: periodLabels.map(() => 1),
        line: {
          color: "#7F8C8D",
          width: 2,
          dash: "dash",
        },
        hovertemplate: "%{x}<br>Referência de custo: 1.00<extra></extra>",
      },
    ],
    layout: {
      ...projectMonthlyBaseLayout(
        "Índice de Desempenho de Custo por Mês",
        "IDC (VA / Custo Real)"
      ),
      bargap: 0.45,
      yaxis: {
        ...projectMonthlyBaseLayout("", "IDC (VA / Custo Real)").yaxis,
        range: costPerformanceRange(idcValues),
        tickformat: ".2f",
        rangemode: "tozero",
      },
      legend: {
        ...projectMonthlyBaseLayout("", "IDC (VA / Custo Real)").legend,
        y: -0.28,
      },
    },
    config: projectMonthlyConfig(),
  };
}

async function loadEarnedValueData() {
  setFeedback(feedback10El, "Carregando gráfico...");
  showState(empty10El, chart10El, { showEmpty: false, showChart: false });
  setFeedback(feedback11El, "Carregando gráfico...");
  showState(empty11El, chart11El, { showEmpty: false, showChart: false });
  setFeedback(feedback12El, "Carregando gráfico...");
  showState(empty12El, chart12El, { showEmpty: false, showChart: false });

  const payload = await apiFetch("/dashboard/project-earned-value");
  earnedValueItems = Array.isArray(payload?.items) ? payload.items : [];
  buildEarnedValueFilterOptions(earnedValueItems);
  buildSchedulePerformanceFilterOptions(earnedValueItems);
  buildCostPerformanceFilterOptions(earnedValueItems);
  await renderEarnedValueChart();
  await renderSchedulePerformanceChart();
  await renderCostPerformanceChart();
}

async function renderEarnedValueChart() {
  const filteredItems = getFilteredEarnedValueItems();

  if (!filteredItems.length) {
    setFeedback(feedback10El, "Sem dados para exibir no filtro atual.");
    showState(empty10El, chart10El, { showEmpty: true, showChart: false });
    return;
  }

  const { data, layout, config } = toEarnedValueChartPayload(filteredItems);
  const hasVisibleData = data.some((trace) =>
    Array.isArray(trace.y) && trace.y.some((value) => Number(value) > 0)
  );

  if (!hasVisibleData) {
    setFeedback(feedback10El, "Sem valores positivos para exibir no filtro atual.");
    showState(empty10El, chart10El, { showEmpty: true, showChart: false });
    return;
  }

  await plotVisible(empty10El, chart10El, data, layout, config);

  const totalProjects = filteredItems.length;
  const periods = aggregateEarnedValueItems(filteredItems).length;
  setFeedback(
    feedback10El,
    `Gráfico atualizado com ${totalProjects} projeto(s) em ${periods} período(s).`
  );
}

function rerenderEarnedValueChart() {
  renderEarnedValueChart().catch((err) => {
    const message = err?.message || "Erro ao atualizar gráfico de valor agregado.";
    setFeedback(feedback10El, message, "error");
    showState(empty10El, chart10El, { showEmpty: false, showChart: false });
  });
}

async function renderSchedulePerformanceChart() {
  const filteredItems = getFilteredSchedulePerformanceItems();
  const points = getSchedulePerformancePoints(filteredItems);

  if (!filteredItems.length || !points.length) {
    setFeedback(feedback11El, "Sem dados com VP positivo para calcular IDP no filtro atual.");
    showState(empty11El, chart11El, { showEmpty: true, showChart: false });
    return;
  }

  const { data, layout, config } = toSchedulePerformanceChartPayload(filteredItems);
  await plotVisible(empty11El, chart11El, data, layout, config);

  setFeedback(
    feedback11El,
    `Gráfico atualizado com ${filteredItems.length} projeto(s) em ${points.length} período(s).`
  );
}

function rerenderSchedulePerformanceChart() {
  renderSchedulePerformanceChart().catch((err) => {
    const message = err?.message || "Erro ao atualizar gráfico de IDP.";
    setFeedback(feedback11El, message, "error");
    showState(empty11El, chart11El, { showEmpty: false, showChart: false });
  });
}

async function renderCostPerformanceChart() {
  const filteredItems = getFilteredCostPerformanceItems();
  const points = getCostPerformancePoints(filteredItems);

  if (!filteredItems.length || !points.length) {
    setFeedback(feedback12El, "Sem dados com VA e custo real positivo para calcular IDC no filtro atual.");
    showState(empty12El, chart12El, { showEmpty: true, showChart: false });
    return;
  }

  const { data, layout, config } = toCostPerformanceChartPayload(filteredItems);
  await plotVisible(empty12El, chart12El, data, layout, config);

  setFeedback(
    feedback12El,
    `Gráfico atualizado com ${filteredItems.length} projeto(s) em ${points.length} período(s).`
  );
}

function rerenderCostPerformanceChart() {
  renderCostPerformanceChart().catch((err) => {
    const message = err?.message || "Erro ao atualizar gráfico de IDC.";
    setFeedback(feedback12El, message, "error");
    showState(empty12El, chart12El, { showEmpty: false, showChart: false });
  });
}
