function toProjectComplexityChartPayload(items) {
  const groupedByType = new Map();
  const scores = [...new Set(
    items.map((item) => Number(item.complexity_score))
  )]
    .filter((score) => Number.isFinite(score) && score >= 1 && score <= 5)
    .sort((a, b) => a - b);

  for (const item of items) {
    const typeKey = item.project_type;
    const current = groupedByType.get(typeKey) || {
      label: item.project_type_label || item.project_type,
      total: 0,
      scores: new Map(),
    };
    const score = Number(item.complexity_score);
    const count = Number(item.project_count || 0);

    current.total += count;
    current.scores.set(score, (current.scores.get(score) || 0) + count);
    groupedByType.set(typeKey, current);
  }

  const typeItems = [...groupedByType.values()].sort((a, b) => {
    if (b.total !== a.total) {
      return b.total - a.total;
    }
    return a.label.localeCompare(b.label, "pt-BR");
  });

  const labels = typeItems.map((item) => item.label);
  const maxValue = Math.max(
    0,
    ...typeItems.flatMap((item) =>
      scores.map((score) => Number(item.scores.get(score) || 0))
    )
  );
  const yAxisMax = maxValue > 0 ? maxValue * 1.28 : 1;

  return {
    data: scores.map((score) => {
      const values = typeItems.map((item) => Number(item.scores.get(score) || 0));
      return {
        type: "bar",
        name: `Complexidade ${score}`,
        x: labels,
        y: values,
        marker: {
          color: complexityColor(score),
          opacity: 0.95,
          line: {
            color: "#ffffff",
            width: 1.4,
          },
        },
        text: values.map((value) => (value > 0 ? String(value) : "")),
        textposition: "outside",
        textfont: {
          color: "#2c3e50",
          size: 12,
          family: "Manrope, Avenir Next, Segoe UI, sans-serif",
        },
        cliponaxis: false,
        hovertemplate: `%{x}<br>Complexidade ${score}: %{y} projeto(s)<extra></extra>`,
      };
    }),
    layout: {
      barmode: "group",
      bargap: 0.22,
      bargroupgap: 0.08,
      title: {
        text: "Quantidade de Projetos por Complexidade",
        x: 0.5,
        xanchor: "center",
        font: {
          size: 24,
          color: "#2c3e50",
          family: "Manrope, Avenir Next, Segoe UI, sans-serif",
        },
      },
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#f8fafc",
      margin: {
        l: 88,
        r: 48,
        t: 86,
        b: 132,
      },
      xaxis: {
        title: {
          text: "<b>Tipo de Projeto</b>",
          standoff: 18,
          font: {
            size: 16,
            color: "#2c3e50",
            family: "Manrope, Avenir Next, Segoe UI, sans-serif",
          },
        },
        tickangle: -35,
        tickfont: {
          size: 13,
          color: "#516278",
          family: "Manrope, Avenir Next, Segoe UI, sans-serif",
        },
        automargin: true,
        showgrid: false,
        zeroline: false,
      },
      yaxis: {
        range: [0, yAxisMax],
        dtick: maxValue <= 10 ? 1 : undefined,
        rangemode: "tozero",
        title: {
          text: "<b>Quantidade de Projetos</b>",
          standoff: 16,
          font: {
            size: 16,
            color: "#2c3e50",
            family: "Manrope, Avenir Next, Segoe UI, sans-serif",
          },
        },
        tickfont: {
          size: 13,
          color: "#516278",
          family: "Manrope, Avenir Next, Segoe UI, sans-serif",
        },
        gridcolor: "rgba(44, 62, 80, 0.12)",
        griddash: "dash",
        zeroline: false,
      },
      legend: {
        title: {
          text: "Nível de Complexidade",
        },
        orientation: "h",
        x: 0.5,
        y: -0.28,
        xanchor: "center",
        yanchor: "top",
        font: {
          size: 12,
          color: "#2c3e50",
          family: "Manrope, Avenir Next, Segoe UI, sans-serif",
        },
      },
      hoverlabel: {
        bgcolor: "#112338",
        bordercolor: "#112338",
        font: {
          color: "#ffffff",
          family: "Manrope, Avenir Next, Segoe UI, sans-serif",
        },
      },
    },
    config: {
      responsive: true,
      displayModeBar: false,
    },
  };
}

function aggregateComplexityMonthlyItems(items) {
  const grouped = new Map();

  for (const item of items) {
    const year = Number(item.year);
    const month = Number(item.month);
    const score = Number(item.complexity_score);
    const count = Number(item.project_count || 0);

    if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(score)) {
      continue;
    }

    const key = `${year}-${String(month).padStart(2, "0")}`;
    const current = grouped.get(key) || {
      year,
      month,
      monthLabel: item.month_label,
      periodLabel: item.period_label,
      total: 0,
      scores: new Map(),
    };

    current.total += count;
    current.scores.set(score, (current.scores.get(score) || 0) + count);
    grouped.set(key, current);
  }

  return [...grouped.values()].sort((a, b) => {
    if (a.year !== b.year) {
      return a.year - b.year;
    }
    return a.month - b.month;
  });
}

function toProjectComplexityByMonthChartPayload(items) {
  const aggregatedItems = aggregateComplexityMonthlyItems(items);
  const scores = [...new Set(
    items.map((item) => Number(item.complexity_score))
  )]
    .filter((score) => Number.isFinite(score) && score >= 1 && score <= 5)
    .sort((a, b) => a - b);
  const monthLabels = aggregatedItems.map((item) => item.monthLabel);
  const yearLabels = aggregatedItems.map((item) => String(item.year));
  const periodLabels = aggregatedItems.map((item) => item.periodLabel);
  const maxTotal = Math.max(0, ...aggregatedItems.map((item) => item.total));
  const yAxisMax = maxTotal > 0 ? maxTotal * 1.2 : 1;

  return {
    data: scores.map((score) => {
      const values = aggregatedItems.map((item) => Number(item.scores.get(score) || 0));
      return {
        type: "bar",
        name: `Complexidade ${score}`,
        x: [monthLabels, yearLabels],
        y: values,
        customdata: periodLabels,
        marker: {
          color: complexityColor(score),
          opacity: 0.95,
          line: {
            color: "#ffffff",
            width: 1.5,
          },
        },
        text: values.map((value) => (value > 0 ? String(value) : "")),
        textposition: "inside",
        insidetextanchor: "middle",
        textfont: {
          color: complexityTextColor(score),
          size: 12,
          family: "Manrope, Avenir Next, Segoe UI, sans-serif",
        },
        cliponaxis: false,
        hovertemplate: `%{customdata}<br>Complexidade ${score}: %{y} projeto(s)<extra></extra>`,
      };
    }),
    layout: {
      ...projectMonthlyBaseLayout(
        "Quantidade de Projetos por Complexidade por Mês",
        "Quantidade de Projetos"
      ),
      barmode: "stack",
      bargap: 0.34,
      uniformtext: {
        mode: "show",
        minsize: 10,
      },
      xaxis: {
        ...projectMonthlyBaseLayout("", "Quantidade de Projetos").xaxis,
        type: "multicategory",
        tickangle: -28,
        title: {
          ...projectMonthlyBaseLayout("", "Quantidade de Projetos").xaxis.title,
          text: "<b>Mês/Ano</b>",
        },
      },
      yaxis: {
        ...projectMonthlyBaseLayout("", "Quantidade de Projetos").yaxis,
        range: [0, yAxisMax],
        dtick: maxTotal <= 10 ? 1 : undefined,
        rangemode: "tozero",
      },
      legend: {
        ...projectMonthlyBaseLayout("", "Quantidade de Projetos").legend,
        title: {
          text: "Nível de Complexidade",
        },
      },
    },
    config: projectMonthlyConfig(),
  };
}

async function renderProjectComplexityChart() {
  setFeedback(feedback8El, "Carregando gráfico...");
  showState(empty8El, chart8El, { showEmpty: false, showChart: false });

  const payload = await apiFetch("/dashboard/project-complexity-counts");
  const items = Array.isArray(payload?.items) ? payload.items : [];

  if (!items.length) {
    setFeedback(feedback8El, "Sem dados para exibir no momento.");
    showState(empty8El, chart8El, { showEmpty: true, showChart: false });
    return;
  }

  const { data, layout, config } = toProjectComplexityChartPayload(items);
  await plotVisible(empty8El, chart8El, data, layout, config);

  const totalProjects = items.reduce(
    (acc, item) => acc + Number(item.project_count || 0),
    0
  );
  const totalScores = new Set(items.map((item) => item.complexity_score)).size;
  setFeedback(
    feedback8El,
    `Gráfico atualizado com ${totalProjects} projeto(s) e ${totalScores} complexidade(s).`
  );
}

async function loadComplexityMonthlyData() {
  setFeedback(feedback9El, "Carregando gráfico...");
  showState(empty9El, chart9El, { showEmpty: false, showChart: false });

  const payload = await apiFetch("/dashboard/project-complexity-counts-by-month");
  complexityMonthlyItems = Array.isArray(payload?.items) ? payload.items : [];
  buildComplexityMonthlyFilterOptions(complexityMonthlyItems);
  await renderComplexityMonthlyChart();
}

async function renderComplexityMonthlyChart() {
  const filteredItems = getFilteredComplexityMonthlyItems();

  if (!filteredItems.length) {
    setFeedback(feedback9El, "Sem dados para exibir no filtro atual.");
    showState(empty9El, chart9El, { showEmpty: true, showChart: false });
    return;
  }

  const { data, layout, config } = toProjectComplexityByMonthChartPayload(filteredItems);
  const hasVisibleData = data.some((trace) =>
    Array.isArray(trace.y) && trace.y.some((value) => Number(value) > 0)
  );

  if (!hasVisibleData) {
    setFeedback(feedback9El, "Sem dados para exibir no filtro atual.");
    showState(empty9El, chart9El, { showEmpty: true, showChart: false });
    return;
  }

  await plotVisible(empty9El, chart9El, data, layout, config);

  const totalProjects = filteredItems.reduce(
    (acc, item) => acc + Number(item.project_count || 0),
    0
  );
  const periods = aggregateComplexityMonthlyItems(filteredItems).length;
  setFeedback(
    feedback9El,
    `Gráfico atualizado com ${totalProjects} projeto(s) em ${periods} período(s).`
  );
}

function rerenderComplexityMonthlyChart() {
  renderComplexityMonthlyChart().catch((err) => {
    const message = err?.message || "Erro ao atualizar gráfico mensal de complexidade.";
    setFeedback(feedback9El, message, "error");
    showState(empty9El, chart9El, { showEmpty: false, showChart: false });
  });
}
