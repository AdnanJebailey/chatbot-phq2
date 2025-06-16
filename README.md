# 🤖 chatbot-phq2

Chatbot automatizado via WhatsApp para envio e coleta de informações utilizando a escala PHQ-2. Desenvolvido com Flask, Twilio e integrado ao Google Cloud Run e BigQuery.

---

## 📦 Visão Geral

Este projeto envia mensagens via WhatsApp para usuários cadastrados no sandbox da Twilio, coleta suas respostas e armazena os dados em uma tabela do BigQuery. O deploy da aplicação foi realizado via Google Cloud Run utilizando um container Docker.

---

## ⚙️ Configuração

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/chatbot-phq2.git
cd chatbot-phq2
```
---

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Preencha os campos com:

```bash
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
```

### 3. Configuração do Google Cloud

O deploy foi realizado via Google Cloud Run.

A aplicação é containerizada com Docker.

As credenciais de acesso ao BigQuery são passadas utilizando a flag:

```bash
--service-account=model-argon-443519-c1@appspot.gserviceaccount.com.
```
### 4. 🚀 Executando o Fluxo

O endpoint principal para iniciar o fluxo de mensagens é:

```bash
POST https://<sua-url-cloud-run>/send_all
```

Este endpoint irá:

Ler os números de telefone contidos em um arquivo telefones.csv;

Enviar mensagens via WhatsApp utilizando a API da Twilio (apenas números previamente cadastrados no sandbox);

Coletar e registrar as respostas na tabela do BigQuery.

### 5. 📝 Considerações

Certifique-se de que os números de telefone estão registrados no sandbox do Twilio antes de iniciar o fluxo.

O projeto utiliza o Flask, Twilio, google-cloud-bigquery e python-dotenv para orquestrar todo o funcionamento.
