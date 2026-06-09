requireAuth();

const projectId = qs("id");
if (!projectId) {
  alert("Projeto não informado.");
  location.href = "projects.html";
}
const projectIdPath = encodeURIComponent(projectId);

const projectTitle = document.getElementById("project-title");
const projectSubtitle = document.getElementById("project-subtitle");
const projectMetrics = document.getElementById("project-metrics");
const projectFeedback = document.getElementById("project-feedback");
const taskList = document.getElementById("task-list");
const taskForm = document.getElementById("task-form");
const taskFormFeedback = document.getElementById("task-form-feedback");
const refreshBtn = document.getElementById("refresh-btn");
const deleteProjectBtn = document.getElementById("delete-project-btn");
const TASK_NAME_MAX_LENGTH = 160;
const TASK_DESCRIPTION_MAX_LENGTH = 150;
const MAX_MONEY_VALUE = 1000000000;

const taskStartInput = document.getElementById("task_planned_start");
const taskEndInput = document.getElementById("task_planned_end");
const taskStartDefault = new Date();
const taskEndDefault = new Date(Date.now() + 2 * 24 * 60 * 60 * 1000);
taskStartInput.value = toLocalInputValue(taskStartDefault);
taskEndInput.value = toLocalInputValue(taskEndDefault);

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

function metricItem(label, value) {
  return `
    <article class="item">
      <p class="item-subtitle">${escapeHtml(label)}</p>
      <h3 class="item-title">${escapeHtml(value)}</h3>
    </article>
  `;
}

function renderTaskItem(task) {
  const card = document.createElement("article");
  card.className = "item";
  const encodedTask = encodeURIComponent(task.name);
  const descriptionHtml = task.description
    ? `<p class="item-subtitle task-description">${escapeHtml(task.description)}</p>`
    : "";
  card.innerHTML = `
    <div class="row">
      <h3 class="item-title">${escapeHtml(task.name)}</h3>
      <span class="item-subtitle">${escapeHtml(task.status)}</span>
    </div>
    ${descriptionHtml}
    <p class="item-subtitle">Período: ${escapeHtml(formatDateTime(task.planned_start))} - ${escapeHtml(formatDateTime(task.planned_end))}</p>
    <p class="item-subtitle">Custo: ${escapeHtml(Number(task.cost || 0).toFixed(2))}</p>
    <div class="row">
      <span class="item-subtitle">Tempo real: ${escapeHtml(formatSeconds(task.actual_seconds))}</span>
      <span class="item-subtitle">Progresso: ${escapeHtml(task.percent_completed)}%</span>
    </div>
    <div class="actions" style="margin-top:10px;">
      <a class="button secondary" href="task.html?project=${projectIdPath}&task=${encodedTask}">Abrir tarefa</a>
      <button type="button" class="danger delete-task-btn">Excluir tarefa</button>
    </div>
  `;

  const deleteTaskBtn = card.querySelector(".delete-task-btn");
  deleteTaskBtn.addEventListener("click", async () => {
    const confirmed = confirm(`Deseja excluir a tarefa "${task.name}"? Essa ação não pode ser desfeita.`);
    if (!confirmed) {
      return;
    }

    projectFeedback.textContent = "Excluindo tarefa...";
    projectFeedback.className = "status";

    try {
      await apiFetch(`/projects/${projectIdPath}/tasks/${encodedTask}`, {
        method: "DELETE",
      });
      await loadProjectDetail();
    } catch (err) {
      projectFeedback.textContent = err.message || "Erro ao excluir tarefa.";
      projectFeedback.className = "error";
    }
  });

  return card;
}

async function loadProjectDetail() {
  projectFeedback.textContent = "Carregando projeto...";
  projectFeedback.className = "status";
  projectMetrics.innerHTML = "";
  taskList.innerHTML = "";

  try {
    const detail = await apiFetch(`/projects/${projectIdPath}/detail`);

    projectTitle.textContent = detail.name;
    projectSubtitle.textContent = `Responsável: ${detail.responsible_login} | Tipo: ${formatProjectTypeSafe(detail.project_type)} | Processo: ${formatProcessClassification(detail.process_classification)}`;

    projectMetrics.innerHTML =
      metricItem("Descrição", detail.description || "Sem descrição") +
      metricItem("Progresso", `${detail.percent_completed}%`) +
      metricItem("Tarefas", String(detail.task_count)) +
      metricItem("Processo", formatProcessClassification(detail.process_classification)) +
      metricItem("Dias reais", Number(detail.actual_days || 0).toFixed(2)) +
      metricItem("Custo estimado", Number(detail.estimated_cost || 0).toFixed(2)) +
      metricItem("Início", formatDateTime(detail.planned_start)) +
      metricItem("Fim", formatDateTime(detail.planned_end));

    if (!detail.tasks.length) {
      taskList.innerHTML = `<article class="item"><p class="item-subtitle">Nenhuma tarefa cadastrada.</p></article>`;
    } else {
      detail.tasks.forEach((task) => {
        taskList.appendChild(renderTaskItem(task));
      });
    }

    projectFeedback.textContent = "";
  } catch (err) {
    projectFeedback.textContent = err.message || "Erro ao carregar projeto.";
    projectFeedback.className = "error";
  }
}

taskForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  taskFormFeedback.textContent = "";
  taskFormFeedback.className = "status";

  const payload = {
    name: document.getElementById("task_name").value.trim(),
    description: document.getElementById("task_description").value.trim(),
    planned_start: normalizeIsoFromInput(taskStartInput.value),
    planned_end: normalizeIsoFromInput(taskEndInput.value),
    cost: Number(document.getElementById("task_cost").value || 0),
  };

  if (!payload.name) {
    taskFormFeedback.textContent = "Informe o nome da tarefa.";
    taskFormFeedback.className = "error";
    return;
  }

  if (payload.name.length > TASK_NAME_MAX_LENGTH) {
    taskFormFeedback.textContent = "O nome da tarefa excede o tamanho permitido.";
    taskFormFeedback.className = "error";
    return;
  }

  if (payload.description.length > TASK_DESCRIPTION_MAX_LENGTH) {
    taskFormFeedback.textContent = "A descrição da tarefa excede o tamanho permitido.";
    taskFormFeedback.className = "error";
    return;
  }

  if (!Number.isFinite(payload.cost) || payload.cost < 0 || payload.cost > MAX_MONEY_VALUE) {
    taskFormFeedback.textContent = "Informe um custo válido e não negativo.";
    taskFormFeedback.className = "error";
    return;
  }

  if (!payload.planned_start || !payload.planned_end) {
    taskFormFeedback.textContent = "Informe datas de início e fim.";
    taskFormFeedback.className = "error";
    return;
  }

  try {
    await apiFetch(`/projects/${projectIdPath}/tasks/`, {
      method: "POST",
      body: JSON.stringify(payload),
    });

    taskFormFeedback.textContent = "Tarefa criada com sucesso.";
    taskFormFeedback.className = "success";
    taskForm.reset();
    document.getElementById("task_cost").value = "0";
    taskStartInput.value = toLocalInputValue(new Date());
    taskEndInput.value = toLocalInputValue(new Date(Date.now() + 2 * 24 * 60 * 60 * 1000));
    await loadProjectDetail();
  } catch (err) {
    taskFormFeedback.textContent = err.message || "Erro ao criar tarefa.";
    taskFormFeedback.className = "error";
  }
});

refreshBtn.addEventListener("click", loadProjectDetail);
deleteProjectBtn.addEventListener("click", async () => {
  const confirmed = confirm("Deseja excluir este projeto? Todas as tarefas e entradas de tempo serão removidas.");
  if (!confirmed) {
    return;
  }

  projectFeedback.textContent = "Excluindo projeto...";
  projectFeedback.className = "status";

  try {
    await apiFetch(`/projects/${projectIdPath}`, { method: "DELETE" });
    location.href = "projects.html";
  } catch (err) {
    projectFeedback.textContent = err.message || "Erro ao excluir projeto.";
    projectFeedback.className = "error";
  }
});
loadProjectDetail();
