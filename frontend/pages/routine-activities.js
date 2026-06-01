requireAuth();

const ACTIVITY_TYPES = [
  "Atendimento de Fábrica",
  "Cadastro",
  "Atualização de Custos",
  "Finame",
  "Reuniões",
  "Reuniões sobre Processos Novos",
  "Análise de Processos",
  "Análise de Processos Novos",
];

const statusLabel = document.getElementById("status-label");
const activeBox = document.getElementById("active-box");
const activeLabel = document.getElementById("active-label");
const selectedLabel = document.getElementById("selected-label");
const activityTypesEl = document.getElementById("activity-types");
const responsavelInput = document.getElementById("responsavel");
const descricaoInput = document.getElementById("descricao");
const startBtn = document.getElementById("start-btn");
const finishBtn = document.getElementById("finish-btn");
const feedback = document.getElementById("feedback");
const RESPONSIBLE_MAX_LENGTH = 120;
const DESCRIPTION_MAX_LENGTH = 1000;

let selectedType = null;
let currentActivity = null;

function setFeedback(message, type = "status") {
  feedback.textContent = message || "";
  feedback.className = type;
}

function updateTypeButtons() {
  const buttons = activityTypesEl.querySelectorAll("button");
  buttons.forEach((button) => {
    const isSelected = button.dataset.value === selectedType;
    button.classList.toggle("active", isSelected);
    button.disabled = Boolean(currentActivity) && !isSelected;
  });
}

function setSelection(value) {
  selectedType = value;
  selectedLabel.textContent = selectedType
    ? `Selecionado: ${selectedType}`
    : "Nenhuma atividade selecionada.";
  updateTypeButtons();
  if (!currentActivity) {
    startBtn.disabled = !selectedType;
  }
}

function renderActivityTypeButtons() {
  activityTypesEl.innerHTML = "";
  ACTIVITY_TYPES.forEach((activityType) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary routine-type-btn";
    button.dataset.value = activityType;
    button.textContent = activityType;
    button.addEventListener("click", () => {
      if (currentActivity) {
        return;
      }
      setSelection(activityType);
    });
    activityTypesEl.appendChild(button);
  });
  updateTypeButtons();
}

function renderCurrentActivity(activity) {
  currentActivity = activity;

  if (currentActivity) {
    setSelection(currentActivity.tipo_atividade);
    responsavelInput.value = currentActivity.responsavel || "";
    responsavelInput.disabled = true;
    descricaoInput.value = currentActivity.descricao || "";
    descricaoInput.disabled = true;
    startBtn.disabled = true;
    finishBtn.disabled = false;
    statusLabel.textContent = `Em andamento: ${currentActivity.tipo_atividade}`;
    activeLabel.textContent = `Atividade em andamento: ${currentActivity.tipo_atividade}`;
    activeBox.classList.remove("hidden");
    return;
  }

  responsavelInput.disabled = false;
  descricaoInput.disabled = false;
  finishBtn.disabled = true;
  statusLabel.textContent = "Pronto para iniciar.";
  activeLabel.textContent = "";
  activeBox.classList.add("hidden");
  setSelection(null);
  responsavelInput.value = "";
  descricaoInput.value = "";
}

async function loadCurrentActivity() {
  try {
    const current = await apiFetch("/routine-activities/current");
    renderCurrentActivity(current);
    setFeedback("");
  } catch (err) {
    setFeedback(err.message || "Erro ao carregar atividade atual.", "error");
  }
}

startBtn.addEventListener("click", async () => {
  if (!selectedType) {
    setFeedback("Selecione um tipo de atividade.", "error");
    return;
  }

  const responsavel = responsavelInput.value.trim();
  const descricao = descricaoInput.value.trim();
  if (responsavel.length > RESPONSIBLE_MAX_LENGTH || descricao.length > DESCRIPTION_MAX_LENGTH) {
    setFeedback("Responsável ou descrição excedem o tamanho permitido.", "error");
    return;
  }

  setFeedback("Iniciando atividade...");

  try {
    const created = await apiFetch("/routine-activities/start", {
      method: "POST",
      body: JSON.stringify({
        tipo_atividade: selectedType,
        responsavel,
        descricao,
      }),
    });
    renderCurrentActivity(created);
    setFeedback("Atividade iniciada com sucesso.", "success");
  } catch (err) {
    setFeedback(err.message || "Erro ao iniciar atividade.", "error");
  }
});

finishBtn.addEventListener("click", async () => {
  setFeedback("Finalizando atividade...");

  try {
    const finished = await apiFetch("/routine-activities/finish-current", {
      method: "POST",
    });
    renderCurrentActivity(null);
    const hours = Number(finished.horas_trabalhadas || 0).toFixed(4);
    setFeedback(`Atividade finalizada. Horas trabalhadas: ${hours}.`, "success");
  } catch (err) {
    setFeedback(err.message || "Erro ao finalizar atividade.", "error");
  }
});

renderActivityTypeButtons();
loadCurrentActivity();
