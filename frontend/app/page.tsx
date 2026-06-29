import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gray-100 px-6">
      <h1 className="text-5xl font-bold text-blue-700 mb-4">
        Ally AI
      </h1>

      <p className="text-lg text-gray-600 mb-8 text-center">
        Hospital Service Agent Proof of Concept
      </p>

      <Link
        href="/chat"
        className="rounded-lg bg-blue-600 px-6 py-3 text-white font-semibold hover:bg-blue-700 transition"
      >
        Start Chat
      </Link>
    </main>
  );
}