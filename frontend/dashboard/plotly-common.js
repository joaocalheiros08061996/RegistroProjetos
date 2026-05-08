function waitForFrame() {
  return new Promise((resolve) => requestAnimationFrame(resolve));
}

async function plotVisible(emptyTarget, chartTarget, data, layout, config) {
  showState(emptyTarget, chartTarget, { showEmpty: false, showChart: true });
  await waitForFrame();
  await Plotly.newPlot(chartTarget, data, layout, config);
  await waitForFrame();
  Plotly.Plots.resize(chartTarget);
}

function projectMonthlyBaseLayout(title, yTitle) {
  const fontFamily = "Manrope, Avenir Next, Segoe UI, sans-serif";

  return {
    title: {
      text: title,
      x: 0.5,
      xanchor: "center",
      y: 0.97,
      yanchor: "top",
      font: {
        size: 22,
        color: "#2c3e50",
        family: fontFamily,
      },
    },
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#f8fafc",
    margin: {
      l: 86,
      r: 54,
      t: 86,
      b: 104,
    },
    autosize: true,
    xaxis: {
      title: {
        text: "<b>Mês/Ano</b>",
        standoff: 14,
        font: {
          size: 15,
          color: "#2c3e50",
          family: fontFamily,
        },
      },
      tickangle: -25,
      tickfont: {
        size: 12,
        color: "#516278",
        family: fontFamily,
      },
      showgrid: false,
      zeroline: false,
      linecolor: "#dce7f2",
      linewidth: 1,
      automargin: true,
    },
    yaxis: {
      title: {
        text: `<b>${yTitle}</b>`,
        standoff: 14,
        font: {
          size: 15,
          color: "#2c3e50",
          family: fontFamily,
        },
      },
      tickfont: {
        size: 12,
        color: "#516278",
        family: fontFamily,
      },
      gridcolor: "rgba(44, 62, 80, 0.12)",
      griddash: "dash",
      zeroline: false,
      linecolor: "#dce7f2",
      linewidth: 1,
      automargin: true,
    },
    legend: {
      orientation: "h",
      y: -0.24,
      x: 0.5,
      xanchor: "center",
      yanchor: "top",
      bgcolor: "rgba(255,255,255,0)",
      font: {
        size: 12,
        color: "#2c3e50",
        family: fontFamily,
      },
    },
    hoverlabel: {
      bgcolor: "#112338",
      bordercolor: "#112338",
      font: {
        color: "#ffffff",
        family: fontFamily,
      },
    },
  };
}

function projectMonthlyLineStyle(color) {
  return {
    color,
    width: 3,
    shape: "spline",
  };
}

function projectMonthlyMarkerStyle(color) {
  return {
    color,
    size: 7,
    line: {
      color: "#ffffff",
      width: 1.4,
    },
  };
}

function projectMonthlyBarStyle(color) {
  return {
    color,
    opacity: 0.95,
    line: {
      color: "#ffffff",
      width: 1.6,
    },
  };
}

function projectMonthlyTextStyle(color = "#2c3e50") {
  return {
    color,
    size: 12,
    family: "Manrope, Avenir Next, Segoe UI, sans-serif",
  };
}

function projectMonthlySlaRange(values) {
  const maxValue = Math.max(0, ...finiteNumbers(values));
  if (maxValue <= 0) {
    return [0, 100];
  }
  return [0, Math.min(100, Math.max(10, maxValue * 1.25))];
}

function projectMonthlySignedRange(values) {
  const finiteValues = finiteNumbers(values);
  if (!finiteValues.length) {
    return [-1, 1];
  }

  const minValue = Math.min(...finiteValues);
  const maxValue = Math.max(...finiteValues);
  const padding = Math.max((maxValue - minValue) * 0.18, 0.5);
  return [minValue - padding, maxValue + padding];
}

function projectMonthlyEfficiencyRange(values) {
  const maxValue = Math.max(0, ...finiteNumbers(values));
  return [0, maxValue > 0 ? maxValue * 1.2 : 100];
}

function projectMonthlyConfig() {
  return {
    responsive: true,
    displayModeBar: false,
  };
}
