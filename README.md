
# AdivinhaBot — Resumo do Projeto

## 1. Visão geral do projeto

O AdivinhaBot é um chatbot simples feito em Python que vira um joguinho de adivinhação de palavras usando IA generativa.  
A ideia é bem direta: o bot escolhe uma palavra secreta dentro de uma categoria (ex.: país, fruta, animal), gera cinco dicas com ajuda de um modelo de linguagem e o usuário vai chutando até acertar ou acabar as tentativas.

Ele foi pensado para atender os requisitos do projeto final: aplicação em Python, interface onde o usuário digita a mensagem, envio dessa mensagem para um modelo de IA e manutenção da conversação até o usuário encerrar o jogo.

Além disso, o projeto também implementa uma interface gráfica com Gradio, que está listada como uma das funcionalidades opcionais nas diretrizes.

---

## 2. Tecnologias utilizadas

- **Linguagem:** Python  
- **Backend / API:** FastAPI  
- **Interface web:** Gradio  
- **Banco de dados:** SQLite, via SQLAlchemy  
- **Cliente de IA:** consumo de modelo via API HTTP (OpenRouter), usando `requests`  
- **Gerenciamento de ambiente:** `python-dotenv` para ler a chave da IA do arquivo `.env`

A chave do modelo de IA é carregada de variável de ambiente (`OPENROUTER_API_KEY`) e o nome do modelo e URL base também ficam centralizados numa classe de configuração.

---

## 3. Arquitetura da solução

A aplicação está organizada em módulos dentro do diretório `app/`:

### 3.1. `config.py`

- Centraliza as configurações do sistema:
  - Nome da aplicação;
  - URL do banco (`sqlite:///./game.db`);
  - Chave da API do provedor de IA;
  - Modelo e URL do endpoint de chat.
- Usa `dotenv` para carregar variáveis do arquivo `.env`, o que facilita trocar o modelo ou a chave sem mexer no código.

### 3.2. `database.py` e `models.py`

- `database.py`:
  - Cria o `engine` do SQLAlchemy apontando para o SQLite;
  - Define a `SessionLocal` e a `Base` para os modelos;
  - Expõe a função `get_db()` usada como dependência no FastAPI para abrir/fechar a sessão de banco de dados por requisição.

- `models.py`:
  - Define a tabela `GameSession`, responsável por guardar o estado do jogo:
    - `session_id`: identificador lógico da sessão (UUID);
    - `category`: categoria escolhida (país, fruta, etc.);
    - `word`: palavra secreta normalizada (minúsculas, sem espaços extras);
    - `hints_json`: lista de dicas em formato JSON armazenada como texto;
    - `attempts`: quantidade de tentativas já usadas;
    - `finished`: flag para saber se o jogo daquela sessão já terminou;
    - `create_at`: data/hora da criação da sessão.

Isso garante a “memória” mínima do chatbot: mesmo sendo uma API stateless por HTTP, o estado do jogo é mantido no banco via `session_id`.

### 3.3. `schemas.py`

- Define os modelos Pydantic usados na API:
  - `ChatRequest`: recebe `session_id` e `user_message`;
  - `ChatResponse`: devolve `session_id`, `reply` (texto de resposta) e `finished` (se o jogo acabou ou não).

Esses esquemas garantem que a entrada e a saída da API sigam um formato bem definido.

### 3.4. `llm_client.py`

Aqui fica o cliente que conversa com o modelo de linguagem.

- Função `_post_openrouter(messages)`:
  - Monta o payload no formato de `messages` (estilo chat);
  - Envia a requisição POST para o endpoint configurado;
  - Devolve só o `content` da resposta do modelo;
  - Faz tratamento básico de erro com `raise_for_status()`.

- Função `generate_word_and_hints(category)`:
  - Envia um prompt de sistema explicando que o modelo deve:
    - Escolher uma palavra para a categoria recebida;
    - Gerar **exatamente 5 dicas** curtas e objetivas;
    - Responder **apenas em JSON** no formato:
      ```json
      {"word": "...", "hints": ["...", "...", "...", "...", "..."]}
      ```
  - Tenta se proteger de respostas com Markdown, removendo ``` caso o modelo embrulhe o JSON em bloco de código;
  - Faz um `json.loads` do texto final e garante que:
    - Existe a chave `word`;
    - Existe a chave `hints` com pelo menos 5 itens;
  - Em seguida, corta a lista para as cinco primeiras dicas e devolve só `word` + `hints`.

- Função `format_reply(context)`:
  - Define um prompt para o modelo atuar como narrador do jogo;
  - Recebe um dicionário com informações do estado da jogada (se acertou, tentativas restantes, próxima dica, etc.);
  - Gera um texto curto e amigável para o jogador.
  - Essa função já está pronta, mas o fluxo principal hoje monta a resposta “na mão”, então ela fica como possibilidade de melhoria futura (usar IA também na formatação da resposta ao invés de texto fixo).

### 3.5. `game_service.py`

É o módulo que concentra a regra de negócio do jogo.

- Lista fixa de categorias (`CATEGORIES`): objeto, fruta, país, estado brasileiro, animal, profissão, esporte.
- Função `_normalize(text)`:
  - Faz o “tratamento” do palpite e da palavra secreta: tira espaços extras e converte para minúsculas.

- Função `get_or_create_session(db, session_id)`:
  - Se recebeu um `session_id`, tenta buscar a última sessão desse id:
    - Se encontrar uma sessão **não finalizada**, reaproveita a mesma;
    - Se não encontrar ou se já estiver `finished`, cria uma nova.
  - Na criação de nova sessão:
    - Gera um `UUID` se não tiver `session_id`;
    - Sorteia uma categoria aleatória da lista;
    - Chama `generate_word_and_hints(category)` para pegar a palavra secreta e as cinco dicas;
    - Normaliza a palavra secreta;
    - Salva tudo na tabela `GameSession` com `attempts = 0` e `finished = False`.

- Função `_build_new_game_message(session)`:
  - Carrega as dicas do `hints_json` e pega a primeira dica;
  - Monta o texto inicial para o jogador, informando:
    - Que um novo jogo foi iniciado;
    - Qual a categoria;
    - A primeira dica;
    - E o número de tentativas (5).

- Função `process_message(db, session_id, user_message)`:
  - Garante que existe uma sessão ativa (`get_or_create_session`);
  - Normaliza o texto do usuário;
  - Define `max_attempts = 5`.

  Fluxo principal:

  1. **Comandos de controle**  
     Se o usuário digita algo como `"novo jogo"`, `"reiniciar"` ou `"resetar"`:
     - Marca a sessão atual como finalizada;
     - Cria uma nova sessão;
     - Devolve a mensagem padrão de novo jogo com a primeira dica.

  2. **Sessão já finalizada**  
     Se a sessão que chegou já estava `finished`:
     - Automaticamente inicia um novo jogo e já responde como no passo anterior.

  3. **Palpite normal**  
     - Carrega as dicas do JSON;
     - Incrementa o número de tentativas e salva;
     - Calcula quantas tentativas ainda restam;
     - Compara o palpite com a palavra secreta:
       - **Acertou:**
         - Marca `finished = True`;
         - Monta uma resposta parabenizando e mostrando a palavra correta;
       - **Errou sem tentativas restantes:**
         - Marca `finished = True`;
         - Informa ao usuário que as tentativas acabaram e revela a palavra secreta;
       - **Errou com tentativas restantes:**
         - Mantém `finished = False`;
         - Escolhe a próxima dica com base no número de tentativas já feitas;
         - Monta uma resposta dizendo que ainda não é a palavra, mostra quantas tentativas restam e exibe a próxima dica.

  No final, a função devolve:
  - O texto da resposta;
  - Um booleano indicando se o jogo terminou ou não;
  - O `session_id` (caso tenha sido criado um novo).

### 3.6. `main.py` (API FastAPI)

- Cria a aplicação FastAPI e chama `Base.metadata.create_all(bind=engine)` para garantir que a tabela existe.
- Configura CORS liberando acesso de qualquer origem (útil para a interface rodar separada da API).
- Define o endpoint principal:

  ```python
  @app.post("/chat", response_model=ChatResponse)
  def chat(payload: ChatRequest, db: Session = Depends(get_db)):
      reply, finished, new_session_id = process_message(
          db=db,
          session_id=payload.session_id,
          user_message=payload.user_message,
      )
      return ChatResponse(
          session_id=new_session_id,
          reply=reply,
          finished=finished,
      )
  ```

- Também tem um `GET /` simples só para indicar que a API está no ar.

### 3.7. `ui.py` (interface Gradio)

- Define o `API_URL` apontando para `http://127.0.0.1:8000/chat`;
- Função `create_session_id()` gera um `UUID` novo caso ainda não exista;
- Função `send_message(message, chat_history, session_id)`:
  - Garante que exista histórico de chat e `session_id`;
  - Envia um POST para a API com `user_message` e `session_id`;
  - Lê o JSON de resposta e extrai a mensagem (`reply`) e o `session_id` retornado;
  - Atualiza o histórico do `Chatbot` com a fala do usuário e a resposta do bot.

- Função `new_game(...)`:
  - Basicamente dispara `send_message("novo jogo", ...)` para forçar a API a reiniciar o jogo.

- Função `clear_chat()`:
  - Limpa o histórico e zera o estado da sessão.

- A interface em si usa `gr.Blocks`:
  - Um título “AdivinhaBot” com explicação rápida de como jogar;
  - Um componente `Chatbot` para mostrar as mensagens;
  - Um `Textbox` para o usuário digitar os palpites;
  - Botão **Enviar**, botão **Novo jogo** e botão **Limpar chat**;
  - As ações de `submit` e `click` desses botões são ligadas às funções descritas acima.

### 4. Execução

#### 4.1. Criar e ativar o ambiente virtual

Windows (PowerShell ou CMD)

Na raiz do projeto, execute:
```bash
python -m venv venv  
venv\Scripts\activate 
```
Sempre que for usar o projeto, lembre de ativar o ambiente virtual antes de rodar os comandos.

#### 4.2. Instalar as dependências

Ainda na pasta raiz do projeto, onde existe o arquivo requirements.txt, execute no terminal:

```bash
pip install -r requirements.txt
```

#### 4.3. Configurar variáveis de ambiente

Crie um arquivo chamado .env na raiz do projeto e adicione a chave do LLM que você irá utilizar. Exemplo:

```
OPENAI_API_KEY=sua_chave_aqui
```

#### 4.5. Execução

##### 4.5.1 API (FastAPI)

Na raiz do projeto, execute:
```bash
uvicorn app.main:app --reload
```

A API ficará disponível em:
- http://127.0.0.1:8000
- Documentação automática (Swagger): http://127.0.0.1:8000/docs

Deixe esse terminal aberto enquanto estiver usando o sistema.

##### 4.5.2 Interface (Gradio)

Em outro terminal (também com o ambiente virtual ativado), na raiz do projeto, execute:
```bash
python -m app.ui
```
---

