import json
import requests
from typing import List, Dict
from .config import config


HEADERS = {
    "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost",
    "X-Title": config.APP_NAME,
}


def _post_openrouter(messages: List[Dict]) -> str:
    """
    Envia uma requisição para a OpenRouter e devolve apenas o content do modelo.
    """
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY não configurada no ambiente (.env).")

    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": messages,
    }

    resp = requests.post(
        config.OPENROUTER_BASE_URL,
        headers=HEADERS,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    return data["choices"][0]["message"]["content"]


def generate_word_and_hints(category: str) -> Dict:

    system_msg = {
        "role": "system",
        "content": (
            "Você é um gerador de desafios de adivinhação em português. "
            "Escolha uma palavra para a categoria informada "
            "A palavra escolhida deve gerar um médio desafio, não deve ser muito fácil nem muito difícil. "
            "e crie exatamente 5 dicas claras e objetivas sobre essa palavra "
            "Gere os textos das dicas de forma concisa, diretamente relacionada à palavra, sem dizer a palavra secreta"
            "Evite usar frases como 'a palavra é...' ou 'a resposta é...'. "
            "Evite usar dicas que sejam muito óbvias ou que possam levar a múltiplas interpretações. "
            "O tom dos textos das dicas devem ser divertidos e envolventes."
            "NÃO explique nada, apenas devolva JSON."
        ),
    }
    user_msg = {
        "role": "user",
        "content": (
            "Gere uma palavra secreta em português e cinco dicas objetivas. "
            f"Categoria: {category}. "
            "Responda SOMENTE em JSON no formato: "
            '{"word": "palavra", "hints": ["dica1", "dica2", "dica3", "dica4", "dica5"]}. '
            "Não use markdown, não use ```."
        ),
    }

    content = _post_openrouter([system_msg, user_msg])

    text = content.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]

    try:
        data = json.loads(text)
        assert "word" in data and "hints" in data
        assert isinstance(data["hints"], list) and len(data["hints"]) >= 5
        return {
            "word": data["word"],
            "hints": data["hints"][:5],
        }
    except Exception as e:
        print("ERRO AO PARSEAR JSON DA OPENROUTER")
        print("Conteúdo bruto recebido:")
        print(repr(content))
        print("Após limpeza:")
        print(repr(text))
        print("Exceção:", e)
        raise RuntimeError("Falha ao interpretar resposta do modelo para gerar dicas.")


def format_reply(context: Dict) -> str:
    """
    Usa o modelo para formatar uma resposta amigável em português
    com base no contexto da jogada.

    context pode conter:
      - event: "new_game", "guess", etc.
      - last_guess
      - correct (bool)
      - attempts_left (int)
      - next_hint (str | None)
      - answer (str)
      - finished (bool)
    """
    system_msg = {
        "role": "system",
        "content": (
            "Você é o narrador de um jogo de adivinhação de palavras em português. "
            "Explique de forma curta, clara e amigável o que aconteceu na jogada. "
            "Se o jogador acertar, parabenize. Se errar, informe quantas tentativas "
            "restam e mostre a próxima dica (quando houver). "
            "Se o jogo acabou, revele a palavra correta e convide para um novo jogo."
        ),
    }

    user_msg = {
        "role": "user",
        "content": (
            "Gere uma mensagem curta para o jogador em português com base neste contexto: "
            f"{json.dumps(context, ensure_ascii=False)}"
        ),
    }

    reply = _post_openrouter([system_msg, user_msg])
    return reply.strip()
