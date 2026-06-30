import { Suspense } from "react";
import LoginPanel from "@/components/auth/LoginPanel";

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginPanel />
    </Suspense>
  );
}
