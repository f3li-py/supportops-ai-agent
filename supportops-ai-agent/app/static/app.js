// SupportOps AI Agent Frontend Controller

// Suporta tanto acesso via servidor web (http://127.0.0.1:8000) quanto se o usuário abrir o arquivo index.html direto
const API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "";

const SCENARIOS = {
  quota: {
    userId: "USR-103",
    message: "Minhas requisições de API começaram a falhar repentinamente com o erro HTTP 429 Too Many Requests. Poderiam verificar se há algum bloqueio na minha conta?",
  },
  past_due: {
    userId: "USR-102",
    message: "Recebi um aviso de que minha conta está com serviços pausados por problema no pagamento do cartão de crédito. Como resolvo isso?",
  },
  critical_sla: {
    userId: "USR-101",
    message: "URGENTE: Nosso cluster de produção parou de se comunicar com o gateway da plataforma. Nosso checkout está fora do ar com prejuízo imediato a clientes!",
  },
  mfa: {
    userId: "USR-103",
    message: "Gostaria de saber qual é o procedimento oficial para ativar autenticação em dois fatores (MFA/2FA) na minha conta.",
  },
};

function setScenario(key) {
  const sc = SCENARIOS[key];
  if (!sc) return;
  document.getElementById("userIdInput").value = sc.userId;
  document.getElementById("messageInput").value = sc.message;
}

async function loadUsers() {
  const grid = document.getElementById("usersGrid");
  try {
    const res = await fetch(`${API_BASE}/api/v1/users`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const users = await res.json();

    grid.innerHTML = users.map(u => {
      const planBadge = u.plan === "Enterprise" ? "bg-purple-500/20 text-purple-300 border-purple-500/30" :
                        u.plan === "Pro" ? "bg-blue-500/20 text-blue-300 border-blue-500/30" :
                        "bg-slate-700 text-slate-300 border-slate-600";

      const statusBadge = u.status === "active" ? "text-emerald-400" : "text-amber-400";

      return `
        <div onclick="selectUser('${u.user_id}')" class="cursor-pointer p-4 rounded-xl bg-slate-900 hover:bg-slate-800/80 border border-slate-800 hover:border-indigo-500/50 transition shadow-sm space-y-2">
          <div class="flex items-center justify-between">
            <span class="font-mono text-xs font-bold text-indigo-400">${u.user_id}</span>
            <span class="text-[11px] px-2 py-0.5 rounded-full border ${planBadge}">${u.plan}</span>
          </div>
          <div>
            <h4 class="text-sm font-semibold text-white">${u.name}</h4>
            <p class="text-xs text-slate-400">${u.email}</p>
          </div>
          <div class="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-400">
            <span>Status: <span class="${statusBadge} font-medium">${u.status}</span></span>
            <span>Uso: ${u.api_calls_this_month.toLocaleString()} / ${u.api_limit.toLocaleString()}</span>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    grid.innerHTML = `
      <div class="col-span-full p-4 rounded-xl bg-amber-950/40 border border-amber-500/40 text-amber-200 text-xs space-y-2">
        <p class="font-bold text-amber-300 flex items-center gap-1.5">
          <span>⚠️</span> Não foi possível conectar ao backend (${err.message})
        </p>
        <p class="text-slate-300">
          O servidor FastAPI pode ter sido fechado ou você abriu o arquivo direto.
        </p>
        <p class="text-slate-400 font-mono text-[11px]">
          1. Dê dois cliques em <b>iniciar.bat</b> na pasta do projeto.<br>
          2. Acesse no navegador: <a href="http://127.0.0.1:8000" class="text-indigo-400 underline font-semibold">http://127.0.0.1:8000</a>
        </p>
      </div>
    `;
  }
}

function selectUser(userId) {
  document.getElementById("userIdInput").value = userId;
}

async function processTicket() {
  const userId = document.getElementById("userIdInput").value.trim();
  const message = document.getElementById("messageInput").value.trim();

  if (!userId || !message) {
    alert("Por favor, preencha o ID do usuário e a mensagem.");
    return;
  }

  const submitBtn = document.getElementById("submitBtn");
  const btnSpinner = document.getElementById("btnSpinner");
  const btnText = document.getElementById("btnText");
  const terminal = document.getElementById("toolsTerminal");
  const triageCard = document.getElementById("triageCard");
  const execBadge = document.getElementById("executionTimeBadge");

  submitBtn.disabled = true;
  btnSpinner.classList.remove("hidden");
  btnText.innerText = "Investigando com o Modelo Gemini...";

  terminal.innerHTML = `
    <div class="flex items-center gap-2 text-indigo-400 animate-pulse py-2">
      <span class="animate-spin">⚙️</span>
      <span>O agente iniciou a investigação técnica (loop de ferramentas)...</span>
    </div>
  `;

  try {
    const res = await fetch(`${API_BASE}/api/v1/tickets/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, message: message }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Falha ao processar o ticket.");
    }

    const data = await res.json();
    renderToolLogs(data.tool_calls);
    renderTriageDecision(data);
    execBadge.innerText = `Tempo de Execução: ${data.execution_time_seconds}s`;
    loadTickets();
  } catch (err) {
    terminal.innerHTML = `
      <div class="p-3 rounded-lg bg-rose-950/40 border border-rose-500/30 text-rose-300">
        ❌ <b>Erro na execução do agente:</b> ${err.message}
      </div>
    `;
  } finally {
    submitBtn.disabled = false;
    btnSpinner.classList.add("hidden");
    btnText.innerText = "Processar com Agente Autônomo";
  }
}

function renderToolLogs(toolCalls) {
  const terminal = document.getElementById("toolsTerminal");

  if (!toolCalls || toolCalls.length === 0) {
    terminal.innerHTML = `<p class="text-slate-400">Nenhuma ferramenta externa precisou ser acionada.</p>`;
    return;
  }

  terminal.innerHTML = toolCalls.map((t, idx) => {
    const icon = t.tool_name === "get_user_account_info" ? "👤" :
                 t.tool_name === "search_knowledge_base" ? "📚" :
                 t.tool_name === "check_system_health" ? "🖥️" :
                 t.tool_name === "escalate_to_human_tier" ? "🚨" : "🔧";

    return `
      <div class="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1.5">
        <div class="flex items-center justify-between">
          <span class="font-semibold text-indigo-300 flex items-center gap-1.5">
            <span>${icon}</span>
            <span class="font-mono">${t.tool_name}</span>
          </span>
          <span class="text-[10px] text-slate-500 font-mono">Passo #${idx + 1}</span>
        </div>
        <div class="text-[11px] text-slate-400 font-mono">
          <span class="text-slate-500">Argumentos:</span> ${JSON.stringify(t.arguments)}
        </div>
        <div class="text-[11px] text-slate-300 font-mono bg-slate-950 p-2 rounded border border-slate-800/80 overflow-x-auto max-h-32">
          ${JSON.stringify(t.output, null, 2)}
        </div>
      </div>
    `;
  }).join("");
}

function renderTriageDecision(data) {
  const triage = data.triage;
  const triageCard = document.getElementById("triageCard");
  const ticketIdBadge = document.getElementById("ticketIdBadge");
  const badgesContainer = document.getElementById("badgesContainer");
  const summaryEl = document.getElementById("triageSummary");
  const actionEl = document.getElementById("triageAction");
  const replyEl = document.getElementById("customerReplyText");

  triageCard.classList.remove("hidden");
  ticketIdBadge.innerText = data.ticket_id;

  const priorityColor = triage.priority === "critical" ? "bg-rose-500/20 text-rose-300 border-rose-500/40" :
                        triage.priority === "high" ? "bg-amber-500/20 text-amber-300 border-amber-500/40" :
                        triage.priority === "medium" ? "bg-blue-500/20 text-blue-300 border-blue-500/40" :
                        "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";

  badgesContainer.innerHTML = `
    <span class="text-xs px-2.5 py-1 rounded-full border uppercase tracking-wider font-semibold ${priorityColor}">
      ${triage.priority}
    </span>
    <span class="text-xs px-2.5 py-1 rounded-full border border-slate-700 bg-slate-800 text-slate-300 uppercase tracking-wider font-semibold">
      ${triage.category}
    </span>
    <span class="text-xs px-2.5 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 font-medium">
      ${triage.resolution_type}
    </span>
  `;

  summaryEl.innerText = triage.summary;
  actionEl.innerText = triage.action_taken;
  replyEl.innerText = triage.customer_reply;

  triageCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function loadTickets() {
  const tbody = document.getElementById("ticketsTableBody");
  try {
    const res = await fetch(`${API_BASE}/api/v1/tickets`);
    const tickets = await res.json();

    if (!tickets || tickets.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="py-4 text-center text-slate-500">Nenhum chamado registrado ainda.</td></tr>`;
      return;
    }

    tbody.innerHTML = tickets.map(t => `
      <tr class="hover:bg-slate-800/40 transition">
        <td class="py-2.5 px-3 font-mono font-bold text-indigo-400">${t.ticket_id}</td>
        <td class="py-2.5 px-3 font-mono text-slate-300">${t.user_id}</td>
        <td class="py-2.5 px-3 capitalize">${t.category}</td>
        <td class="py-2.5 px-3 font-semibold ${t.priority === 'critical' ? 'text-rose-400' : t.priority === 'high' ? 'text-amber-400' : 'text-slate-300'}">${t.priority}</td>
        <td class="py-2.5 px-3 text-slate-400 font-mono text-[11px]">${t.status}</td>
        <td class="py-2.5 px-3 text-slate-300 max-w-xs truncate">${t.resolution_summary}</td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Falha ao carregar tickets:", err);
  }
}

// Initial loads on page startup
document.addEventListener("DOMContentLoaded", () => {
  loadUsers();
  loadTickets();
  setScenario("quota");
});
