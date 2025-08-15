export type Idea = { title: string; logline: string; genre?: string; tone?: string };

export async function runCreatorAgent(idea: Idea) {
  const url = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/pitch/generate`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(idea),
  });
  if (!res.ok) throw new Error(`Agent call failed: ${res.status}`);
  return res.json();
}
