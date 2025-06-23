// frontend/src/lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function likeMovie(user_id: string, movie_title: string) {
  const res = await fetch(`${API_URL}/like`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id, movie_title }),
  });
  if (!res.ok) throw new Error("Failed to like movie");
  return res.json();
}

export async function trainModel() {
  const res = await fetch(`${API_URL}/train`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Training failed");
  return res.json();
}

export async function getRecommendations(user_id: string, n: number = 10) {
  const res = await fetch(`${API_URL}/recommend/${user_id}?n=${n}`);
  if (!res.ok) throw new Error("Failed to get recommendations");
  return res.json();
}
