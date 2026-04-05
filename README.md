# SESMailer

Wrapper leve sobre o Amazon SES para envio de e-mails em projetos Python. Otimizado para AWS Lambda.

## Instalacao

```bash
uv add git+https://github.com/kauelima21/SESMailer.git
```

## Uso basico

```python
from sesmailer import SESMailer

mailer = SESMailer()
mailer.set_from("no-reply@example.com", from_name="Minha App")
mailer.add_address("destinatario@example.com", address_name="Joao")
mailer.Subject = "Bem-vindo"
mailer.Body = "Ola, Joao!"
mailer.send()
```

### E-mail HTML

```python
mailer = SESMailer()
(
    mailer
    .set_from("no-reply@example.com")
    .add_address("user@example.com")
    .is_html(True)
)
mailer.Subject = "Newsletter"
mailer.Body = "<h1>Novidades</h1><p>Confira as atualizacoes.</p>"
mailer.AltBody = "Novidades - Confira as atualizacoes."
mailer.send()
```

### CC, BCC e anexos

```python
mailer = SESMailer()
(
    mailer
    .set_from("no-reply@example.com")
    .add_address("principal@example.com")
    .add_cc("copia@example.com")
    .add_bcc("oculto@example.com")
    .add_attachment("/tmp/relatorio.pdf", filename="relatorio.pdf")
)
mailer.Subject = "Relatorio mensal"
mailer.Body = "Segue em anexo o relatorio."
mailer.send()
```

## Uso em AWS Lambda

O construtor aceita um `ses_client` para reutilizar a conexao entre invocacoes, evitando overhead de cold start:

```python
import boto3
from sesmailer import SESMailer

# Cliente criado fora do handler = reutilizado entre invocacoes
ses_client = boto3.client("ses", region_name="us-east-1")

def handler(event, context):
    mailer = SESMailer(ses_client=ses_client)
    mailer.set_from("no-reply@example.com")
    mailer.add_address(event["email"])
    mailer.Subject = "Confirmacao"
    mailer.Body = "Seu pedido foi confirmado."
    mailer.send()
```

## API

| Metodo | Descricao |
|---|---|
| `SESMailer(ses_client=None)` | Cria instancia. Aceita um `boto3.client("ses")` existente. |
| `.set_from(email, from_name=None)` | Define o remetente. |
| `.add_address(email, address_name=None)` | Adiciona destinatario (To). |
| `.add_cc(email, address_name=None)` | Adiciona copia (CC). |
| `.add_bcc(email, address_name=None)` | Adiciona copia oculta (BCC). |
| `.add_reply_to(email, address_name=None)` | Adiciona endereco de resposta (Reply-To). |
| `.add_attachment(file_path, filename=None)` | Anexa arquivo. |
| `.is_html(bool)` | Define se o corpo e HTML. |
| `.send()` | Envia o e-mail via SES. Levanta `ClientError` em caso de falha. |

Todos os metodos de configuracao retornam `self`, permitindo encadeamento.

## Tratamento de erros

O metodo `send()` propaga `botocore.exceptions.ClientError` em caso de falha, permitindo tratamento adequado pelo chamador:

```python
from botocore.exceptions import ClientError

try:
    mailer.send()
except ClientError as e:
    print(f"Falha ao enviar: {e}")
```

## Testes

```bash
uv sync --group dev
uv run pytest tests/ -v
```
