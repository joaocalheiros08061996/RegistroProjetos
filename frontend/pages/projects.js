requireAuth();

const projectList = document.getElementById("project-list");
const listFeedback = document.getElementById("list-feedback");
const formFeedback = document.getElementById("form-feedback");
const projectForm = document.getElementById("project-form");
const refreshBtn = document.getElementById("refresh-btn");

const plannedStartInput = document.getElementById("planned_start");
const plannedEndInput = document.getElementById("planned_end");
const fteInput = document.getElementById("fte");
const PROJECT_NAME_MAX_LENGTH = 160;
const PROJECT_DESCRIPTION_MAX_LENGTH = 150;
const RESPONSIBLE_MAX_LENGTH = 120;
const MAX_FTE = 100;
const MAX_MONEY_VALUE = 1000000000;

const now = new Date();
const plus7 = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
plannedStartInput.value = toLocalInputValue(now);
plannedEndInput.value = toLocalInputValue(plus7);

const PROJECT_TYPE_LABELS = {
  LAYOUT: "LAYOUT",
  EXPORTACAO: "EXPORTAÇÃO",
  NORMATIZACAO: "NORMATIZAÇÃO",
  PADRONIZACAO: "PADRONIZAÇÃO",
  TRY_OUT: "TRY OUT",
  MAPEAMENTO: "MAPEAMENTO",
  MELHORIA: "MELHORIA DE PROC. EXISTENTES",
  MELHORIA_PROC_NOVOS: "MELHORIA DE PROC. NOVOS",
  PECAS: "PEÇAS",
};

function formatProjectTypeSafe(projectType) {
  if (typeof formatProjectType === "function") {
    return formatProjectType(projectType);
  }
  if (PROJECT_TYPE_LABELS[projectType]) {
    return PROJECT_TYPE_LABELS[projectType];
  }
  return String(projectType || "").split("_").join(" ").toUpperCase();
}

function formatProcessClassification(value) {
  return value || "Não informado";
}

fteInput.addEventListener("beforeinput", (event) => {
  if (event.data && !/^\d+$/.test(event.data)) {
    event.preventDefault();
  }
});

function getProjectPriority(project) {
  const level = Number(project.priority_level || 5);
  const normalizedLevel = Number.isInteger(level) && level >= 1 && level <= 5
    ? level
    : 5;

  return {
    level: normalizedLevel,
    label: project.priority_label || `Prioridade ${normalizedLevel}`,
    gutScore: Number(project.gut_score || 0),
  };
}

function renderProjectItem(project) {
  const card = document.createElement("article");
  card.className = "item";

  const period = `${formatDateTime(project.planned_start)} - ${formatDateTime(project.planned_end)}`;
  const progress = `${project.percent_completed ?? 0}%`;
  const priority = getProjectPriority(project);
  const processClassification = formatProcessClassification(project.process_classification);
  const projectIdParam = encodeURIComponent(project.id);
  const descriptionHtml = project.description
    ? `<p class="item-subtitle task-description">${escapeHtml(project.description)}</p>`
    : "";

  card.innerHTML = `
    <div class="row project-heading">
      <div class="project-title-stack">
        <div class="project-title-with-priority">
          <span class="priority-dot priority-${priority.level}" aria-label="${escapeHtml(priority.label)}"></span>
          <h3 class="item-title">${escapeHtml(project.name)}</h3>
        </div>
        <p class="project-priority-label priority-text-${priority.level}">
          ${escapeHtml(priority.label)}
        </p>
      </div>
      <span class="item-subtitle">${escapeHtml(formatProjectTypeSafe(project.project_type))}</span>
    </div>
    ${descriptionHtml}
    <p class="item-subtitle">Responsável: ${escapeHtml(project.responsible_login)}</p>
    ${project.process_classification ? `<p class="item-subtitle">Processo: ${escapeHtml(processClassification)}</p>` : ""}
    <p class="item-subtitle">Período: ${escapeHtml(period)}</p>
    <div class="row">
      <span class="item-subtitle">Tarefas: ${escapeHtml(project.task_count)}</span>
      <span class="item-subtitle">Progresso: ${escapeHtml(progress)}</span>
    </div>
    <div class="actions" style="margin-top:10px;">
      <a class="button secondary" href="project.html?id=${projectIdParam}">Abrir projeto</a>
      <button type="button" class="danger delete-project-btn">Excluir projeto</button>
    </div>
  `;

  const deleteButton = card.querySelector(".delete-project-btn");
  deleteButton.addEventListener("click", async () => {
    const confirmed = confirm(`Deseja excluir o projeto "${project.name}"? Essa ação não pode ser desfeita.`);
    if (!confirmed) {
      return;
    }

    listFeedback.textContent = "Excluindo projeto...";
    listFeedback.className = "status";

    try {
      await apiFetch(`/projects/${projectIdParam}`, { method: "DELETE" });
      await loadProjects();
    } catch (err) {
      listFeedback.textContent = err.message || "Erro ao excluir projeto.";
      listFeedback.className = "error";
    }
  });

  return card;
}

async function loadProjects() {
  listFeedback.textContent = "Carregando projetos...";
  listFeedback.className = "status";
  projectList.innerHTML = "";

  try {
    const projects = await apiFetch("/projects/");

    if (!projects.length) {
      listFeedback.textContent = "Nenhum projeto cadastrado.";
      return;
    }

    listFeedback.textContent = `${projects.length} projeto(s) encontrado(s).`;
    projects.forEach((project) => {
      projectList.appendChild(renderProjectItem(project));
    });
  } catch (err) {
    listFeedback.textContent = err.message || "Erro ao carregar projetos.";
    listFeedback.className = "error";
  }
}

projectForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  formFeedback.textContent = "";
  formFeedback.className = "status";

  const payload = {
    name: document.getElementById("name").value.trim(),
    description: document.getElementById("description").value.trim(),
    project_type: document.getElementById("project_type").value,
    process_classification: document.getElementById("process_classification").value || null,
    responsible_login: document.getElementById("responsible_login").value.trim(),
    fte: Number(fteInput.value),
    planned_start: normalizeIsoFromInput(plannedStartInput.value),
    planned_end: normalizeIsoFromInput(plannedEndInput.value),
    severity: document.getElementById("severity").value,
    urgency: document.getElementById("urgency").value,
    trend: document.getElementById("trend").value,
    objective_clarity: document.getElementById("objective_clarity").value,
    method_clarity: document.getElementById("method_clarity").value,
    estimated_cost: Number(document.getElementById("estimated_cost").value || 0),
  };

  if (!payload.name || !payload.responsible_login) {
    formFeedback.textContent = "Preencha nome e responsável.";
    formFeedback.className = "error";
    return;
  }

  if (payload.name.length > PROJECT_NAME_MAX_LENGTH || payload.responsible_login.length > RESPONSIBLE_MAX_LENGTH) {
    formFeedback.textContent = "Nome ou responsável excedem o tamanho permitido.";
    formFeedback.className = "error";
    return;
  }

  if (payload.description.length > PROJECT_DESCRIPTION_MAX_LENGTH) {
    formFeedback.textContent = "A descrição do projeto excede o tamanho permitido.";
    formFeedback.className = "error";
    return;
  }

  if (!Number.isInteger(payload.fte) || payload.fte < 1 || payload.fte > MAX_FTE) {
    formFeedback.textContent = "Informe um FTE inteiro entre 1 e 100.";
    formFeedback.className = "error";
    return;
  }

  if (
    !Number.isFinite(payload.estimated_cost)
    || payload.estimated_cost < 0
    || payload.estimated_cost > MAX_MONEY_VALUE
  ) {
    formFeedback.textContent = "Informe um custo estimado válido e não negativo.";
    formFeedback.className = "error";
    return;
  }

  if (!payload.planned_start || !payload.planned_end) {
    formFeedback.textContent = "Informe início e fim planejados.";
    formFeedback.className = "error";
    return;
  }

  try {
    await apiFetch("/projects/", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    formFeedback.textContent = "Projeto criado com sucesso.";
    formFeedback.className = "success";
    projectForm.reset();
    document.getElementById("fte").value = "1";
    document.getElementById("estimated_cost").value = "0";
    plannedStartInput.value = toLocalInputValue(new Date());
    plannedEndInput.value = toLocalInputValue(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000));
    await loadProjects();
  } catch (err) {
    formFeedback.textContent = err.message || "Erro ao criar projeto.";
    formFeedback.className = "error";
  }
});

refreshBtn.addEventListener("click", loadProjects);
loadProjects();
