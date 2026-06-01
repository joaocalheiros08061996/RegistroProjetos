function buildValueMetricFilterOptions(items, { yearEl, monthEl, typeEl, userEl }) {
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

  const types = [...new Map(
    items
      .filter((item) => item.project_type)
      .map((item) => [
        item.project_type,
        {
          value: item.project_type,
          label: item.project_type_label || item.project_type,
        },
      ])
  ).values()].sort((a, b) => a.label.localeCompare(b.label, "pt-BR"));

  const users = [...new Set(items.map((item) => item.responsible_login))]
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b, "pt-BR"))
    .map((user) => ({ value: user, label: user }));

  setSelectOptions(
    yearEl,
    [
      { value: "ALL", label: "Todos" },
      ...years.map((year) => ({ value: year, label: String(year) })),
    ]
  );
  setSelectOptions(
    monthEl,
    [
      { value: "ALL", label: "Todos" },
      ...months,
    ]
  );
  setSelectOptions(
    typeEl,
    [
      { value: "ALL", label: "Todos" },
      ...types,
    ]
  );
  setSelectOptions(
    userEl,
    [
      { value: "ALL", label: "Todos" },
      ...users,
    ]
  );
}

function buildEarnedValueFilterOptions(items) {
  buildValueMetricFilterOptions(items, {
    yearEl: earnedValueYearFilterEl,
    monthEl: earnedValueMonthFilterEl,
    typeEl: earnedValueTypeFilterEl,
    userEl: earnedValueUserFilterEl,
  });
}

function buildSchedulePerformanceFilterOptions(items) {
  buildValueMetricFilterOptions(items, {
    yearEl: schedulePerformanceYearFilterEl,
    monthEl: schedulePerformanceMonthFilterEl,
    typeEl: schedulePerformanceTypeFilterEl,
    userEl: schedulePerformanceUserFilterEl,
  });
}

function buildCostPerformanceFilterOptions(items) {
  buildValueMetricFilterOptions(items, {
    yearEl: costPerformanceYearFilterEl,
    monthEl: costPerformanceMonthFilterEl,
    typeEl: costPerformanceTypeFilterEl,
    userEl: costPerformanceUserFilterEl,
  });
}

function buildEffortDeviationFilterOptions(items) {
  buildValueMetricFilterOptions(items, {
    yearEl: effortDeviationYearFilterEl,
    monthEl: effortDeviationMonthFilterEl,
    typeEl: effortDeviationTypeFilterEl,
    userEl: effortDeviationUserFilterEl,
  });
}

function filterMetricItems(items, { yearEl, monthEl, typeEl, userEl }) {
  const selectedYear = yearEl.value;
  const selectedMonth = monthEl.value;
  const selectedType = typeEl.value;
  const selectedUser = userEl.value;

  return items.filter((item) => {
    if (selectedYear !== "ALL" && Number(item.year) !== Number(selectedYear)) {
      return false;
    }
    if (selectedMonth !== "ALL" && Number(item.month) !== Number(selectedMonth)) {
      return false;
    }
    if (selectedType !== "ALL" && item.project_type !== selectedType) {
      return false;
    }
    if (selectedUser !== "ALL" && item.responsible_login !== selectedUser) {
      return false;
    }
    return true;
  });
}

function getFilteredValueMetricItems(filters) {
  return filterMetricItems(earnedValueItems, filters);
}

function getFilteredEarnedValueItems() {
  return getFilteredValueMetricItems({
    yearEl: earnedValueYearFilterEl,
    monthEl: earnedValueMonthFilterEl,
    typeEl: earnedValueTypeFilterEl,
    userEl: earnedValueUserFilterEl,
  });
}

function getFilteredSchedulePerformanceItems() {
  return getFilteredValueMetricItems({
    yearEl: schedulePerformanceYearFilterEl,
    monthEl: schedulePerformanceMonthFilterEl,
    typeEl: schedulePerformanceTypeFilterEl,
    userEl: schedulePerformanceUserFilterEl,
  });
}

function getFilteredCostPerformanceItems() {
  return getFilteredValueMetricItems({
    yearEl: costPerformanceYearFilterEl,
    monthEl: costPerformanceMonthFilterEl,
    typeEl: costPerformanceTypeFilterEl,
    userEl: costPerformanceUserFilterEl,
  });
}

function getFilteredEffortDeviationItems() {
  return filterMetricItems(effortDeviationItems, {
    yearEl: effortDeviationYearFilterEl,
    monthEl: effortDeviationMonthFilterEl,
    typeEl: effortDeviationTypeFilterEl,
    userEl: effortDeviationUserFilterEl,
  });
}

function aggregateEarnedValueItems(items) {
  const grouped = new Map();

  for (const item of items) {
    const key = `${item.year}-${String(item.month).padStart(2, "0")}`;
    const current = grouped.get(key) || {
      year: Number(item.year),
      month: Number(item.month),
      monthLabel: item.month_label,
      periodLabel: item.period_label,
      projectCount: 0,
      taskCount: 0,
      completedTaskCount: 0,
      estimatedCost: 0,
      plannedValue: 0,
      earnedValue: 0,
      totalTaskCost: 0,
      plannedEffortHours: 0,
      actualEffortHours: 0,
      plannedLaborCost: 0,
      actualLaborCost: 0,
      actualCost: 0,
    };

    current.projectCount += 1;
    current.taskCount += Number(item.task_count || 0);
    current.completedTaskCount += Number(item.completed_task_count || 0);
    current.estimatedCost += Number(item.estimated_cost || 0);
    current.plannedValue += Number(item.planned_value || 0);
    current.earnedValue += Number(item.earned_value || 0);
    current.totalTaskCost += Number(item.total_task_cost || 0);
    current.plannedEffortHours += Number(item.planned_effort_hours || 0);
    current.actualEffortHours += Number(item.actual_effort_hours || 0);
    current.plannedLaborCost += Number(item.planned_labor_cost || 0);
    current.actualLaborCost += Number(item.actual_labor_cost || 0);
    current.actualCost += Number(item.actual_cost || item.total_task_cost || 0);
    grouped.set(key, current);
  }

  return [...grouped.values()].sort((a, b) => {
    if (a.year !== b.year) {
      return a.year - b.year;
    }
    return a.month - b.month;
  });
}

function earnedValueRange(values) {
  const maxValue = Math.max(0, ...finiteNumbers(values));
  return [0, maxValue > 0 ? maxValue * 1.24 : 1];
}
