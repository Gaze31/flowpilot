const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.FLOWPILOT_API_KEY;

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  if (!API_KEY) {
    return Response.json({ error: "FLOWPILOT_API_KEY is not set" }, { status: 500 });
  }

  const { id } = await params;
  const res = await fetch(`${API_URL}/workflows/${encodeURIComponent(id)}/runs`, {
    method: "POST",
    headers: { "X-API-Key": API_KEY },
  });

  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const res = await fetch(`${API_URL}/workflows/${encodeURIComponent(id)}/runs`, { cache: "no-store" });
  return new Response(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}