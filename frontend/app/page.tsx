"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getProfile } from "@/lib/patient";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    const profile = getProfile();
    router.replace(profile ? "/chat" : "/login");
  }, [router]);

  return null;
}