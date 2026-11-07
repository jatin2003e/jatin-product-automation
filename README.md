# Digital Product Automation

**Webhook ingestion, event processing and email fulfillment**

Author: [jatin2003e](https://github.com/jatin2003e)

## Features

See application screens and API endpoints in `app.py`. This is a working, self-hostable MVP intended as a strong foundation for a commercial product. Production deployment requires domain/TLS, external backups, monitoring, and a security review.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Set strong SECRET_KEY and ADMIN_PASSWORD in .env
python app.py
```

Open http://localhost:5000. For Docker: `docker compose up --build`.

## Testing

```bash
pytest -q
```

## Security and operations

- Never commit `.env`, customer files, private keys, or databases.
- Set unique secrets and serve behind HTTPS in production.
- Change default secrets before exposure to the internet.
- Implement rate limiting, backups, audit logs, and external transactional email as appropriate.
- Only distribute content you own or have rights to sell.

## License

MIT; see `LICENSE`.

## Signed webhook example

Send JSON `{"id":"order-123","type":"order.paid","email":"customer@example.com","product":"Creator Kit","download_url":"https://example.com/secure-download"}` with `X-Webhook-Signature` set to the hex HMAC-SHA256 digest of the **raw JSON request bytes** using `WEBHOOK_SECRET`. Duplicate event IDs are ignored. Admin reviews and triggers SMTP fulfillment in the dashboard. For fully automatic delivery, add a background job worker and provider-specific signature validation, retry policies and dead-letter queue.
