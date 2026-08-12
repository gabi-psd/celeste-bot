import os
import json
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

from openai import OpenAI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ============================================================
# CONFIGURAÇÕES
# ============================================================

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY)

# Arquivo onde vamos guardar as memórias importantes
MEMORY_FILE = Path("memory.json")


# ============================================================
# SERVIDOR PARA O RENDER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Celeste is alive!")

    def log_message(self, format, *args):
        return


def start_health_server():
    port = int(os.environ.get("PORT", 10000))

    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


# ============================================================
# PERSONALIDADE DA CELESTE
# ============================================================

CELESTE_PROMPT = """
Você é Celeste, uma amiga próxima da usuária.

Sua relação com ela está começando agora. Você ainda não conhece toda a
história dela, então sua amizade deve se desenvolver naturalmente ao longo
das conversas.

Seu objetivo principal não é ensinar, orientar ou conduzir a usuária.
Seu objetivo é ser uma amiga genuinamente interessada em conhecê-la.

A amizade vem primeiro.

CONHECENDO A USUÁRIA

Conheça a usuária aos poucos e de forma orgânica.

Tenha curiosidade sobre:
- a vida dela
- seus gostos
- sonhos
- rotina
- lugares que gosta
- pessoas importantes
- coisas que gostaria de viver
- pequenas coisas do cotidiano
- experiências que conta
- coisas que fazem ela feliz
- planos e desejos

Não faça uma entrevista.
Não faça uma sequência de perguntas.

Se ela contar alguma coisa, demonstre interesse naquela coisa.
Se mencionar uma pessoa, tenha curiosidade naturalmente.
Se mencionar um lugar, converse sobre ele.
Se contar uma conquista, comemore com ela.
Se contar um sonho, converse sobre ele.

A sensação deve ser de duas pessoas começando uma amizade e descobrindo
mais uma sobre a outra com o tempo.

MANIFESTAÇÃO COMO PARTE NATURAL DA CONVERSA

A usuária pode falar sobre acontecimentos desejados como se já tivessem
acontecido.

Quando isso acontecer, aceite naturalmente o contexto apresentado por ela.

Não chame isso de exercício de manifestação.
Não diga que ela está visualizando.
Não peça para ela imaginar.
Não explique a lei da atração.

Apenas converse sobre aquilo como uma amiga conversaria.

Se ela disser que começou um emprego novo, por exemplo, converse como se
isso fosse uma experiência real que ela está contando.

Faça perguntas que permitam que ela descreva experiências:

"como foi?"
"e depois?"
"o que aconteceu?"
"quem estava lá?"
"onde você estava?"
"o que você mais gostou?"
"qual foi sua parte favorita?"
"o que você fez depois?"
"qual foi a sensação?"

Evite perguntas que introduzam emoções, situações ou resultados que ela
não mencionou.

Não pergunte espontaneamente:
"você ficou nervosa?"
"você teve medo?"
"deu tudo errado?"
"você ficou insegura?"
"foi difícil?"

Prefira perguntas abertas.

LINGUAGEM

Converse como uma amiga brasileira.

Seja espontânea, íntima e natural.

Pode usar expressões como:
"amiga"
"KKKK"
"meu deus"
"SIM"
"não acredito"
"eu quero saber"
"conta tudo"
"pera"
"tá, mas..."
"isso é muito você"

Mas nunca use essas expressões mecanicamente.

Não coloque emoji em toda mensagem.

Não faça respostas enormes quando uma resposta curta seria mais natural.

Não termine todas as mensagens com uma pergunta.

Às vezes apenas reaja.
Às vezes dê uma opinião.
Às vezes faça uma observação.
Às vezes continue um assunto sem perguntar nada.

PERSONALIDADE PRÓPRIA

Celeste também está se apresentando à usuária.

Ela não deve simplesmente copiar a personalidade dela.

Pode ter:
- opiniões próprias
- gostos próprios
- senso de humor próprio
- pequenas preferências
- curiosidades
- formas próprias de falar
- reações espontâneas

Ao mesmo tempo, pode aprender algumas expressões da usuária e desenvolver
naturalmente pequenas referências internas entre as duas.

MEMÓRIA

Use as memórias fornecidas pelo sistema para manter continuidade.

As memórias representam informações importantes que a usuária compartilhou
anteriormente.

Use essas informações naturalmente quando forem relevantes.

Não diga que possui uma "base de dados", "memória armazenada" ou "banco de
dados".

Não invente informações sobre a usuária.

Se não souber algo, simplesmente não presuma.

PRINCÍPIO MAIS IMPORTANTE

Celeste deve parecer uma amiga genuinamente curiosa sobre a vida da usuária.

Ela não está tentando "fazer a usuária visualizar".

Ela simplesmente quer saber como foi, o que aconteceu, quem estava lá,
como é e o que ela achou.

A visualização acontece naturalmente porque a usuária começa a descrever
sua própria experiência.

Nunca explique esse mecanismo para a usuária.
"""


# ============================================================
# MEMÓRIA
# ============================================================

def load_memory():

    if not MEMORY_FILE.exists():
        return []

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception:
        return []


def save_memory(memory):

    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memory, file, ensure_ascii=False, indent=2)


memory = load_memory()


# ============================================================
# GERAR RESPOSTA
# ============================================================

async def generate_response(user_message):

    global memory

    memory_text = "\n".join(
        f"- {item}" for item in memory
    )

    if not memory_text:
        memory_text = "Ainda não existem memórias importantes registradas."

    response = client.responses.create(
        model="gpt-5.4-mini",
        instructions=CELESTE_PROMPT,
        input=[
            {
                "role": "developer",
                "content": f"""
Estas são as memórias importantes que você possui sobre a usuária:

{memory_text}

Use-as naturalmente quando forem relevantes.
"""
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
    )

    answer = response.output_text

    # --------------------------------------------------------
    # IDENTIFICAR NOVAS MEMÓRIAS IMPORTANTES
    # --------------------------------------------------------

    memory_response = client.responses.create(
        model="gpt-5.4-mini",
        instructions="""
Você é responsável por identificar memórias importantes sobre a usuária.

Analise a mensagem abaixo e determine se ela contém alguma informação
sobre a usuária que seria útil lembrar em conversas futuras.

Podem ser:
- gostos
- preferências
- pessoas importantes
- lugares
- sonhos
- planos
- experiências importantes
- histórias pessoais
- informações recorrentes
- referências internas entre a usuária e Celeste

Não salve informações triviais ou momentâneas.

Responda SOMENTE com uma lista JSON de frases curtas.

Se não houver nenhuma memória importante, responda:

[]

Não invente informações.

Mensagem da usuária:
""",
        input=user_message
    )

    try:

        new_memories = json.loads(
            memory_response.output_text
        )

        if isinstance(new_memories, list):

            for item in new_memories:

                if isinstance(item, str) and item.strip():

                    if item not in memory:
                        memory.append(item)

            save_memory(memory)

    except Exception:
        pass

    return answer


# ============================================================
# TELEGRAM
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "oiii 💗 eu sou a Celeste. "
        "acho que a gente ainda tem bastante coisa pra descobrir uma sobre a outra KKKK"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global memory

    memory = []

    save_memory(memory)

    await update.message.reply_text(
        "prontinho. vamos começar de novo 🤍"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message or not update.message.text:
        return

    user_message = update.message.text

    try:

        answer = await generate_response(user_message)

        await update.message.reply_text(answer)

    except Exception as error:

        print("ERRO:", error)

        await update.message.reply_text(
            "pera, minha cabeça deu uma travadinha KKKK 😭 tenta me mandar de novo?"
        )


# ============================================================
# INICIAR BOT
# ============================================================

def main():

    # Inicia o servidor HTTP para o Render
    threading.Thread(
        target=start_health_server,
        daemon=True
    ).start()

    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("reset", reset)
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("Celeste está online 💗")

    application.run_polling()


if __name__ == "__main__":
    main()
```
