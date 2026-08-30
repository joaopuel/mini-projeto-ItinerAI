"""Validação de entrada do usuário para o ItinerAI.

Bloqueia, antes de a mensagem chegar ao LLM do agente, três tipos de entrada:

1. Prompt injection (ex.: "ignore as instruções anteriores"), detectado por
   regex nos 6 idiomas mais falados: português, inglês, espanhol, francês,
   mandarim e híndi.
2. Mensagens em outros idiomas: o filtro barra scripts não-latinos (mandarim/
   CJK e híndi/devanágari). Inglês/espanhol/francês não são barrados aqui — só
   suas eventuais tentativas de injeção (regra 1) — para não gerar falso
   positivo em português.
3. URLs/links enviados pelo usuário — o agente nunca deve acessá-los.

Toda a detecção é determinística (regex puro, sem LLM/rede), mantendo o módulo
barato, previsível e testável.
"""

import re

# --- URLs / links (regra 3) ------------------------------------------------

# Cobre http(s)://, www. e domínios "nus" (exemplo.com, site.com.br/rota).
_URL_PATTERN = re.compile(
    r"https?://\S+"
    r"|www\.\S+"
    r"|\b[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.(?:com|net|org|br|io|gov|edu|"
    r"info|co|app|dev|me|tv|xyz|site|online)\b(?:/\S*)?",
    re.IGNORECASE,
)

# --- Prompt injection (regra 1) --------------------------------------------

# Frases típicas de injeção/jailbreak nos 6 idiomas. Cada padrão é tolerante a
# artigos/variações de flexão para reduzir evasões triviais.
_INJECTION_PATTERNS = [
    # Português
    r"ignor\w*\s+(?:as?\s+|os?\s+|todas?\s+|todos?\s+|tudo\s+|essas?\s+|esses?\s+)*"
    r"(?:instru\w+|prompts?|mensage\w+|regras?|orienta\w+|coman\w+)",
    r"desconsider\w*\s+(?:as?\s+|os?\s+|todas?\s+|tudo\s+)*"
    r"(?:instru\w+|prompts?|regras?|orienta\w+)",
    r"esque\w*\s+(?:as?\s+|os?\s+|tudo\s+|todas?\s+)*"
    r"(?:instru\w+|prompts?|regras?|orienta\w+)",
    r"novas?\s+instru\w+",
    r"revel\w*.{0,20}(?:prompt|instru\w+|regras)",
    r"prompt\s+do\s+sistema",
    r"aja\s+como|finja\s+ser|se\s+comporte\s+como",
    r"modo\s+desenvolvedor",
    # Inglês
    r"ignore\s+(?:all\s+|the\s+|any\s+|these\s+|previous\s+)*"
    r"(?:previous|prior|above|earlier|preceding)?\s*"
    r"(?:instruction|prompt|message|rule|command)s?",
    r"disregard\s+(?:all\s+|the\s+|any\s+)*(?:previous|prior|above)",
    r"forget\s+(?:all\s+|your\s+|the\s+|everything|previous)",
    r"new\s+instructions?",
    r"system\s+prompt",
    r"(?:act|behave)\s+as|pretend\s+to\s+be",
    r"developer\s+mode|jailbreak|dan\s+mode",
    r"override\s+(?:your\s+|the\s+)?(?:instructions?|rules?|prompt)",
    # Espanhol
    r"ignora\w*\s+(?:las?\s+|los?\s+|todas?\s+|todos?\s+)*"
    r"(?:instruccion\w+|indicacion\w+|reglas?|órdenes|ordenes)",
    r"olvida\w*\s+(?:las?\s+|los?\s+|todas?\s+)*"
    r"(?:instruccion\w+|indicacion\w+|reglas?)",
    r"nuevas?\s+instruccion\w+",
    r"actúa\s+como|actua\s+como|compórtate\s+como|comportate\s+como",
    r"modo\s+desarrollador",
    # Francês
    r"ignore[rz]?\s+(?:les?\s+|toutes?\s+|tous\s+)*"
    r"(?:instructions?|consignes?|règles?|regles?)",
    r"oublie[rz]?\s+(?:les?\s+|toutes?\s+|vos\s+)*"
    r"(?:instructions?|consignes?|règles?|regles?)",
    r"nouvelles?\s+instructions?",
    r"agis\s+comme|comporte-toi\s+comme|fais\s+semblant",
    r"mode\s+développeur|mode\s+developpeur",
    # Mandarim (chinês simplificado): "忽略/无视...(之前/上面的)指令/提示/规则"
    r"(?:忽略|无视|忘记|忘掉).{0,6}(?:指令|提示|规则|说明|命令)",
    r"新的?指令",
    r"系统提示",
    # Híndi (devanágari): "पिछले निर्देशों को अनदेखा/नज़रअंदाज़ करें"
    r"(?:निर्देश\w*|आदेश\w*|नियम\w*).{0,12}(?:अनदेखा|नज़रअंदाज़|नजरअंदाज|भूल)",
    r"नए\s+निर्देश",
]
_INJECTION_REGEXES = [re.compile(pattern, re.IGNORECASE) for pattern in _INJECTION_PATTERNS]

# --- Idioma: scripts não-latinos (regra 2) ---------------------------------

# CJK (mandarim) e devanágari (híndi). A presença de qualquer caractere dessas
# faixas indica um idioma que o agente não deve atender.
_NON_LATIN_SCRIPT_PATTERN = re.compile(
    r"[一-鿿㐀-䶿"  # CJK unificado (+ extensão A)
    r"ऀ-ॿ]"  # devanágari
)

# --- Mensagens informativas ao usuário -------------------------------------

INJECTION_MESSAGE = (
    "Desculpe, não posso atender a esse pedido: percebi uma tentativa de alterar "
    "as minhas instruções. Estou aqui apenas para ajudar a planejar a sua viagem. "
    "Me conte o destino e por quantos dias você pretende viajar."
)
FOREIGN_LANGUAGE_MESSAGE = (
    "Por favor, fale comigo em português. Só consigo ajudar no planejamento da "
    "sua viagem quando a conversa acontece em português. Me diga o destino e por "
    "quantos dias você pretende viajar."
)
URL_MESSAGE = (
    "Por segurança, não acesso links ou URLs enviados por usuários. Se quiser, me "
    "diga apenas o nome do destino (e por quantos dias você pretende viajar) que eu "
    "pesquiso as informações para você."
)
INVALID_EMAIL_MESSAGE = (
    "O endereço de e-mail informado não parece válido, então não vou enviar nada. "
    "O roteiro continua disponível no arquivo criado em output/."
)


# --- E-mail do destinatário (T14/#25) --------------------------------------

# Validação de FORMATO, não de existência: um endereço bem-formado é o suficiente
# para decidir se vale acionar o webhook do n8n.
#
# Este padrão é DELIBERADAMENTE MAIS ESTRITO que o do nó `Validar payload` do
# workflow (`docs/low-code/n8n-workflow.json`, `^[^@\s]+@[^@\s.]+\.[^@\s]+$`),
# que aceita rótulo vazio e ponto final (`a@b..c`, `a@b.c.`) porque o `[^@\s]+`
# final permite pontos. Aqui cada rótulo depois do @ precisa ser não vazio.
# A assimetria é segura no sentido em que existe: a aplicação valida ANTES e é
# a mais restritiva, então o n8n nunca recebe algo que ela recusaria. Ao mexer
# em um dos lados, não presuma que o outro acompanha.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+$")


def is_valid_email(text: str) -> bool:
    """Indica se o texto é um endereço de e-mail bem-formado.

    Determinístico e sem rede, no mesmo espírito das demais regras deste módulo:
    não verifica se a caixa existe, apenas se o formato justifica a chamada
    externa."""
    return bool(_EMAIL_PATTERN.match(text.strip()))


def contains_url(text: str) -> bool:
    """Indica se o texto contém uma URL ou link."""
    return bool(_URL_PATTERN.search(text))


def contains_prompt_injection(text: str) -> bool:
    """Indica se o texto contém uma tentativa de prompt injection/jailbreak
    (em qualquer um dos 6 idiomas cobertos)."""
    return any(regex.search(text) for regex in _INJECTION_REGEXES)


def contains_non_latin_script(text: str) -> bool:
    """Indica se o texto contém caracteres de um script não-latino barrado
    (mandarim/CJK ou híndi/devanágari)."""
    return bool(_NON_LATIN_SCRIPT_PATTERN.search(text))


def validate_user_input(text: str) -> str | None:
    """Valida a mensagem do usuário contra as regras de entrada.

    Retorna a mensagem de recusa (em português) da primeira regra violada, ou
    `None` se a entrada for válida. A ordem prioriza a injeção de prompt: uma
    tentativa de injeção em mandarim/híndi recebe a mensagem específica de
    injeção, e não a de idioma.
    """
    if contains_prompt_injection(text):
        return INJECTION_MESSAGE
    if contains_non_latin_script(text):
        return FOREIGN_LANGUAGE_MESSAGE
    if contains_url(text):
        return URL_MESSAGE
    return None
