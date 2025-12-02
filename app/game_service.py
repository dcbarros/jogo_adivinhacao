# app/game_service.py
import json
import uuid
import random
from typing import Tuple
from sqlalchemy.orm import Session
from . import models
from .llm_client import generate_word_and_hints

CATEGORIES = ["objeto", "fruta", "país", "estado brasileiro", "animal", "profissão", "esporte"]


def _normalize(text: str) -> str:
    return text.strip().lower()


def get_or_create_session(db: Session, session_id: str | None) -> models.GameSession:

    if session_id:
        session = (
            db.query(models.GameSession)
            .filter(models.GameSession.session_id == session_id)
            .order_by(models.GameSession.id.desc())
            .first()
        )
        if session and not session.finished:
            return session

    new_session_id = session_id or str(uuid.uuid4())
    category = random.choice(CATEGORIES)

    word_data = generate_word_and_hints(category)
    hints_json = json.dumps(word_data["hints"], ensure_ascii=False)

    session = models.GameSession(
        session_id=new_session_id,
        category=category,
        word=_normalize(word_data["word"]),
        hints_json=hints_json,
        attempts=0,
        finished=False,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def _build_new_game_message(session: models.GameSession) -> str:

    hints = json.loads(session.hints_json)
    first_hint = hints[0] if hints else "Não foi possível gerar dica."
    return (
        f"🎮 Novo jogo iniciado!\n"
        f"Categoria: {session.category}.\n"
        f"Dica 1: {first_hint}\n"
        f"Você tem 5 tentativas para acertar a palavra."
    )


def process_message(db: Session, session_id: str, user_message: str) -> Tuple[str, bool, str]:

    session = get_or_create_session(db, session_id)
    text = _normalize(user_message)
    max_attempts = 5

    if text in {"novo jogo", "reiniciar", "resetar"}:
        session.finished = True
        db.commit()

        new_session = get_or_create_session(db, None)
        reply = _build_new_game_message(new_session)
        return reply, False, new_session.session_id

    if session.finished:
        new_session = get_or_create_session(db, None)
        reply = _build_new_game_message(new_session)
        return reply, False, new_session.session_id

    hints = json.loads(session.hints_json)

    session.attempts += 1
    db.commit()  

    guess = text
    correct = guess == _normalize(session.word)
    attempts_left = max_attempts - session.attempts
    finished = False

    reply_lines: list[str] = []

    if correct:
        finished = True
        reply_lines.append("🎉 Parabéns, você acertou!")
        reply_lines.append(f"A palavra era: **{session.word}**.")
        reply_lines.append(f"Você usou {session.attempts} tentativa(s).")
        reply_lines.append("Clique em **Novo jogo** para jogar novamente.")
    else:
        if session.attempts >= max_attempts:

            finished = True
            reply_lines.append("❌ Você usou todas as tentativas.")
            reply_lines.append(f"A palavra correta era: **{session.word}**.")
            reply_lines.append("Clique em **Novo jogo** para iniciar outra partida.")
        else:

            idx = min(session.attempts, len(hints) - 1)
            next_hint = hints[idx]

            reply_lines.append("Ainda não é essa palavra.")
            reply_lines.append(f"Tentativas restantes: {attempts_left}.")
            reply_lines.append(f"Próxima dica: {next_hint}")

    session.finished = finished
    db.commit()
    db.refresh(session)

    reply = "\n".join(reply_lines)
    return reply, finished, session.session_id
