// Plano da chave (engine/REGRAS-ACESSO-E-SIGILO.md e FLUXOS-POR-PLANO-E-NOTAS.md): vip | membro.
// Lido de ~/.arkos/licenca.txt sem conferir a assinatura (o segredo só existe no servidor da base, que confere
// a cada consulta). Aqui só escolhe o catálogo de fluxos, o limite B e o bloqueio de tema; sem licença = membro.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

export function planoLocal(arq = join(process.env.ARKOS_HOME || join(homedir(), ".arkos"), "licenca.txt")) {
  try {
    const partes = readFileSync(arq, "utf8").trim().split(".");
    if (partes.length !== 3 || partes[0] !== "ARK1") return "membro";
    const p = JSON.parse(Buffer.from(partes[1].replace(/-/g, "+").replace(/_/g, "/"), "base64").toString("utf8"));
    return p && p.plano === "vip" ? "vip" : "membro";
  } catch { return "membro"; }
}

// pedido do membro em área do plano VIP (mesma lista de engine/fluxos/acesso.mjs e do servidor da base)
export const TEMA_VIP = /(\bvsls?\b|video ?sales ?letter|advertorial|pre-?sell|\bugc\b|tiktok ?shop|\be-?commerce\b|loja (virtual|online)|\bshopify\b|mercado ?livre|\bshopee\b|marketplace|dropship)/i;
export const MSG_VIP = "Isso faz parte do plano VIP.";
