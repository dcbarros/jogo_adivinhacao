import uuid
import requests
import gradio as gr

API_URL = "http://127.0.0.1:8000/chat"


def create_session_id() -> str:
    return str(uuid.uuid4())


def send_message(message: str, chat_history, session_id: str):

    if chat_history is None:
        chat_history = []

    if not message.strip():
        return "", chat_history, session_id

    if not session_id:
        session_id = create_session_id()

    payload = {
        "session_id": session_id,
        "user_message": message,
    }

    try:
        resp = requests.post(API_URL, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:

        chat_history.append({"role": "user", "content": message})
        chat_history.append(
            {
                "role": "assistant",
                "content": f"⚠️ Erro ao falar com a API: {e}",
            }
        )
        return "", chat_history, session_id

    new_session_id = data.get("session_id", session_id)
    reply = data.get("reply", "Não entendi a resposta da API.")

    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": reply})

    return "", chat_history, new_session_id


def new_game(chat_history, session_id: str):

    if chat_history is None:
        chat_history = []

    _msg, new_history, new_session_id = send_message("novo jogo", chat_history, session_id)
    return new_history, new_session_id


def clear_chat():
    return [], ""


with gr.Blocks(title="AdivinhaBot") as demo:
    gr.Markdown(
        """
        # 🎯 AdivinhaBot
        Jogo de adivinhação com IA.

        **Como jogar:**
        1. Clique em **Novo jogo** para o bot iniciar uma nova palavra secreta.
        2. O bot vai dar uma dica.
        3. Você tenta adivinhar a palavra com base nas dicas.
        4. A cada erro, uma nova dica é mostrada (até o limite de 5 tentativas).
        5. Quando quiser recomeçar, clique em **Novo jogo** novamente.
        """
    )
    session_state = gr.State("")

    chatbot = gr.Chatbot(label="Mensagens do Jogo")
    with gr.Row():
        msg = gr.Textbox(
            label="Seu palpite",
            placeholder="Digite aqui...",
            scale=4,
        )
        send_btn = gr.Button("Enviar", scale=1)

    with gr.Row():
        newgame_btn = gr.Button("Novo jogo", variant="primary")
        clear_btn = gr.Button("Limpar chat")

    msg.submit(
        send_message,
        inputs=[msg, chatbot, session_state],
        outputs=[msg, chatbot, session_state],
    )

    send_btn.click(
        send_message,
        inputs=[msg, chatbot, session_state],
        outputs=[msg, chatbot, session_state],
    )

    newgame_btn.click(
        new_game,
        inputs=[chatbot, session_state],
        outputs=[chatbot, session_state],
    )

    clear_btn.click(
        clear_chat,
        inputs=[],
        outputs=[chatbot, session_state],
    )

if __name__ == "__main__":
    demo.launch()
