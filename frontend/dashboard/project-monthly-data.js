function buildProjectMonthlyFilterOptions(items) {
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
    projectMonthlyYearFilterEl,
    [
      { value: "ALL", label: "Todos" },
      ...years.map((year) => ({ value: year, label: String(year) })),
    ]
  );
  setSelectOptions(
    projectMonthlyMonthFilterEl,
    [
      { value: "ALL", label: "Todos" },
      ...months,
    ]
  );
  setSelectOptions(
    projectMonthlyTypeFilterEl,
    [
      { value: "ALL", label: "Todos" },
      ...types,
    ]
  );
  setSelectOptions(
    projectMonthlyUserFilterEl,
    [
      { value: "ALL", label: "Todos" },
      ...users,
    ]
  );
}

function getFilteredProjectMonthlyItems() {
  const selectedYear = projectMonthlyYearFilterEl.value;
  const selectedMonth = projectMonthlyMonthFilterEl.value;
  const selectedType = projectMonthlyTypeFilterEl.value;
  const selectedUser = projectMonthlyUserFilterEl.value;

  return projectMonthlyItems.filter((item) => {
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

function aggregateProjectMonthlyByTypeAndPeriod(items) {
  const grouped = new Map();

  for (const item of items) {
    const key = `${item.project_type}|${item.year}-${String(item.month).padStart(2, "0")}`;
    const existing = grouped.get(key) || {
      projectType: item.project_type,
      projectTypeLabel: item.project_type_label,
      year: Number(item.year),
      month: Number(item.month),
      monthLabel: item.month_label,
      periodLabel: item.period_label,
      projectCount: 0,
      plannedDaysSum: 0,
      plannedDaysCount: 0,
      realDaysSum: 0,
      realDaysCount: 0,
      slaBreachCount: 0,
      slaProjectCount: 0,
    };

    existing.projectCount += Number(item.project_count || 0);
    existing.plannedDaysSum += Number(item.planned_days_sum || 0);
    existing.plannedDaysCount += Number(item.planned_days_count || 0);
    existing.realDaysSum += Number(item.real_days_sum || 0);
    existing.realDaysCount += Number(item.real_days_count || 0);
    existing.slaBreachCount += Number(item.sla_breach_count || 0);
    existing.slaProjectCount += Number(item.sla_project_count || 0);
    grouped.set(key, existing);
  }

  return [...grouped.values()]
    .map((item) => {
      const realAverageDays = item.realDaysCount > 0
        ? item.realDaysSum / item.realDaysCount
        : null;
      const plannedAverageDays = item.plannedDaysCount > 0
        ? item.plannedDaysSum / item.plannedDaysCount
        : null;
      const delayAverageDays = realAverageDays !== null && plannedAverageDays !== null
        ? realAverageDays - plannedAverageDays
        : null;
      const efficiency = realAverageDays && plannedAverageDays !== null
        ? plannedAverageDays / realAverageDays
        : null;

      return {
        ...item,
        realAverageDays,
        plannedAverageDays,
        delayAverageDays,
        efficiency,
      };
    })
    .sort((a, b) => {
      if (a.year !== b.year) {
        return a.year - b.year;
      }
      if (a.month !== b.month) {
        return a.month - b.month;
      }
      return a.projectTypeLabel.localeCompare(b.projectTypeLabel, "pt-BR");
    });
}

function aggregateProjectMonthlyByPeriod(items) {
  const grouped = new Map();

  for (const item of items) {
    const key = `${item.year}-${String(item.month).padStart(2, "0")}`;
    const existing = grouped.get(key) || {
      year: Number(item.year),
      month: Number(item.month),
      monthLabel: item.month_label,
      periodLabel: item.period_label,
      plannedDaysSum: 0,
      plannedDaysCount: 0,
      realDaysSum: 0,
      realDaysCount: 0,
      slaBreachCount: 0,
      slaProjectCount: 0,
    };

    existing.plannedDaysSum += Number(item.planned_days_sum || 0);
    existing.plannedDaysCount += Number(item.planned_days_count || 0);
    existing.realDaysSum += Number(item.real_days_sum || 0);
    existing.realDaysCount += Number(item.real_days_count || 0);
    existing.slaBreachCount += Number(item.sla_breach_count || 0);
    existing.slaProjectCount += Number(item.sla_project_count || 0);
    grouped.set(key, existing);
  }

  return [...grouped.values()]
    .map((item) => {
      const realAverageDays = item.realDaysCount > 0
        ? item.realDaysSum / item.realDaysCount
        : null;
      const plannedAverageDays = item.plannedDaysCount > 0
        ? item.plannedDaysSum / item.plannedDaysCount
        : null;
      const delayAverageDays = realAverageDays !== null && plannedAverageDays !== null
        ? realAverageDays - plannedAverageDays
        : null;
      const efficiency = realAverageDays && plannedAverageDays !== null
        ? (plannedAverageDays / realAverageDays) * 100
        : null;
      const slaRate = item.slaProjectCount > 0
        ? (item.slaBreachCount / item.slaProjectCount) * 100
        : null;

      return {
        ...item,
        realAverageDays,
        plannedAverageDays,
        delayAverageDays,
        efficiency,
        slaRate,
      };
    })
    .sort((a, b) => {
      if (a.year !== b.year) {
        return a.year - b.year;
      }
      return a.month - b.month;
    });
}

function getProjectMonthlyPeriods(items) {
  return [...new Map(
    items.map((item) => [
      `${item.year}-${String(item.month).padStart(2, "0")}`,
      {
        year: item.year,
        month: item.month,
        label: item.periodLabel,
      },
    ])
  ).values()].sort((a, b) => {
    if (a.year !== b.year) {
      return a.year - b.year;
    }
    return a.month - b.month;
  });
}

function getProjectMonthlyTypes(items) {
  return [...new Map(
    items.map((item) => [
      item.projectType,
      {
        type: item.projectType,
        label: item.projectTypeLabel,
      },
    ])
  ).values()].sort((a, b) => a.label.localeCompare(b.label, "pt-BR"));
}

function buildProjectMonthlySeries(items, metricKey, hoverLabel, decimals = 2) {
  const periods = getProjectMonthlyPeriods(items);
  const types = getProjectMonthlyTypes(items);

  return types.map((type) => {
    const values = periods.map((period) => {
      const item = items.find(
        (candidate) =>
          candidate.projectType === type.type &&
          candidate.year === period.year &&
          candidate.month === period.month
      );
      const value = item ? item[metricKey] : null;
      return Number.isFinite(value) ? value : null;
    });

    return {
      type: metricKey === "realAverageDays" ? "bar" : "scatter",
      mode: metricKey === "realAverageDays" ? undefined : "lines+markers",
      name: type.label,
      x: periods.map((period) => period.label),
      y: values,
      connectgaps: false,
      hovertemplate: `%{x}<br>${hoverLabel}: %{y:.${decimals}f}<extra>%{fullData.name}</extra>`,
    };
  });
}

function getGraphOneRealAverageForSelectedTypes() {
  const selectedType = projectMonthlyTypeFilterEl.value;
  const selectedAvgItems = selectedType === "ALL"
    ? avgRealItems
    : avgRealItems.filter((item) => item.project_type === selectedType);

  if (!selectedAvgItems.length) {
    return null;
  }

  const total = selectedAvgItems.reduce(
    (acc, item) => acc + Number(item.average_days || 0),
    0
  );
  return total / selectedAvgItems.length;
}

function getOverallDelayAverage(items) {
  const totalRealDays = items.reduce(
    (acc, item) => acc + Number(item.real_days_sum || 0),
    0
  );
  const totalRealCount = items.reduce(
    (acc, item) => acc + Number(item.real_days_count || 0),
    0
  );
  const totalPlannedDays = items.reduce(
    (acc, item) => acc + Number(item.planned_days_sum || 0),
    0
  );
  const totalPlannedCount = items.reduce(
    (acc, item) => acc + Number(item.planned_days_count || 0),
    0
  );

  if (totalRealCount <= 0 || totalPlannedCount <= 0) {
    return null;
  }

  return (totalRealDays / totalRealCount) - (totalPlannedDays / totalPlannedCount);
}
