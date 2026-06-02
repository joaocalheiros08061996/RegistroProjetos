function formatDaysLabel(value) {
  const numericValue = Number(value || 0);
  if (!Number.isFinite(numericValue)) {
    return "0.0 dias";
  }
  return `${numericValue.toFixed(1)} dias`;
}

function formatShortDays(value) {
  const numericValue = Number(value || 0);
  if (!Number.isFinite(numericValue)) {
    return "0.00";
  }
  return numericValue.toFixed(2);
}

function finiteNumbers(values) {
  return values
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value));
}

function getDaysPrecision(values) {
  const maxValue = Math.max(0, ...finiteNumbers(values).map((value) => Math.abs(value)));
  if (maxValue > 0 && maxValue < 0.01) {
    return 4;
  }
  if (maxValue > 0 && maxValue < 0.1) {
    return 3;
  }
  if (maxValue < 10) {
    return 2;
  }
  return 1;
}

const DASHBOARD_TIME_UNIT_STORAGE_KEY = "registroProjetos.dashboardTimeUnit";
const DASHBOARD_DAY_HOURS = 24;
const DASHBOARD_WORKDAY_HOURS = 8.8;

function normalizeDashboardTimeUnit(value) {
  return value === "hours" ? "hours" : "days";
}

function readDashboardTimeUnitPreference() {
  try {
    return window.localStorage.getItem(DASHBOARD_TIME_UNIT_STORAGE_KEY);
  } catch {
    return null;
  }
}

function saveDashboardTimeUnitPreference(value) {
  try {
    window.localStorage.setItem(
      DASHBOARD_TIME_UNIT_STORAGE_KEY,
      normalizeDashboardTimeUnit(value)
    );
  } catch {
    // A preferencia do usuario e opcional; o dashboard continua funcional sem localStorage.
  }
}

function getDashboardTimeUnit() {
  const selectEl = typeof dashboardTimeUnitFilterEl !== "undefined"
    ? dashboardTimeUnitFilterEl
    : null;

  return normalizeDashboardTimeUnit(
    selectEl?.value || readDashboardTimeUnitPreference()
  );
}

function setupDashboardTimeUnitFilter(onChange) {
  const selectEl = typeof dashboardTimeUnitFilterEl !== "undefined"
    ? dashboardTimeUnitFilterEl
    : null;

  if (!selectEl) {
    return;
  }

  selectEl.value = normalizeDashboardTimeUnit(
    readDashboardTimeUnitPreference() || selectEl.value
  );

  selectEl.addEventListener("change", () => {
    selectEl.value = normalizeDashboardTimeUnit(selectEl.value);
    saveDashboardTimeUnitPreference(selectEl.value);
    onChange?.();
  });
}

function getDashboardTimeUnitLabel(unit = getDashboardTimeUnit()) {
  return normalizeDashboardTimeUnit(unit) === "hours" ? "horas" : "dias";
}

function getDashboardTimeUnitTitle(unit = getDashboardTimeUnit()) {
  return normalizeDashboardTimeUnit(unit) === "hours" ? "Horas" : "Dias";
}

function convertDaysToDashboardUnit(
  value,
  unit = getDashboardTimeUnit(),
  hoursPerDay = DASHBOARD_DAY_HOURS
) {
  const numericValue = Number(value || 0);
  if (!Number.isFinite(numericValue)) {
    return 0;
  }

  return normalizeDashboardTimeUnit(unit) === "hours"
    ? numericValue * hoursPerDay
    : numericValue;
}

function convertHoursToDashboardUnit(
  value,
  unit = getDashboardTimeUnit(),
  hoursPerDay = DASHBOARD_DAY_HOURS
) {
  const numericValue = Number(value || 0);
  if (!Number.isFinite(numericValue)) {
    return 0;
  }

  return normalizeDashboardTimeUnit(unit) === "days"
    ? numericValue / hoursPerDay
    : numericValue;
}

function formatDashboardDurationLabelFromDays(
  value,
  unit = getDashboardTimeUnit(),
  hoursPerDay = DASHBOARD_DAY_HOURS
) {
  const convertedValue = convertDaysToDashboardUnit(value, unit, hoursPerDay);
  return `${convertedValue.toFixed(1)} ${getDashboardTimeUnitLabel(unit)}`;
}

function formatDashboardDurationValue(value, unit = getDashboardTimeUnit()) {
  const numericValue = Number(value || 0);
  const normalizedUnit = normalizeDashboardTimeUnit(unit);
  if (!Number.isFinite(numericValue)) {
    return normalizedUnit === "hours" ? "0 h" : "0 dias";
  }

  const absValue = Math.abs(numericValue);
  const suffix = normalizedUnit === "hours" ? "h" : "dias";
  if (absValue >= 100) {
    return `${numericValue.toFixed(0)} ${suffix}`;
  }
  if (absValue >= 10) {
    return `${numericValue.toFixed(1)} ${suffix}`;
  }
  return `${numericValue.toFixed(2)} ${suffix}`;
}

function formatSignedDashboardDurationValue(value, unit = getDashboardTimeUnit()) {
  const numericValue = Number(value || 0);
  if (!Number.isFinite(numericValue) || numericValue === 0) {
    return formatDashboardDurationValue(0, unit);
  }
  return `${numericValue > 0 ? "+" : ""}${formatDashboardDurationValue(numericValue, unit)}`;
}

function formatAdaptiveDays(value, values) {
  const numericValue = Number(value || 0);
  if (!Number.isFinite(numericValue)) {
    return "0";
  }
  return numericValue.toFixed(getDaysPrecision(values));
}

function formatRoutineDays(value) {
  const numericValue = Number(value || 0);
  if (!Number.isFinite(numericValue)) {
    return "0";
  }
  if (Math.abs(numericValue) >= 100) {
    return numericValue.toFixed(0);
  }
  if (Math.abs(numericValue) >= 10) {
    return numericValue.toFixed(1);
  }
  return numericValue.toFixed(2);
}

function setSelectOptions(selectEl, options, selectedValue = "ALL") {
  const currentValue = selectEl.value || selectedValue;
  selectEl.innerHTML = "";

  for (const option of options) {
    const optionEl = document.createElement("option");
    optionEl.value = String(option.value);
    optionEl.textContent = option.label;
    selectEl.appendChild(optionEl);
  }

  const values = options.map((option) => String(option.value));
  selectEl.value = values.includes(currentValue) ? currentValue : selectedValue;
}

function formatPercent(value) {
  const numericValue = Number(value || 0);
  if (!Number.isFinite(numericValue)) {
    return "0.0%";
  }
  return `${numericValue.toFixed(1)}%`;
}

function formatIdp(value) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return "-";
  }
  return numericValue.toFixed(2);
}

function formatMoney(value) {
  const numericValue = Number(value || 0);
  if (!Number.isFinite(numericValue)) {
    return "R$ 0";
  }

  return numericValue.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: Math.abs(numericValue) >= 1000 ? 0 : 2,
  });
}

function formatCompactMoney(value) {
  const numericValue = Number(value || 0);
  if (!Number.isFinite(numericValue)) {
    return "R$ 0";
  }

  const absValue = Math.abs(numericValue);
  if (absValue >= 1000000) {
    return `R$ ${(numericValue / 1000000).toLocaleString("pt-BR", {
      maximumFractionDigits: 1,
    })} mi`;
  }
  if (absValue >= 1000) {
    return `R$ ${(numericValue / 1000).toLocaleString("pt-BR", {
      maximumFractionDigits: 1,
    })} mil`;
  }
  return formatMoney(numericValue);
}

function formatSignedDays(value) {
  const numericValue = Number(value || 0);
  if (!Number.isFinite(numericValue)) {
    return "0.00";
  }
  return numericValue.toFixed(2);
}

function formatHours(value) {
  const numericValue = Number(value || 0);
  if (!Number.isFinite(numericValue)) {
    return "0 h";
  }
  const absValue = Math.abs(numericValue);
  if (absValue >= 100) {
    return `${numericValue.toFixed(0)} h`;
  }
  if (absValue >= 10) {
    return `${numericValue.toFixed(1)} h`;
  }
  return `${numericValue.toFixed(2)} h`;
}

function formatSignedHours(value) {
  const numericValue = Number(value || 0);
  if (!Number.isFinite(numericValue) || numericValue === 0) {
    return "0 h";
  }
  return `${numericValue > 0 ? "+" : ""}${formatHours(numericValue)}`;
}
