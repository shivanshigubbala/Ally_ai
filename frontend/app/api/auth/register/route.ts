import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://backend:8000";
    const response = await fetch(`${backendUrl}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const text = await response.text();
    let data;
    try {
      data = text ? JSON.parse(text) : { ok: false, detail: "Empty response from auth service" };
    } catch {
      data = { ok: false, detail: text || `Auth service returned status ${response.status}` };
    }

    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    return NextResponse.json(
      { ok: false, detail: error.message || "Internal server error" },
      { status: 500 }
    );
  }
}
