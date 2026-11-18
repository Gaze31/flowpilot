const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Reads go through here too, so the browser only ever talks to this site (https).
export async function GET() {
  const res = await fetch(`${API_URL}/workflows`, { cache: "no-store" });
  return new Response(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}