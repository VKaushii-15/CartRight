export function genSessionId() {
  let id = localStorage.getItem("session_id");
  if (!id) {
    id = "sess_" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem("session_id", id);
  }
  return id;
}
