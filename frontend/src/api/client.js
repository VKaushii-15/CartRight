import axios from "axios";

const api = axios.create({
  baseURL: '/',
  timeout: 8000,
  headers: { "Content-Type": "application/json" },
});

export async function fetchCatalog(q) {
  const res = await api.get(`/catalog${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  return res.data;
}

export async function fetchProduct(id) {
  const res = await api.get(`/catalog/${id}`);
  return res.data;
}

export async function getCart(sessionId) {
  const res = await api.get(`/cart/${sessionId}`);
  return res.data;
}

export async function addToCart(sessionId, product_id, quantity = 1) {
  const res = await api.post(`/cart/${sessionId}/add`, { product_id, quantity });
  return res.data;
}

export async function applyDiscount(sessionId, discount_percent) {
  const res = await api.post(`/cart/${sessionId}/apply_discount?discount_percent=${discount_percent}`);
  return res.data;
}

export async function checkout(sessionId) {
  const res = await api.post(`/cart/${sessionId}/checkout`);
  return res.data;
}

export async function sendChatMessage(sessionId, message) {
  const res = await api.post(`/chat/${sessionId}`, { message });
  return res.data;
}

export default api;
