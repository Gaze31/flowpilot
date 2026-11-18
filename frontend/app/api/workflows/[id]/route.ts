const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.FLOWPILOT_API_KEY;

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  if (!API_KEY) {
    return Response.json({ error: "FLOWPILOT_API_KEY is not set" }, { status: 500 });
  }

  const { id } = await params;
  const body = await request.text();

  const res = await fetch(`${API_URL}/workflows/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body,
  });

  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}