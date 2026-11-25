// Hook PostToolUse (TodoWrite / TaskCreate / TaskUpdate): passo N/M real, lido da lista de tarefas do Claude.
import { loadState, saveState } from "../lib/core.mjs";
import { readStdin } from "./io.mjs";

const input = await readStdin();
const sid = input.session_id;
const tool = input.tool_name;
const ti = input.tool_input || {};
const st = loadState(sid);
st.tasks = st.tasks || {};

function taskId(resp) {
  if (!resp) return null;
  if (typeof resp === "object") {
    const id = resp.task?.id ?? resp.id ?? resp.taskId;
    if (id != null) return String(id);
    resp = JSON.stringify(resp);
  }
  const m = String(resp).match(/#?(\d+)/);
  return m ? m[1] : null;
}

if (tool === "TodoWrite" && Array.isArray(ti.todos)) {
  const todos = ti.todos;
  st.total = todos.length;
  st.done = todos.filter((t) => t.status === "completed").length;
  const cur = todos.find((t) => t.status === "in_progress") || todos.find((t) => t.status !== "completed");
  st.current = cur ? (cur.content || cur.activeForm) : null;
} else if (tool === "TaskCreate") {
  // primeira tarefa nova depois do aviso de módulo zera a lista do playbook
  if (!st.fromTasks) { st.tasks = {}; st.fromTasks = true; }
  const id = taskId(input.tool_response) || String(Object.keys(st.tasks).length + 1);
  st.tasks[id] = { subject: ti.subject || ti.description || `tarefa ${id}`, status: "pending" };
} else if (tool === "TaskUpdate") {
  const id = String(ti.taskId ?? ti.id ?? "");
  if (id && st.tasks[id]) {
    if (ti.status) st.tasks[id].status = ti.status;
    if (ti.subject) st.tasks[id].subject = ti.subject;
  }
  if (ti.status === "deleted" && st.tasks[id]) delete st.tasks[id];
}

if (tool !== "TodoWrite" && st.fromTasks) {
  const list = Object.values(st.tasks);
  st.total = list.length;
  st.done = list.filter((t) => t.status === "completed").length;
  const cur = list.find((t) => t.status === "in_progress") || list.find((t) => t.status !== "completed");
  st.current = cur ? cur.subject : null;
}

saveState(sid, st);
