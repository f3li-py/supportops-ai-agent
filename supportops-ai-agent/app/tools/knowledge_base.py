import re
from typing import Any, Dict, List

# Simulação de base de conhecimento técnica e empresarial
ARTICLES = [
    {
        "id": "KB-101",
        "title": "Erros 429 e Limite de Taxa da API (Rate Limiting)",
        "category": "technical",
        "keywords": ["429", "rate limit", "limite de chamadas", "cota", "api", "quota", "bloqueio"],
        "content": (
            "O erro HTTP 429 Too Many Requests ocorre quando o volume de requisições excede o limite mensal ou por minuto do plano. "
            "Plano Free: 1.000 requisições/mês (10 req/min). "
            "Plano Pro: 50.000 requisições/mês (120 req/min). "
            "Plano Enterprise: Cota customizada sem limite rígido e suporte 24/7. "
            "Solução imediata: O cliente deve verificar o painel de faturamento para realizar upgrade de plano ou aplicar backoff exponencial."
        ),
    },
    {
        "id": "KB-102",
        "title": "Faturas Atrasadas e Regularização de Pagamento (Past Due)",
        "category": "billing",
        "keywords": ["pagamento", "fatura", "cartao", "past due", "atrasada", "cobranca", "bloqueada", "suspensa"],
        "content": (
            "Quando uma cobrança não é autorizada pela operadora do cartão, a conta entra no estado 'past_due' (pagamento pendente). "
            "O cliente tem um período de tolerância de 3 dias antes do bloqueio das APIs. "
            "Para regularizar: O cliente deve acessar Painel > Configurações > Cobrança e atualizar o método de pagamento. "
            "Após atualização, a re-tentativa é automática em até 10 minutos."
        ),
    },
    {
        "id": "KB-103",
        "title": "Autenticação em Duas Etapas (2FA / MFA)",
        "category": "security",
        "keywords": ["mfa", "2fa", "dois fatores", "seguranca", "autenticacao", "login", "codigo"],
        "content": (
            "A autenticação de dois fatores (MFA) é obrigatória para contas Enterprise e recomendada para todas. "
            "Para habilitar: Acesse Perfil > Segurança > Habilitar 2FA e use aplicativos como Google Authenticator ou Authy. "
            "Em caso de perda de dispositivo, um operador humano de segurança precisa verificar o documento do titular."
        ),
    },
    {
        "id": "KB-104",
        "title": "SLA e Política de Escalonamento Crítico para Clientes Enterprise",
        "category": "support",
        "keywords": ["sla", "enterprise", "incidente", "queda", "parado", "emergencia", "critico", "urgente"],
        "content": (
            "Clientes no plano Enterprise possuem SLA de resposta de 15 minutos para incidentes críticos (severidade P1). "
            "Se o problema envolver indisponibilidade de sistema ou risco de segurança em conta Enterprise, o agente DEVE "
            "acionar imediatamente a ferramenta de escalonamento humano para o time 'Engenharia de Plantão'."
        ),
    },
    {
        "id": "KB-105",
        "title": "Instabilidade de Infraestrutura e Status dos Serviços",
        "category": "technical",
        "keywords": ["status", "queda", "instabilidade", "fora do ar", "lento", "conexao", "gateway", "banco de dados"],
        "content": (
            "Para verificar se o problema decorre de uma pane global na infraestrutura da plataforma, sempre consulte "
            "o status atual dos componentes. Se houver incidente ativo no serviço correspondente, informe o cliente "
            "com transparência sobre a previsão de normalização."
        ),
    },
]


def search_knowledge_base(query: str) -> List[Dict[str, Any]]:
    """Pesquisa artigos na base de conhecimento interna por palavras-chave relevantes.

    Args:
        query: Termo ou dúvida do cliente para buscar documentação correspondente.

    Returns:
        Lista de artigos encontrados contendo id, título e conteúdo.
    """
    tokens = set(re.findall(r"\w+", query.lower()))
    scored_articles = []

    for article in ARTICLES:
        score = 0
        article_text = f"{article['title']} {article['content']}".lower()

        for token in tokens:
            if len(token) < 3:
                continue
            if token in article_text:
                score += 2
            for kw in article["keywords"]:
                if token in kw or kw in token:
                    score += 3

        if score > 0:
            scored_articles.append((score, {
                "id": article["id"],
                "title": article["title"],
                "content": article["content"],
            }))

    scored_articles.sort(key=lambda x: x[0], reverse=True)
    results = [art for _, art in scored_articles[:3]]

    # Se nada bater diretamente, retorna os 2 artigos mais gerais de suporte
    if not results:
        results = [
            {"id": "KB-101", "title": ARTICLES[0]["title"], "content": ARTICLES[0]["content"]},
            {"id": ARTICLES[4]["id"], "title": ARTICLES[4]["title"], "content": ARTICLES[4]["content"]},
        ]

    return results
