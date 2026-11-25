// Entrada/saída comum dos hooks: JSON pela stdin, JSON pela stdout.
export async function readStdin() {
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  try { return JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}"); } catch { return {}; }
}

export function emit(obj) {
  process.stdout.write(JSON.stringify(obj));
}
