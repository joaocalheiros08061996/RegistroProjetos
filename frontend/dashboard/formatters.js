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
