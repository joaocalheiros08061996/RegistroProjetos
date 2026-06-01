function toAvgRealChartPayload(items) {
  const timeUnit = getDashboardTimeUnit();
  const unitLabel = getDashboardTimeUnitLabel(timeUnit);
  const labels = items.map((item) => item.project_type_label);
  const dayValues = items.map((item) => Number(item.average_days || 0));
  const values = dayValues.map((value) => convertDaysToDashboardUnit(value, timeUnit));
  const maxValue = Math.max(...values, 0);
  const xAxisMax = maxValue > 0 ? maxValue * 1.2 : 1;
  const barColors = [
    "#2F80ED",
    "#27AE60",
    "#F2994A",
    "#EB5757",
    "#9B51E0",
    "#00A7A0",
    "#F2C94C",
    "#56CCF2",
  ];


  return {
    data: [
      {
        type: "bar",
        orientation: "h",
        y: labels,
        x: values,
        text: dayValues.map((value) => formatDashboardDurationLabelFromDays(value, timeUnit)),
        textposition: "outside",
        textfont: {
          color: "#2c3e50",
          size: 14,
          family: "Manrope, Avenir Next, Segoe UI, sans-serif",
        },
        cliponaxis: false,
        marker: {
          color: values.map((_, index) => barColors[index % barColors.length]),
          line: {
            color: "#ffffff",
            width: 2,
          },
        },
        hovertemplate: `%{y}<br>%{x:.1f} ${unitLabel}<extra></extra>`,
        opacity: 0.95,
        showlegend: false,
      },
    ],
    layout: {
      title: {
        text: "📈 Lead Time Médio por Tipo de Projeto",
        x: 0.5,
        xanchor: "center",
        font: {
          size: 24,
          color: "#2c3e50",
        },
      },
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#f8fafc",
      margin: {
        l: 220,
        r: 120,
        t: 78,
        b: 74,
      },
      xaxis: {
        range: [0, xAxisMax],
        tickformat: ".1f",
        title: {
          text: `<b>Lead Time Médio (${unitLabel})</b>`,
          font: {
            size: 16,
          },
        },
        gridcolor: "rgba(44, 62, 80, 0.12)",
        griddash: "dash",
        zeroline: false,
        ticks: "outside",
        tickfont: {
          size: 13,
        },
      },
      yaxis: {
        autorange: "reversed",
        tickfont: {
          size: 16,
        },
        ticks: "",
        automargin: true,
      },
    },
    config: {
      responsive: true,
      displayModeBar: false,
    },
  };
}

function toPlannedVsRealChartPayload(items) {
  const timeUnit = getDashboardTimeUnit();
  const unitLabel = getDashboardTimeUnitLabel(timeUnit);
  const labels = items.map((item) => item.project_type_label);
  const plannedDayValues = items.map((item) => Number(item.planned_average_days || 0));
  const realDayValues = items.map((item) => Number(item.real_average_days || 0));
  const plannedValues = plannedDayValues.map((value) => convertDaysToDashboardUnit(value, timeUnit));
  const realValues = realDayValues.map((value) => convertDaysToDashboardUnit(value, timeUnit));
  const maxValue = Math.max(...plannedValues, ...realValues, 0);
  const xAxisMax = maxValue > 0 ? maxValue * 1.2 : 1;

  const data = [
    {
      type: "bar",
      name: "Planejado",
      orientation: "h",
      y: labels,
      x: plannedValues,
      marker: {
        color: "#2F80ED",
        line: {
          color: "#ffffff",
          width: 1.6,
        },
      },
      text: plannedDayValues.map((value) => formatDashboardDurationLabelFromDays(value, timeUnit)),
      textposition: "outside",
      textfont: {
        color: "#2c3e50",
        size: 13,
        family: "Manrope, Avenir Next, Segoe UI, sans-serif",
      },
      cliponaxis: false,
      hovertemplate: `%{y}<br>Planejado: %{x:.1f} ${unitLabel}<extra></extra>`,
      opacity: 0.94,
    },
    {
      type: "bar",
      name: "Real",
      orientation: "h",
      y: labels,
      x: realValues,
      marker: {
        color: "#F2994A",
        line: {
          color: "#ffffff",
          width: 1.6,
        },
      },
      text: realDayValues.map((value) => formatDashboardDurationLabelFromDays(value, timeUnit)),
      textposition: "outside",
      textfont: {
        color: "#2c3e50",
        size: 13,
        family: "Manrope, Avenir Next, Segoe UI, sans-serif",
      },
      cliponaxis: false,
      hovertemplate: `%{y}<br>Real: %{x:.1f} ${unitLabel}<extra></extra>`,
      opacity: 0.94,
    },
  ];

  return {
    data,
    layout: {
      barmode: "group",
      title: {
        text: "📊 Lead Time Médio: Planejado vs Real por Tipo de Projeto",
        x: 0.5,
        xanchor: "center",
        y: 0.98,
        yanchor: "top",
        pad: {
          b: 10,
        },
        font: {
          size: 24,
          color: "#2c3e50",
        },
      },
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#f8fafc",
      margin: {
        l: 220,
        r: 130,
        t: 128,
        b: 74,
      },
      xaxis: {
        range: [0, xAxisMax],
        tickformat: ".1f",
        title: {
          text: `<b>Lead Time Médio (${unitLabel})</b>`,
          font: {
            size: 16,
          },
        },
        gridcolor: "rgba(44, 62, 80, 0.12)",
        griddash: "dash",
        zeroline: false,
        ticks: "outside",
        tickfont: {
          size: 13,
        },
      },
      yaxis: {
        autorange: "reversed",
        automargin: true,
        tickfont: {
          size: 16,
        },
        ticks: "",
      },
      legend: {
        orientation: "h",
        x: 0.5,
        y: 1.12,
        xanchor: "center",
        yanchor: "bottom",
        bgcolor: "rgba(255,255,255,0.0)",
        font: {
          size: 13,
          color: "#2c3e50",
        },
      },
    },
    config: {
      responsive: true,
      displayModeBar: false,
    },
  };
}

async function renderAvgRealChart() {
  setFeedback(feedbackEl, "Carregando gráfico...");
  showState(emptyEl, chartEl, { showEmpty: false, showChart: false });

  const payload = await apiFetch("/dashboard/avg-real-days-by-project-type");
  const items = Array.isArray(payload?.items) ? payload.items : [];
  avgRealItems = items;

  if (!items.length) {
    setFeedback(feedbackEl, "Sem dados para exibir no momento.");
    showState(emptyEl, chartEl, { showEmpty: true, showChart: false });
    return;
  }

  const { data, layout, config } = toAvgRealChartPayload(items);
  await plotVisible(emptyEl, chartEl, data, layout, config);
  setFeedback(feedbackEl, `Gráfico atualizado com ${items.length} tipo(s).`);
}

async function renderPlannedVsRealChart() {
  setFeedback(feedback2El, "Carregando gráfico...");
  showState(empty2El, chart2El, { showEmpty: false, showChart: false });

  const payload = await apiFetch("/dashboard/avg-planned-vs-real-days-by-project-type");
  const items = Array.isArray(payload?.items) ? payload.items : [];

  if (!items.length) {
    setFeedback(feedback2El, "Sem dados para exibir no momento.");
    showState(empty2El, chart2El, { showEmpty: true, showChart: false });
    return;
  }

  const { data, layout, config } = toPlannedVsRealChartPayload(items);
  await plotVisible(empty2El, chart2El, data, layout, config);
  setFeedback(feedback2El, `Gráfico atualizado com ${items.length} tipo(s).`);
}
