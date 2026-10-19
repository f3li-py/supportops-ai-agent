import json
import logging
import time
from typing import Any, Dict, List, Tuple

from google import genai
from google.genai import types

from app.agent.prompt import SYSTEM_INSTRUCTION
from app.config import get_settings
from app.schemas import (
    ResolutionType,
    TicketCategory,
    TicketPriority,
    ToolCallLog,
    TriageOutput,
)
from app.tools.escalation import escalate_to_human_tier
from app.tools.knowledge_base import search_knowledge_base
from app.tools.system_status import check_system_health
from app.tools.user_service import get_user_account_info

logger = logging.getLogger("supportops.agent")
settings = get_settings()


class SupportAgentEngine:
    """Core autonomous agent engine orchestrating Gemini Function Calling and Structured Output."""

    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model_name or settings.gemini_model
        self.tool_dispatcher = {
            "search_knowledge_base": search_knowledge_base,
            "get_user_account_info": get_user_account_info,
            "check_system_health": check_system_health,
            "escalate_to_human_tier": escalate_to_human_tier,
        }

        if self.api_key and self.api_key.strip():
            self.client = genai.Client(api_key=self.api_key)
            logger.info("Google GenAI client initialized with model %s", self.model_name)
        else:
            self.client = None
            logger.warning("No GEMINI_API_KEY detected. Running in resilient offline mode.")

    def process_ticket(
        self,
        ticket_id: str,
        user_id: str,
        message: str,
    ) -> Tuple[TriageOutput, List[ToolCallLog], float]:
        """Runs the investigation and triage loop for an incoming ticket."""
        start_time = time.time()
        tool_logs: List[ToolCallLog] = []

        if self.client is None:
            triage, logs = self._fallback_triage(ticket_id, user_id, message)
            execution_time = round(time.time() - start_time, 3)
            return triage, logs, execution_time

        try:
            triage, tool_logs = self._run_gemini_agent_loop(ticket_id, user_id, message)
        except Exception as exc:
            logger.error("Error during Gemini agent execution: %s. Falling back to local triage.", exc)
            triage, fallback_logs = self._fallback_triage(ticket_id, user_id, message)
            tool_logs.extend(fallback_logs)

        execution_time = round(time.time() - start_time, 3)
        return triage, tool_logs, execution_time

    def _run_gemini_agent_loop(
        self,
        ticket_id: str,
        user_id: str,
        message: str,
    ) -> Tuple[TriageOutput, List[ToolCallLog]]:
        """Executes multi-turn tool calling and extracts structured triage."""
        tool_logs: List[ToolCallLog] = []
        tools_list = list(self.tool_dispatcher.values())

        prompt = (
            f"Ticket ID: {ticket_id}\n"
            f"ID do Usuário: {user_id}\n"
            f"Mensagem do Cliente:\n\"{message}\"\n\n"
            f"Inicie sua investigação técnica utilizando as ferramentas disponíveis."
        )

        contents: List[Any] = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            )
        ]

        # Multi-turn tool execution loop (máx 5 turnos de ferramentas)
        for turn in range(5):
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=tools_list,
                automatic_function_calling=False,
                temperature=0.2,
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )

            candidate = response.candidates[0] if response.candidates else None
            if not candidate or not candidate.content:
                break

            # Se o modelo não chamou ferramentas neste turno, terminamos a fase de busca
            if not response.function_calls:
                contents.append(candidate.content)
                break

            # O modelo chamou ferramentas: registrar e executar cada uma
            contents.append(candidate.content)
            response_parts = []

            for call in response.function_calls:
                func_name = call.name
                func_args = dict(call.args) if call.args else {}

                logger.info("Executing tool: %s with args: %s", func_name, func_args)
                tool_func = self.tool_dispatcher.get(func_name)

                if tool_func:
                    try:
                        result = tool_func(**func_args)
                    except Exception as err:
                        result = {"error": f"Tool execution failed: {str(err)}"}
                else:
                    result = {"error": f"Unknown tool '{func_name}'"}

                tool_logs.append(
                    ToolCallLog(
                        tool_name=func_name,
                        arguments=func_args,
                        output=result,
                    )
                )

                response_parts.append(
                    types.Part.from_function_response(
                        name=func_name,
                        response={"result": result},
                    )
                )

            contents.append(
                types.Content(
                    role="tool",
                    parts=response_parts,
                )
            )

        # Passo Final: Gerar a saída estruturada com Pydantic schema
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=(
                            "Com base em todas as evidências coletadas, produza o relatório de triagem técnica final "
                            "estritamente de acordo com o esquema JSON configurado."
                        )
                    )
                ],
            )
        )

        final_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=TriageOutput,
            temperature=0.1,
        )

        final_response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=final_config,
        )

        triage_output = TriageOutput.model_validate_json(final_response.text)
        return triage_output, tool_logs

    def _fallback_triage(
        self,
        ticket_id: str,
        user_id: str,
        message: str,
    ) -> Tuple[TriageOutput, List[ToolCallLog]]:
        """Determinist, rule-based fallback when API key is missing or service is offline."""
        logs: List[ToolCallLog] = []

        # 1. Obter dados do usuário
        user_info = get_user_account_info(user_id)
        logs.append(ToolCallLog(tool_name="get_user_account_info", arguments={"user_id": user_id}, output=user_info))

        # 2. Pesquisar documentação
        kb_results = search_knowledge_base(message)
        logs.append(ToolCallLog(tool_name="search_knowledge_base", arguments={"query": message}, output=kb_results))

        # 3. Lógica de decisão
        user_plan = user_info.get("plan", "Free")
        user_status = user_info.get("status", "active")
        is_quota_exhausted = user_info.get("is_quota_exhausted", False)
        msg_lower = message.lower()

        if "429" in msg_lower or is_quota_exhausted:
            category = TicketCategory.TECHNICAL
            priority = TicketPriority.HIGH if user_plan == "Enterprise" else TicketPriority.MEDIUM
            resolution = ResolutionType.RESOLVED_AUTOMATICALLY
            summary = f"Cliente atingiu o limite de requisições de API ({user_info.get('api_calls_this_month')}/{user_info.get('api_limit')})."
            action = "Diagnosticado erro 429 por cota esgotada. Orientado upgrade de plano e backoff exponencial."
            reply = (
                f"Olá {user_info.get('name', 'Cliente')}, identificamos que sua conta consumiu 100% da cota mensal "
                f"do plano {user_plan} ({user_info.get('api_limit')} requisições). Para retomar o tráfego imediatamente, "
                f"acesse a aba Faturamento no console para realizar o upgrade para o plano superior."
            )
        elif user_status == "past_due":
            category = TicketCategory.BILLING
            priority = TicketPriority.HIGH
            resolution = ResolutionType.RESOLVED_AUTOMATICALLY
            summary = "Bloqueio ou instabilidade causado por fatura em aberto (status past_due)."
            action = "Localizada pendência financeira no cartão cadastrado. Orientada atualização no portal de cobrança."
            reply = (
                f"Olá {user_info.get('name', 'Cliente')}, sua conta está atualmente com status de pagamento pendente. "
                f"Por favor, atualize seus dados de cartão em Configurações > Cobrança para restabelecer os serviços automaticamente."
            )
        elif user_plan == "Enterprise" and any(k in msg_lower for k in ["urgente", "queda", "parado", "emergencia"]):
            category = TicketCategory.TECHNICAL
            priority = TicketPriority.CRITICAL
            resolution = ResolutionType.ESCALATED_TO_HUMAN

            esc_res = escalate_to_human_tier(ticket_id, "engineering", "critical", "Incidente crítico em conta Enterprise.")
            logs.append(ToolCallLog(
                tool_name="escalate_to_human_tier",
                arguments={"ticket_id": ticket_id, "department": "engineering", "urgency": "critical", "reason": "SLA Enterprise P1"},
                output=esc_res,
            ))

            summary = "Incidente de alta criticidade reportado por cliente Enterprise. Acionado plantão de engenharia P1."
            action = f"Escalado via protocolo {esc_res['escalation_protocol']} com SLA de 15 minutos."
            reply = (
                f"Olá {user_info.get('name', 'Cliente')}, identificamos seu plano Enterprise e a alta criticidade do seu relato. "
                f"Seu caso foi escalado com prioridade máxima (Protocolo: {esc_res['escalation_protocol']}) e nosso plantão "
                f"de engenharia entrará em contato em menos de 15 minutos."
            )
        else:
            category = TicketCategory.TECHNICAL
            priority = TicketPriority.LOW
            resolution = ResolutionType.RESOLVED_AUTOMATICALLY
            summary = "Dúvida geral de suporte atendida com base nos artigos da base de conhecimento."
            action = "Pesquisa na base de conhecimento e resposta consultiva enviada ao cliente."
            top_article = kb_results[0]["title"] if kb_results else "Documentação Geral"
            reply = (
                f"Olá {user_info.get('name', 'Cliente')}, consultamos nossa documentação técnica ({top_article}) "
                f"para ajudar com a sua dúvida. Se precisar de passos adicionais ou suporte avançado, estamos à disposição!"
            )

        triage = TriageOutput(
            category=category,
            priority=priority,
            resolution_type=resolution,
            summary=summary,
            action_taken=action,
            customer_reply=reply,
        )
        return triage, logs
