-- Binance, Etapa A (lectura en seco). Ver control_de_gastos/docs/plan-binance.md.
-- No toca ninguna tabla existente.

-- 1. Copia fiel de cada operación finalizada que devuelve Binance. Solo service_role.
create table public.binance_operaciones (
  id           bigint generated always as identity primary key,
  tipo         text        not null check (tipo in ('p2p', 'pay', 'deposito', 'retiro')),
  id_binance   text        not null,
  fecha        timestamptz not null,
  direccion    text        not null check (direccion in ('entrada', 'salida')),
  activo       text        not null,
  cantidad     numeric     not null check (cantidad >= 0),
  comision     numeric     not null default 0 check (comision >= 0),
  monto_fiat   numeric,
  fiat         text,
  datos        jsonb       not null,
  leido_en     timestamptz not null default now(),
  unique (tipo, id_binance)
);
create index binance_operaciones_fecha_idx on public.binance_operaciones (fecha);
alter table public.binance_operaciones enable row level security;
revoke all on public.binance_operaciones from anon, authenticated;

-- Inmutable: una vez leída, una operación no se modifica ni se borra (salvo el dueño de la BD).
create function public.binance_operaciones_inmutable() returns trigger
language plpgsql as $$
begin
  raise exception 'binance_operaciones es de solo inserción';
end $$;
create trigger binance_operaciones_inmutable
  before update or delete on public.binance_operaciones
  for each row execute function public.binance_operaciones_inmutable();

-- 2. Estado e interruptores de la sincronización (fila única). La app solo lee.
create table public.binance_sincronizacion (
  id                 integer     primary key default 1 check (id = 1),
  activa             boolean     not null default false,   -- interruptor general
  etapa              text        not null default 'A' check (etapa in ('A', 'B', 'C')),
  desde              timestamptz not null default '2026-05-01T00:00:00-04:00',
  cursores           jsonb       not null default '{}'::jsonb,
  en_curso_desde     timestamptz,
  ultima_ejecucion   timestamptz,
  ultimo_exito       timestamptz,
  resultado          text,       -- ok | error | clave_insegura | sin_clave | region | limite
  mensaje            text,
  fallos_seguidos    integer     not null default 0,
  saldo_binance_usdt numeric,
  saldo_en           timestamptz
);
insert into public.binance_sincronizacion (id) values (1);
alter table public.binance_sincronizacion enable row level security;
revoke all on public.binance_sincronizacion from anon, authenticated;
grant select on public.binance_sincronizacion to anon;
create policy anon_lee_binance_sincronizacion on public.binance_sincronizacion
  for select to anon using (true);

-- 3. Bloqueo: una sola ejecución a la vez. Un bloqueo de más de 10 min se da por muerto.
create function public.binance_tomar_bloqueo() returns boolean
language sql security definer set search_path = public as $$
  update public.binance_sincronizacion
     set en_curso_desde = now()
   where id = 1
     and activa
     and (en_curso_desde is null or en_curso_desde < now() - interval '10 minutes')
  returning true;
$$;
create function public.binance_soltar_bloqueo() returns void
language sql security definer set search_path = public as $$
  update public.binance_sincronizacion set en_curso_desde = null where id = 1;
$$;
revoke all on function public.binance_tomar_bloqueo() from public, anon, authenticated;
revoke all on function public.binance_soltar_bloqueo() from public, anon, authenticated;
revoke all on function public.binance_operaciones_inmutable() from public, anon, authenticated;
grant execute on function public.binance_tomar_bloqueo(), public.binance_soltar_bloqueo() to service_role;
