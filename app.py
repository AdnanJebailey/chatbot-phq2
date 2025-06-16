from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import os
from google.cloud import bigquery
import csv
from twilio.rest import Client

app = Flask(__name__)
load_dotenv()

# Inicializa cliente BigQuery
bq_client = bigquery.Client()

# Configura dataset e tabela BigQuery
BQ_DATASET = "Base_Interna"
BQ_TABLE = "logs_phq2"

# Perguntas PHQ-2
phq2_questions = [
    "1️⃣ Nos últimos 14 dias, com que frequência você se sentiu desanimado(a), deprimido(a) ou sem esperança?\n\n(0) Nunca\n(1) Vários dias\n(2) Mais da metade dos dias\n(3) Quase todos os dias",
    "2️⃣ Nos últimos 14 dias, com que frequência você teve pouco interesse ou prazer em fazer as coisas?\n\n(0) Nunca\n(1) Vários dias\n(2) Mais da metade dos dias\n(3) Quase todos os dias"
]

# Sessões na memória
sessions = {}

# Busca nome no CSV pelo telefone
def get_name_by_phone(phone_number):
    try:
        with open("telefones.csv", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if f"whatsapp:{row['numero']}" == phone_number:
                    return row["nome"]
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
    return None

# Salva resposta no BigQuery
def save_response_to_bigquery(phone, name, status, preferred_time):
    table_id = f"{bq_client.project}.{BQ_DATASET}.{BQ_TABLE}"
    rows_to_insert = [{
        "phone_number": phone,
        "name": name,
        "status": status,
        "preferred_time": preferred_time
    }]
    errors = bq_client.insert_rows_json(table_id, rows_to_insert)
    if errors:
        print(f"Erro ao inserir no BigQuery: {errors}")

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    from_number = request.form.get("From")
    incoming_msg = request.form.get("Body", "").strip()
    resp = MessagingResponse()
    msg = resp.message()

    session = sessions.get(from_number, {"step": 0, "answers": [], "name": None})

    if incoming_msg.upper() == "RESPONDER" and session["step"] == 0:
        nome = get_name_by_phone(from_number)
        if not nome:
            msg.body("Desculpe, não conseguimos identificar seu nome. Por favor, tente novamente mais tarde.")
            return str(resp)
        session["name"] = nome
        session["step"] = 2
        msg.body(phq2_questions[0])

    elif session["step"] == 2:
        try:
            val = int(incoming_msg)
            if val not in [0, 1, 2, 3]:
                raise ValueError()
            session["answers"].append(val)
            session["step"] = 3
            msg.body(phq2_questions[1])
        except ValueError:
            msg.body("Por favor, responda apenas com 0, 1, 2 ou 3.")

    elif session["step"] == 3:
        try:
            val = int(incoming_msg)
            if val not in [0, 1, 2, 3]:
                raise ValueError()
            session["answers"].append(val)
            score = sum(session["answers"])
            if score > 2:
                msg.body(
                    "📞 Obrigado por responder! Podemos te ligar para entender melhor como você está se sentindo. Qual o melhor horário?\n\n"
                    "1️⃣ Manhã\n2️⃣ Tarde\n3️⃣ Noite"
                )
                session["step"] = 4
            else:
                save_response_to_bigquery(
                    phone=from_number,
                    name=session["name"],
                    status="Não é o perfil",
                    preferred_time=""
                )
                msg.body(
                    "✅ Obrigado por responder! Não identificamos necessidade imediata de acolhimento. "
                    "Se precisar, estamos por aqui.\n\nA Prefeitura de Impulsolândia agradece a sua participação!"
                )
                session = {"step": 0, "answers": [], "name": None}
        except ValueError:
            msg.body(
                "Opa! Não entendi muito bem o que você quis dizer. "
                "Você pode tentar reformular a pergunta ou escrever de outro jeito?"
            )

    elif session["step"] == 4:
        horarios = {"1": "Manhã", "2": "Tarde", "3": "Noite"}
        horario = horarios.get(incoming_msg)
        if horario:
            save_response_to_bigquery(
                phone=from_number,
                name=session["name"],
                status="A entrevistar",
                preferred_time=horario
            )
            msg.body(
                f"📆 Combinado! Entraremos em contato no período da {horario}.\n\n"
                "A Prefeitura de Impulsolândia agradece a sua participação!"
            )
            session = {"step": 0, "answers": [], "name": None}
        else:
            msg.body("Por favor, escolha uma opção válida: 1️⃣ Manhã, 2️⃣ Tarde, 3️⃣ Noite.")

    else:
        msg.body(
            "Opa! Não entendi muito bem o que você quis dizer. "
            "Você pode tentar reformular a pergunta ou escrever de outro jeito?"
        )

    sessions[from_number] = session
    return str(resp)

@app.route("/", methods=["GET"])
def index():
    return "✅ Chatbot PHQ-2 rodando com sucesso no Google Cloud Run!"

@app.route("/send_all", methods=["POST"])
def send_all():
    try:
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_whatsapp_number = "whatsapp:+14155238886"

        client = Client(twilio_sid, twilio_token)

        results = []
        with open("telefones.csv", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                numero = row["numero"]
                nome = row["nome"]
                body = (
                    f"📢 Olá {nome}! A Prefeitura de Impulsolândia quer cuidar de você.\n\n"
                    "Estamos atentos à importância da saúde mental e sabemos que o bem-estar "
                    "emocional faz toda a diferença no dia a dia. Por isso, gostaríamos de fazer algumas "
                    "perguntas rápidas para entender como você tem se sentido ultimamente.\n\n"
                    "Sua participação é voluntária e confidencial. Vamos começar?\n\n"
                    "👉 *Responda com a palavra:* *RESPONDER*"
                )
                try:
                    message = client.messages.create(
                        from_=twilio_whatsapp_number,
                        to=f"whatsapp:{numero}",
                        body=body
                    )
                    results.append({"phone": numero, "success": True})
                except Exception as e:
                    results.append({"phone": numero, "success": False, "error": str(e)})

        return {"status": "done", "results": results}, 200

    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
