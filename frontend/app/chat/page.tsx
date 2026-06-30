"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import Sidebar, { type SidebarTab } from "@/components/sidebar/Sidebar";
import AppointmentsPanel from "@/components/sidebar/AppointmentsPanel";
import ProfilePanel from "@/components/sidebar/ProfilePanel";
import ChatHeader from "@/components/chat/ChatHeader";
import ChatThread from "@/components/chat/ChatThread";
import ChatComposer from "@/components/chat/ChatComposer";
import InboxPanel from "@/components/inbox/InboxPanel";
import LabReportsPanel from "@/components/reports/LabReportsPanel";

import { useChatSocket } from "@/hooks/useChatSocket";

import {
  getProfile,
  getUserId,
  clearProfile,
  type PatientProfile,
} from "@/lib/patient";

export default function ChatPage() {
  const router = useRouter();

  const [session, setSession] = useState<{
    profile: PatientProfile;
    userId: string;
  } | null>(null);

  const [tab, setTab] = useState<SidebarTab>("chat");

  // Re-checks the saved profile and redirects to /login if it's missing.
  // Called both on first mount and whenever the page is restored from the
  // browser's back/forward cache (bfcache) — without the pageshow listener,
  // clicking Back then Forward can show this page from memory without ever
  // re-running this check, letting a logged-out user land back in chat.
  const validateSession = () => {
    const profile = getProfile();
    const uid = getUserId();

    if (!profile || !uid) {
      router.replace("/login");
      return;
    }

    setSession({ profile, userId: uid });
  };

  useEffect(() => {
    validateSession();

    const handlePageShow = (event: PageTransitionEvent) => {
      // event.persisted is true when the page was restored from bfcache
      // rather than freshly loaded — this is exactly the back/forward case.
      if (event.persisted) {
        validateSession();
      }
    };

    window.addEventListener("pageshow", handlePageShow);
    return () => window.removeEventListener("pageshow", handlePageShow);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  const logout = () => {
    clearProfile();

    localStorage.removeItem("token");

    router.replace("/login");
  };

  const profile = session?.profile ?? null;
  const userId = session?.userId ?? null;

  const {
    messages,
    cards,
    inbox,
    reports,
    connected,
    thinking,
    doctorName,
    sendText,
    resolveSlot,
    resolveLabDecision,
    markInboxRead,
    unreadCount,
  } = useChatSocket(userId);

  if (!profile) return null;

  return (
    <div className="flex h-screen bg-gray-50">

      <Sidebar
        active={tab}
        onChange={setTab}
        patientName={profile.name}
        unreadCount={unreadCount}
      />

      <main className="flex-1 flex flex-col">

        {tab === "chat" && (
          <>
            <ChatHeader
              connected={connected}
              doctorName={doctorName}
            />

            <ChatThread
              messages={messages}
              cards={cards}
              thinking={thinking}
              onSelectSlot={resolveSlot}
              onLabDecision={resolveLabDecision}
            />

            <ChatComposer
              onSend={sendText}
              disabled={!connected}
            />
          </>
        )}

        {tab === "inbox" && (
          <InboxPanel
            notifications={inbox}
            onMarkRead={markInboxRead}
            onViewReports={() => setTab("reports")}
          />
        )}

        {tab === "reports" && (
          <LabReportsPanel
            reports={reports}
          />
        )}

        {tab === "appointments" && (
          <AppointmentsPanel
            doctorName={doctorName}
            booked={Boolean(doctorName)}
          />
        )}

        {tab === "profile" && (
          <ProfilePanel
            profile={profile}
            reports={reports}
            onLogout={logout}
          />
        )}

      </main>
    </div>
  );
}