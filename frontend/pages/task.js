requireAuth();

const projectId = qs("project");
const taskName = qs("task");

if (!projectId || !taskName) {
  alert("Parâmetros da tarefa inválidos.");
  location.href = "projects.html";
}

const decodedTaskName = taskName;
const projectIdPath = encodeURIComponent(projectId);

const taskTitle = document.getElementById("task-title");
const taskSubtitle = document.getElementById("task-subtitle");
const taskDetails = document.getElementById("task-details");
const timeEntries = document.getElementById("time-entries");
const actionFeedback = document.getElementById("action-feedback");
const backLink = document.getElementById("back-link");
const refreshBtn = document.getElementById("refresh-btn");

backLink.href = `project.html?id=${projectIdPath}`;

function detailItem(label, value) {
  return `
    <article class="item">
      <p class="item-subtitle">${escapeHtml(label)}</p>
      <h3 class="item-title">${escapeHtml(value)}</h3>
    </article>
  `;
}

function renderTimeEntry(entry) {
  const item = document.createElement("article");
  item.className = "item";

  const start = formatDateTime(entry.start_time);
  const end = entry.end_time ? formatDateTime(entry.end_time) : "Em andamento";

  item.innerHTML = `
    <div class="row">
      <span class="item-subtitle">Início: ${escapeHtml(start)}</span>
      <span class="item-subtitle">Fim: ${escapeHtml(end)}</span>
    </div>
  `;

  return item;
}

async function loadTask() {
  actionFeedback.textContent = "Carregando tarefa...";
  actionFeedback.className = "status";
  taskDetails.innerHTML = "";
  timeEntries.innerHTML = "";

  try {
    const task = await apiFetch(`/projects/${projectIdPath}/tasks/${encodeURIComponent(decodedTaskName)}`);
    const entries = await apiFetch(`/projects/${projectIdPath}/tasks/${encodeURIComponent(decodedTaskName)}/time-entries`);

    taskTitle.textContent = task.name;
    taskSubtitle.textContent = `Projeto #${projectId}`;
    taskDetails.innerHTML =
      detailItem("Status", task.status) +
      detailItem("Progresso", `${task.percent_completed}%`) +
      detailItem("Início planejado", formatDateTime(task.planned_start)) +
      detailItem("Fim planejado", formatDateTime(task.planned_end)) +
      detailItem("Custo", Number(task.cost || 0).toFixed(2)) +
      detailItem("Tempo real", formatSeconds(task.actual_seconds || 0));

    if (!entries.length) {
      timeEntries.innerHTML = `<article class="item"><p class="item-subtitle">Nenhuma entrada de tempo.</p></article>`;
    } else {
      entries.forEach((entry) => timeEntries.appendChild(renderTimeEntry(entry)));
    }

    actionFeedback.textContent = "";
  } catch (err) {
    actionFeedback.textContent = err.message || "Erro ao carregar tarefa.";
    actionFeedback.className = "error";
  }
}

async function runAction(action) {
  actionFeedback.textContent = "Executando ação...";
  actionFeedback.className = "status";

  try {
    const result = await apiFetch(`/projects/${projectIdPath}/tasks/${encodeURIComponent(decodedTaskName)}/${action}`, {
      method: "POST",
    });

    if (action === "stop" && result && typeof result.duration_seconds !== "undefined") {
      actionFeedback.textContent = `Tarefa parada. Duração registrada: ${formatSeconds(result.duration_seconds)}.`;
    } else if (action === "start") {
      actionFeedback.textContent = "Tarefa iniciada.";
    } else if (action === "complete") {
      actionFeedback.textContent = "Tarefa concluída.";
    } else {
      actionFeedback.textContent = "Ação executada.";
    }

    actionFeedback.className = "success";
    await loadTask();
  } catch (err) {
    actionFeedback.textContent = err.message || "Erro ao executar ação.";
    actionFeedback.className = "error";
  }
}

document.getElementById("start-btn").addEventListener("click", () => runAction("start"));
document.getElementById("stop-btn").addEventListener("click", () => runAction("stop"));
document.getElementById("complete-btn").addEventListener("click", () => runAction("complete"));
document.getElementById("delete-btn").addEventListener("click", async () => {
  const confirmed = confirm(`Deseja excluir a tarefa "${decodedTaskName}"? Essa ação não pode ser desfeita.`);
  if (!confirmed) {
    return;
  }

  actionFeedback.textContent = "Excluindo tarefa...";
  actionFeedback.className = "status";

  try {
    await apiFetch(`/projects/${projectIdPath}/tasks/${encodeURIComponent(decodedTaskName)}`, {
      method: "DELETE",
    });
    location.href = `project.html?id=${projectIdPath}`;
  } catch (err) {
    actionFeedback.textContent = err.message || "Erro ao excluir tarefa.";
    actionFeedback.className = "error";
  }
});
refreshBtn.addEventListener("click", loadTask);

loadTask();
