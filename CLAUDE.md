# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

BankTrack Backend is a scheduled Python daemon that monitors a Gmail inbox for Venezuelan bank email notifications (Banco Venezolano de Crédito), parses them with regex, and stores structured transaction records in Supabase (PostgreSQL). It is **not** an HTTP API — it runs as a background worker on a configurable interval.

## Setup & Running

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Unix

pip install -r requirements.txt

# Copy and fill in .env (see config.py for required variables)
python main.py
```

Required `.env` variables: `SUPABASE_URL`, `SUPABASE_KEY`, `GMAIL_CREDENTIALS_PATH`, `GMAIL_TOKEN_PATH`, `GMAIL_LABEL`, `INTERVALO_MINUTOS`, `DOLAR_API_URL`.

Gmail requires an OAuth credentials file at the path set in `GMAIL_CREDENTIALS_PATH`. The first run opens a browser for approval; subsequent runs use the cached token.

## Running Tests

```bash
python test.py          # full suite: parser, comisiones, enriquecimiento
python test_parser.py   # parser-only with simulated email bodies
```

No test framework is used — tests are plain Python functions called from `if __name__ == "__main__"` blocks.

## Architecture

### Main processing loop (`main.py`)

```
Initialize config
  → procesar_correos() every INTERVALO_MINUTOS minutes
      → gmail_reader: fetch unread emails from label
      → parser: identify type + extract fields via regex
      → dolar_api: fetch BCV exchange rate
      → comisiones: compute commission based on type
      → supabase_client: insert or enrich existing record
      → gmail_reader: mark email as read
      → alertas: check monthly spending vs limit
```

### Key modules

| Module | Responsibility |
|---|---|
| `config.py` | Loads and validates `.env`; exports all config constants |
| `gmail_reader.py` | OAuth2 auth, fetches unread threads from Gmail label, decodes base64 bodies |
| `parser.py` | ~1400 lines of regex parsing; routes to one of 7 type-specific functions |
| `supabase_client.py` | All DB operations: insert, duplicate check, enrichment, monthly summaries |
| `comisiones.py` | Commission rules by transaction type |
| `alertas.py` | Monthly spending limit alerts at configurable % threshold |
| `dolar_api.py` | Hits `ve.dolarapi.com` for BCV USD/Bs exchange rate |

### Transaction types

`recibido` · `enviado` · `transferencia` · `pago_inmediato` · `tarjeta` · `servicio` · `rechazado`

Each type has a dedicated parse function in `parser.py` and commission rule in `comisiones.py`.

### Duplicate handling

When a transaction with the same `referencia` already exists, `supabase_client.py` enriches the existing record rather than inserting a duplicate.

### Database tables (Supabase)

- **transacciones** — one row per parsed transaction; dual-currency fields (`monto_bs`, `monto_usd`, `tasa_dolar`)
- **configuracion** — runtime settings (`limite_mensual_bs`, `alerta_porcentaje`)
- **cierres_mensuales** — monthly aggregate summaries

No ORM or migrations — uses the Supabase Python client directly.
