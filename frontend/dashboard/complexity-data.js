function complexityColor(score) {
  const colors = {
    1: "#6A00A8",
    2: "#0077FF",
    3: "#00A676",
    4: "#FFD400",
    5: "#E6002E",
  };
  return colors[Number(score)] || "#516278";
}

function complexityTextColor(score) {
  return Number(score) === 4 ? "#112338" : "#ffffff";
}

function buildComplexityMonthlyFilterOptions(items) {
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
    complexityMonthlyYearFilterEl,
    [
      { value: "ALL", label: "Todos" },
      ...years.map((year) => ({ value: year, label: String(year) })),
    ]
  );
  setSelectOptions(
    complexityMonthlyMonthFilterEl,
    [
      { value: "ALL", label: "Todos" },
      ...months,
    ]
  );
  setSelectOptions(
    complexityMonthlyTypeFilterEl,
    [
      { value: "ALL", label: "Todos" },
      ...types,
    ]
  );
  setSelectOptions(
    complexityMonthlyUserFilterEl,
    [
      { value: "ALL", label: "Todos" },
      ...users,
    ]
  );
}

function getFilteredComplexityMonthlyItems() {
  const selectedYear = complexityMonthlyYearFilterEl.value;
  const selectedMonth = complexityMonthlyMonthFilterEl.value;
  const selectedType = complexityMonthlyTypeFilterEl.value;
  const selectedUser = complexityMonthlyUserFilterEl.value;

  return complexityMonthlyItems.filter((item) => {
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
