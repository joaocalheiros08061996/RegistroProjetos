const ROUTINE_TYPE_ALL_VALUE = "ALL";

let selectedRoutineActivityTypes = new Set();
let availableRoutineActivityTypes = [];
let routineTypeFilterChangeHandler = null;

function buildRoutineFilterOptions(items) {
  const activityTypes = [...new Set(items.map((item) => item.activity_type))]
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b, "pt-BR"));

  const responsaveisByLabel = new Map();
  for (const item of items) {
    const responsavelLabel = getRoutineResponsibleLabel(item);
    if (!responsavelLabel || responsaveisByLabel.has(responsavelLabel)) {
      continue;
    }

    responsaveisByLabel.set(responsavelLabel, {
      value: responsavelLabel,
      label: responsavelLabel,
    });
  }

  const responsaveis = [...responsaveisByLabel.values()].sort((a, b) => (
    a.label.localeCompare(b.label, "pt-BR")
  ));

  const years = [...new Set(items.map((item) => Number(item.year)))]
    .filter((year) => Number.isFinite(year))
    .sort((a, b) => a - b);

  const monthsByNumber = new Map();
  for (const item of items) {
    monthsByNumber.set(Number(item.month), item.month_label);
  }

  const months = [...monthsByNumber.entries()]
    .sort(([monthA], [monthB]) => monthA - monthB)
    .map(([month, label]) => ({ value: month, label }));

  setSelectOptions(
    routineUserFilterEl,
    [
      { value: "ALL", label: "Todos" },
      ...responsaveis,
    ],
  );

  setRoutineTypeFilterOptions(activityTypes);

  setSelectOptions(
    routineYearFilterEl,
    [
      { value: "ALL", label: "Todos" },
      ...years.map((year) => ({
        value: year,
        label: String(year),
      })),
    ],
  );

  setSelectOptions(
    routineMonthFilterEl,
    [
      { value: "ALL", label: "Todos" },
      ...months,
    ],
  );
}

function setupRoutineTypeFilterDropdown(onChange) {
  routineTypeFilterChangeHandler = onChange;

  if (!routineTypeFilterEl || !routineTypeFilterTriggerEl || !routineTypeFilterMenuEl) {
    return;
  }

  routineTypeFilterTriggerEl.addEventListener("click", () => {
    setRoutineTypeFilterOpen(!isRoutineTypeFilterOpen());
  });

  document.addEventListener("click", (event) => {
    if (!routineTypeFilterEl.contains(event.target)) {
      setRoutineTypeFilterOpen(false);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setRoutineTypeFilterOpen(false);
      routineTypeFilterTriggerEl.focus();
    }
  });
}

function isRoutineTypeFilterOpen() {
  return routineTypeFilterTriggerEl?.getAttribute("aria-expanded") === "true";
}

function setRoutineTypeFilterOpen(isOpen) {
  if (!routineTypeFilterTriggerEl || !routineTypeFilterMenuEl) {
    return;
  }

  routineTypeFilterTriggerEl.setAttribute("aria-expanded", String(isOpen));
  routineTypeFilterMenuEl.classList.toggle("hidden", !isOpen);
}

function setRoutineTypeFilterOptions(activityTypes) {
  availableRoutineActivityTypes = activityTypes;
  selectedRoutineActivityTypes = new Set(
    [...selectedRoutineActivityTypes].filter((activityType) => (
      availableRoutineActivityTypes.includes(activityType)
    )),
  );

  if (!routineTypeFilterMenuEl) {
    return;
  }

  routineTypeFilterMenuEl.innerHTML = "";
  routineTypeFilterMenuEl.appendChild(
    createRoutineTypeCheckbox({
      value: ROUTINE_TYPE_ALL_VALUE,
      label: "Todos",
      checked: selectedRoutineActivityTypes.size === 0,
      onChange: () => {
        selectedRoutineActivityTypes.clear();
        syncRoutineTypeFilterState();
        routineTypeFilterChangeHandler?.();
      },
    }),
  );

  for (const activityType of availableRoutineActivityTypes) {
    routineTypeFilterMenuEl.appendChild(
      createRoutineTypeCheckbox({
        value: activityType,
        label: activityType,
        checked: selectedRoutineActivityTypes.has(activityType),
        onChange: (checked) => {
          if (checked) {
            selectedRoutineActivityTypes.add(activityType);
          } else {
            selectedRoutineActivityTypes.delete(activityType);
          }
          syncRoutineTypeFilterState();
          routineTypeFilterChangeHandler?.();
        },
      }),
    );
  }

  syncRoutineTypeFilterState();
}

function createRoutineTypeCheckbox({ value, label, checked, onChange }) {
  const field = document.createElement("label");
  field.className = "multi-select-option";

  const input = document.createElement("input");
  input.type = "checkbox";
  input.value = value;
  input.checked = checked;
  input.addEventListener("change", () => {
    onChange(input.checked);
  });

  const text = document.createElement("span");
  text.textContent = label;

  field.append(input, text);
  return field;
}

function syncRoutineTypeFilterState() {
  if (!routineTypeFilterMenuEl || !routineTypeFilterSummaryEl) {
    return;
  }

  const selectedTypes = selectedRoutineActivityTypes;
  const allInput = routineTypeFilterMenuEl.querySelector(
    `input[value="${ROUTINE_TYPE_ALL_VALUE}"]`,
  );
  if (allInput) {
    allInput.checked = selectedTypes.size === 0;
  }

  for (const input of routineTypeFilterMenuEl.querySelectorAll("input[type='checkbox']")) {
    if (input.value === ROUTINE_TYPE_ALL_VALUE) {
      continue;
    }
    input.checked = selectedTypes.has(input.value);
  }

  if (selectedTypes.size === 0) {
    routineTypeFilterSummaryEl.textContent = "Todos";
    return;
  }

  if (selectedTypes.size === 1) {
    routineTypeFilterSummaryEl.textContent = [...selectedTypes][0];
    return;
  }

  routineTypeFilterSummaryEl.textContent = `${selectedTypes.size} selecionados`;
}

function routineItemMatchesSelectedTypes(item) {
  if (selectedRoutineActivityTypes.size === 0) {
    return true;
  }
  return selectedRoutineActivityTypes.has(item.activity_type);
}

function getRoutineResponsibleLabel(item) {
  const responsavel = String(item.responsavel || "").trim();
  if (responsavel) {
    return responsavel;
  }

  const label = String(item.user_label || "").trim();
  return label || "Sem responsável";
}

function getFilteredRoutineItems() {
  const selectedResponsavel = routineUserFilterEl.value;
  const selectedYear = routineYearFilterEl.value;
  const selectedMonth = routineMonthFilterEl.value;

  return routineItems.filter((item) => {
    if (
      selectedResponsavel !== "ALL"
      && getRoutineResponsibleLabel(item) !== selectedResponsavel
    ) {
      return false;
    }
    if (!routineItemMatchesSelectedTypes(item)) {
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

function aggregateRoutineItemsByPeriod(items) {
  const grouped = new Map();

  for (const item of items) {
    const key = `${item.year}-${String(item.month).padStart(2, "0")}`;
    const existing = grouped.get(key) || {
      year: Number(item.year),
      month: Number(item.month),
      monthLabel: item.month_label,
      periodLabel: item.period_label,
      totalDays: 0,
    };

    existing.totalDays += Number(item.total_days || 0);
    grouped.set(key, existing);
  }

  return [...grouped.values()].sort((a, b) => {
    if (a.year !== b.year) {
      return a.year - b.year;
    }
    return a.month - b.month;
  });
}

function toRoutineTotalDaysChartPayload(items) {
  const timeUnit = getDashboardTimeUnit();
  const unitLabel = getDashboardTimeUnitLabel(timeUnit);
  const unitTitle = getDashboardTimeUnitTitle(timeUnit);
  const aggregatedItems = aggregateRoutineItemsByPeriod(items);
  const monthLabels = aggregatedItems.map((item) => item.monthLabel);
  const yearLabels = aggregatedItems.map((item) => String(item.year));
  const periodLabels = aggregatedItems.map((item) => item.periodLabel);
  const dayValues = aggregatedItems.map((item) => Number(item.totalDays || 0));
  const values = dayValues.map((value) =>
    convertDaysToDashboardUnit(value, timeUnit, DASHBOARD_WORKDAY_HOURS)
  );
  const maxValue = Math.max(...values, 0);
  const yAxisMax = maxValue > 0 ? maxValue * 1.2 : 1;

  return {
    data: [
      {
        type: "bar",
        x: [monthLabels, yearLabels],
        y: values,
        customdata: periodLabels,
        marker: {
          color: "#27AE60",
          line: {
            color: "#ffffff",
            width: 1.8,
          },
        },
        text: dayValues.map((value) =>
          formatDashboardDurationLabelFromDays(value, timeUnit, DASHBOARD_WORKDAY_HOURS)
        ),
        textposition: "outside",
        textfont: {
          color: "#2c3e50",
          size: 13,
          family: "Manrope, Avenir Next, Segoe UI, sans-serif",
        },
        cliponaxis: false,
        hovertemplate: `%{customdata}<br>${unitTitle} totais: %{y:.1f} ${unitLabel}<extra></extra>`,
        opacity: 0.95,
      },
    ],
    layout: {
      title: {
        text: `${unitTitle} Totais para Atividades de Rotina`,
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
        l: 80,
        r: 48,
        t: 76,
        b: 88,
      },
      xaxis: {
        type: "multicategory",
        title: {
          text: "<b>Mês/Ano</b>",
          font: {
            size: 16,
          },
        },
        tickfont: {
          size: 14,
          color: "#2c3e50",
          family: "Manrope, Avenir Next, Segoe UI, sans-serif",
        },
        showgrid: false,
      },
      yaxis: {
        range: [0, yAxisMax],
        tickformat: ".1f",
        rangemode: "tozero",
        title: {
          text: `<b>${unitTitle} totais</b>`,
          font: {
            size: 16,
          },
        },
        tickfont: {
          size: 13,
          color: "#2c3e50",
          family: "Manrope, Avenir Next, Segoe UI, sans-serif",
        },
        gridcolor: "rgba(44, 62, 80, 0.12)",
        griddash: "dash",
        zeroline: false,
      },
      showlegend: false,
    },
    config: {
      responsive: true,
      displayModeBar: false,
    },
  };
}

async function loadRoutineTotalDaysData() {
  setFeedback(feedback3El, "Carregando gráfico...");
  showState(empty3El, chart3El, { showEmpty: false, showChart: false });

  const payload = await apiFetch("/dashboard/routine-total-days-by-month");
  routineItems = Array.isArray(payload?.items) ? payload.items : [];
  buildRoutineFilterOptions(routineItems);
  await renderRoutineTotalDaysChart();
}

async function renderRoutineTotalDaysChart() {
  const filteredItems = getFilteredRoutineItems();

  if (!filteredItems.length) {
    setFeedback(feedback3El, "Sem dados para exibir no filtro atual.");
    showState(empty3El, chart3El, { showEmpty: true, showChart: false });
    return;
  }

  const { data, layout, config } = toRoutineTotalDaysChartPayload(filteredItems);
  await plotVisible(empty3El, chart3El, data, layout, config);
  setFeedback(feedback3El, `Gráfico atualizado com ${aggregateRoutineItemsByPeriod(filteredItems).length} período(s).`);
}

function rerenderRoutineTotalDaysChart() {
  renderRoutineTotalDaysChart().catch((err) => {
    const message = err?.message || "Erro ao atualizar gráfico de rotina.";
    setFeedback(feedback3El, message, "error");
    showState(empty3El, chart3El, { showEmpty: false, showChart: false });
  });
}
