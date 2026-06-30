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
import { getProfile, getUserId, type PatientProfile } from "@/lib/patient";

export default function ChatPage() {
  const router = useRouter();
  const [session] = useState<{
    profile: PatientProfile;
    userId: string;
  } | null>(() => {
    const p = getProfile();
    const uid = getUserId();
    return p && uid ? { profile: p, userId: uid } : null;
  });
  const [tab, setTab] = useState<SidebarTab>("chat");

  useEffect(() => {
    if (!session) {
      router.replace("/");
    }
  }, [session, router]);

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
    <div className="flex h-screen bg-white">
      <Sidebar
        active={tab}
        onChange={setTab}
        patientName={profile.name}
        unreadCount={unreadCount}
      />

      <main className="flex-1 flex flex-col">
        {tab === "chat" && (
          <>
            <ChatHeader connected={connected} doctorName={doctorName} />
            <ChatThread
              messages={messages}
              cards={cards}
              thinking={thinking}
              onSelectSlot={resolveSlot}
              onLabDecision={resolveLabDecision}
            />
            <ChatComposer onSend={sendText} disabled={!connected} />
          </>
        )}

        {tab === "inbox" && (
          <InboxPanel
            notifications={inbox}
            onMarkRead={markInboxRead}
            onViewReports={() => setTab("reports")}
          />
        )}

        {tab === "reports" && <LabReportsPanel reports={reports} />}

        {tab === "appointments" && (
          <AppointmentsPanel
            doctorName={doctorName}
            booked={Boolean(doctorName)}
          />
        )}

        {tab === "profile" && <ProfilePanel profile={profile} />}
      </main>
    </div>
  );
}