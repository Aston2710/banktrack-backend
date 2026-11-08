import { assertEquals } from "jsr:@std/assert@1";
import { parsearCorreo } from "../_shared/parser.ts";
import { resolverComision } from "../_shared/comisiones.ts";

const ASUNTO = "Notificación de uso de su tarjeta del Venezolano de Crédito";
const cuerpo = (resto: string) =>
  "Estimado cliente, le notificamos que hemos registrado una transacción de consumo por un monto de " +
  "Bs 29.531,37 realizada con su tarjeta No. ****-****-**12-1724, el día 05/11/2026 a las 13:42:35 " +
  `en el comercio AREA FOOD CA CCS NOROESTE ${resto}. Para mayor información comuníquese al 0501-mibanco.`;

Deno.test("tarjeta rechazada (correo real 05/11) → rechazado, sin comisión", () => {
  const d = parsearCorreo(ASUNTO, cuerpo("VEla cual fue rechazada"));
  assertEquals(d.tipo, "rechazado");
  assertEquals(d.subtipo, "tarjeta");
  assertEquals(d.comercio, "AREA FOOD CA CCS NOROESTE");
  assertEquals(d.referencia, null);
  assertEquals(resolverComision(d).monto, 0);
});

Deno.test("tarjeta aprobada → salida con código de aprobación", () => {
  const d = parsearCorreo(ASUNTO, cuerpo("VE la cual fue aprobada con código 431375"));
  assertEquals(d.tipo, "salida");
  assertEquals(d.subtipo, "tarjeta");
  assertEquals(d.monto_bs, 29531.37);
  assertEquals(d.comercio, "AREA FOOD CA CCS NOROESTE");
  assertEquals(d.referencia, "431375");
});
