# BankTrack Edge — Supabase Edge Functions

Traducción fiel del backend Python de BankTrack a **TypeScript/Deno** para ejecutarse como **Supabase Edge Functions**.

## Estructura

```
edge/
├── supabase/
│   └── functions/
│       ├── _shared/           ← Módulos compartidos
│       │   ├── types.ts       ← Interfaces del dominio
│       │   ├── parser.ts      ← Parseo de correos bancarios BVC
│       │   ├── comisiones.ts  ← Cálculo de comisiones
│       │   ├── tasas.ts       ← Consulta de tasas BCV (USD/EUR)
│       │   ├── gmail.ts       ← Lector de Gmail via REST API
│       │   ├── supabase-client.ts ← Cliente Supabase + operaciones CRUD
│       │   └── alertas.ts     ← Verificación de límite mensual
│       ├── procesar-correos/  ← Edge Function principal (cron)
│       │   └── index.ts
│       └── api/               ← Edge Function REST API (Hono)
│           └── index.ts
├── deno.json
└── README.md
```

## Estado

Desplegado en el proyecto `nabmpdxjcivsqiygezxs`. Corre solo:

| Pieza | Dónde |
|---|---|
| `procesar-correos` | Edge Function, `verify_jwt = true`, invocada por `pg_cron` cada 5 min |
| `api` | Edge Function, `verify_jwt = false` (usa su propio Bearer `API_KEY`) |
| Token Gmail | Tabla `gmail_tokens` (id=1), se auto-refresca |
| Secrets | `supabase secrets list` |

- API: `https://nabmpdxjcivsqiygezxs.supabase.co/functions/v1/api`
- Worker: `https://nabmpdxjcivsqiygezxs.supabase.co/functions/v1/procesar-correos`

## Variables de entorno requeridas

Los nombres `SUPABASE_*` están reservados por la plataforma, así que los secrets
usan el prefijo `SB_`.

```env
# Supabase
SB_URL=https://tu-proyecto.supabase.co
SB_SERVICE_ROLE_KEY=eyJ...

# Gmail OAuth2
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GMAIL_LABEL=BVC                      # Opcional, default: BVC

# Tasas de cambio
DOLAR_API_URL=https://ve.dolarapi.com/v1/dolares/oficial
EURO_API_URL=https://ve.dolarapi.com/v1/euros/oficial  # Opcional

# API
API_KEY=tu-api-key-secreto
```

## Tabla necesaria en Supabase

Ya creada (migración `crear_gmail_tokens`). Una sola fila, id=1, con RLS activo
y sin policies: solo `service_role` la ve.

```sql
CREATE TABLE public.gmail_tokens (
  id             INTEGER     PRIMARY KEY DEFAULT 1,
  access_token   TEXT        NOT NULL,
  refresh_token  TEXT        NOT NULL,
  expiry         TIMESTAMPTZ NOT NULL,
  actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT gmail_tokens_fila_unica CHECK (id = 1)
);
ALTER TABLE public.gmail_tokens ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.gmail_tokens FROM anon, authenticated;
```

Si el `refresh_token` se revoca (cambio de contraseña de Google, app
desautorizada), hay que re-sembrar la fila: correr `python main.py` local una vez
para regenerar `credentials/token.json` y volcar `token` / `refresh_token` /
`expiry` en la tabla.

## Desarrollo local

```bash
# Instalar Supabase CLI
npm install -g supabase

# Correr funciones localmente
supabase functions serve --env-file .env
```

## Despliegue

```bash
cd edge
supabase functions deploy procesar-correos
supabase functions deploy api
```

`verify_jwt` e `import_map` salen de `supabase/config.toml`. El import map vive
en `supabase/functions/deno.json` — el CLI no lee el `deno.json` de la raíz de
`edge/`, y `hono/` debe mapearse a `npm:/hono@4/` (con la barra después de
`npm:`) o el bundler no resuelve `hono/cors`.

## Cron

Ya agendado (migración `agendar_cron_procesar_correos`), job `procesar-correos`,
`*/5 * * * *`. La clave de invocación está en Vault como `edge_invoke_key`.

```sql
-- ver estado
SELECT * FROM cron.job;
SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 10;

-- pausar / reanudar
UPDATE cron.job SET active = false WHERE jobname = 'procesar-correos';
```

## Notas

- **Traducción fiel**: misma lógica, mismos regex, mismo flujo que el backend Python.
- **Sin cambios arquitectónicos**: `procesar_correos()` es UNA sola Edge Function.
- **Token Gmail**: se almacena en la tabla `gmail_tokens` (id=1) en vez de archivos locales.
- **Comisiones**: 0.3% mínimo 2 Bs para pagomóvil, declarada para transferencias, exonerada para servicios.
- **Zona horaria**: el Edge Runtime corre en UTC, no en hora local como el backend
  Python. `_shared/fecha.ts` aplica UTC-4 fijo (Venezuela, sin DST) al parsear
  fechas de correos y al calcular `mes_corte` y "¿es la tasa de hoy?".
- **Rutas de la API**: Supabase monta la función bajo `/api`, por eso Hono usa
  `basePath("/api")`. Sin eso todas las rutas dan 404.
