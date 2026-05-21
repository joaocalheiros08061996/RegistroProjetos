requireAuth();

const responsibleFilterEl = document.getElementById("responsible-filter");
const projectYearFilterEl = document.getElementById("project-year-filter");
const projectMonthFilterEl = document.getElementById("project-month-filter");
const projectStatusFilterEl = document.getElementById("project-status-filter");
const projectsResponsibleFeedbackEl = document.getElementById("projects-responsible-feedback");
const projectsResponsibleEmptyEl = document.getElementById("projects-responsible-empty");
const projectsResponsibleTableBodyEl = document.getElementById("projects-responsible-table-body");
const refreshBtn = document.getElementById("refresh-btn");

const MONTH_OPTIONS = [
  { value: "ALL", label: "Todos" },
  { value: "1", label: "JAN" },
  { value: "2", label: "FEV" },
  { value: "3", label: "MAR" },
  { value: "4", label: "ABR" },
  { value: "5", label: "MAI" },
  { value: "6", label: "JUN" },
  { value: "7", label: "JUL" },
  { value: "8", label: "AGO" },
  { value: "9", label: "SET" },
  { value: "10", label: "OUT" },
  { value: "11", label: "NOV" },
  { value: "12", label: "DEZ" },
];

let projectsByResponsibleItems = [];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function parseProjectDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatProjectDate(value) {
  const date = parseProjectDate(value);
  if (!date) {
    return "-";
  }

  return date.toLocaleDateString("pt-BR");
}

function formatProjectCost(value) {
  if (typeof formatMoney === "function") {
    return formatMoney(value);
  }

  return Number(value || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function projectResponsibleLabel(project) {
  return String(project.responsible_login || "").trim() || "Sem responsável";
}

function projectIsCompleted(project) {
  return Number(project.percent_completed || 0) >= 100;
}

function projectMatchesPeriod(project) {
  const selectedYear = projectYearFilterEl.value;
  const selectedMonth = projectMonthFilterEl.value;
  const projectYear = Number(project.year);
  const projectMonth = Number(project.month);

  if (!Number.isFinite(projectYear) || !Number.isFinite(projectMonth)) {
    return false;
  }

  if (selectedYear !== "ALL" && projectYear !== Number(selectedYear)) {
    return false;
  }

  if (selectedMonth !== "ALL" && projectMonth !== Number(selectedMonth)) {
    return false;
  }

  return true;
}

function getFilteredProjectsByResponsible() {
  const selectedResponsible = responsibleFilterEl.value;
  const selectedStatus = projectStatusFilterEl.value;

  return projectsByResponsibleItems.filter((project) => {
    if (
      selectedResponsible !== "ALL"
      && projectResponsibleLabel(project) !== selectedResponsible
    ) {
      return false;
    }

    if (selectedStatus === "COMPLETED" && !projectIsCompleted(project)) {
      return false;
    }

    if (selectedStatus === "ONGOING" && projectIsCompleted(project)) {
      return false;
    }

    return projectMatchesPeriod(project);
  });
}

function buildProjectsByResponsibleFilters(projects) {
  const responsibles = [...new Set(projects.map(projectResponsibleLabel))]
    .sort((a, b) => a.localeCompare(b, "pt-BR"))
    .map((responsible) => ({ value: responsible, label: responsible }));

  const years = [...new Set(projects.map((project) => Number(project.year)))]
    .filter((year) => Number.isFinite(year))
    .sort((a, b) => a - b);

  setSelectOptions(
    responsibleFilterEl,
    [
      { value: "ALL", label: "Todos" },
      ...responsibles,
    ],
  );
  setSelectOptions(
    projectYearFilterEl,
    [
      { value: "ALL", label: "Todos" },
      ...years.map((year) => ({ value: year, label: String(year) })),
    ],
  );
  setSelectOptions(projectMonthFilterEl, MONTH_OPTIONS);
}

function sortProjectsByResponsible(projects) {
  return [...projects].sort((a, b) => {
    const responsibleCompare = projectResponsibleLabel(a)
      .localeCompare(projectResponsibleLabel(b), "pt-BR");
    if (responsibleCompare !== 0) {
      return responsibleCompare;
    }

    const priorityCompare = Number(a.priority_level || 5) - Number(b.priority_level || 5);
    if (priorityCompare !== 0) {
      return priorityCompare;
    }

    const startCompare = Number(a.year || 0) - Number(b.year || 0)
      || Number(a.month || 0) - Number(b.month || 0);
    if (startCompare !== 0) {
      return startCompare;
    }

    return String(a.project_name || "").localeCompare(String(b.project_name || ""), "pt-BR");
  });
}

function normalizeScore(value, fallback = 1) {
  const numericValue = Number(value);
  if (!Number.isInteger(numericValue) || numericValue < 1 || numericValue > 5) {
    return fallback;
  }
  return numericValue;
}

function renderProgressCell(project) {
  const progress = Math.max(0, Math.min(100, Number(project.percent_completed || 0)));
  return `
    <div class="table-progress">
      <span>${progress.toFixed(progress % 1 === 0 ? 0 : 1)}%</span>
      <div class="table-progress-bar" aria-hidden="true">
        <span style="width:${progress}%"></span>
      </div>
    </div>
  `;
}

function renderProjectsByResponsibleTable() {
  const filteredProjects = sortProjectsByResponsible(getFilteredProjectsByResponsible());
  projectsResponsibleTableBodyEl.innerHTML = "";

  if (!filteredProjects.length) {
    projectsResponsibleEmptyEl.classList.remove("hidden");
    projectsResponsibleFeedbackEl.textContent = "Nenhum projeto encontrado para os filtros atuais.";
    return;
  }

  projectsResponsibleEmptyEl.classList.add("hidden");
  projectsResponsibleFeedbackEl.textContent = `${filteredProjects.length} projeto(s) encontrado(s).`;

  for (const project of filteredProjects) {
    const priorityLevel = normalizeScore(project.priority_level, 5);
    const complexityScore = normalizeScore(project.complexity_score, 1);
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${escapeHtml(projectResponsibleLabel(project))}</td>
      <td>
        ${escapeHtml(project.project_name)}
      </td>
      <td>${formatProjectDate(project.planned_start)}</td>
      <td>${formatProjectDate(project.planned_end)}</td>
      <td>${renderProgressCell(project)}</td>
      <td>
        <span class="table-pill priority-pill priority-text-${priorityLevel}">
          ${escapeHtml(project.priority_label || `Prioridade ${priorityLevel}`)}
        </span>
      </td>
      <td>
        <span class="table-pill complexity-pill complexity-pill-${complexityScore}">
          ${escapeHtml(project.complexity_label || `Complexidade ${complexityScore}`)}
        </span>
      </td>
      <td>${formatProjectCost(project.estimated_cost)}</td>
    `;
    projectsResponsibleTableBodyEl.appendChild(row);
  }
}

async function loadProjectsByResponsibleDashboard() {
  projectsResponsibleFeedbackEl.textContent = "Carregando projetos...";
  projectsResponsibleFeedbackEl.className = "status";
  projectsResponsibleTableBodyEl.innerHTML = "";
  projectsResponsibleEmptyEl.classList.add("hidden");

  try {
    const payload = await apiFetch("/dashboard/projects-by-responsible");
    projectsByResponsibleItems = Array.isArray(payload?.items) ? payload.items : [];
    buildProjectsByResponsibleFilters(projectsByResponsibleItems);
    renderProjectsByResponsibleTable();
  } catch (err) {
    projectsResponsibleFeedbackEl.textContent = err.message || "Erro ao carregar projetos.";
    projectsResponsibleFeedbackEl.className = "error";
  }
}

[
  responsibleFilterEl,
  projectYearFilterEl,
  projectMonthFilterEl,
  projectStatusFilterEl,
].forEach((filterEl) => {
  filterEl.addEventListener("change", renderProjectsByResponsibleTable);
});

refreshBtn.addEventListener("click", loadProjectsByResponsibleDashboard);

loadProjectsByResponsibleDashboard();
