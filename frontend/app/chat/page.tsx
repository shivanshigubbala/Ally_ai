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
  clearProfile,
  getProfile,
  getUserId,
  type PatientProfile,
} from "@/lib/patient";

export default function ChatPage() {
  const router = useRouter();
  const [session, setSession] = useState<{
    profile: PatientProfile;
    userId: string;
  } | null>(null);
  const [ready, setReady] = useState(false);
  const [tab, setTab] = useState<SidebarTab>("chat");

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
    appointmentPending,
    appointmentBooked,
    doctorReady,
    doctorMessages,
    doctorThinking,
    consultationActive,
    sendText,
    selectDoctor,
    resolveSlot,
    resolveLabDecision,
    markInboxRead,
    startConsultation,
    sendDoctorMessage,
    unreadCount,
    addSampleReport,
  } = useChatSocket(userId);

  useEffect(() => {
    const validateSession = () => {
      const p = getProfile();
      const uid = getUserId();
      const nextSession = p && uid ? { profile: p, userId: uid } : null;

      setSession(nextSession);
      setReady(true);

      if (!nextSession) {
        router.replace("/login");
      }
    };

    validateSession();

    const handlePageShow = (event: PageTransitionEvent) => {
      if (event.persisted) {
        validateSession();
      }
    };

    window.addEventListener("pageshow", handlePageShow);
    return () => window.removeEventListener("pageshow", handlePageShow);
  }, [router]);

  useEffect(() => {
    if (doctorReady) {
      setTab("appointments");
    }
  }, [doctorReady]);

  const logout = () => {
    clearProfile();
    window.localStorage.removeItem("token");
    router.replace("/login");
  };

  if (!ready || !profile) return null;

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar
        active={tab}
        onChange={setTab}
        patientName={profile.name}
        unreadCount={unreadCount}
      />

      <main className="flex-1 flex flex-col min-h-0">
        {tab === "chat" && (
          <>
            <ChatHeader connected={connected} doctorName={null} />

            <ChatThread
              messages={messages}
              cards={cards}
              thinking={thinking}
              onSelectDoctor={selectDoctor}
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

        {tab === "reports" && (
          <LabReportsPanel reports={reports} onAddSampleReport={addSampleReport} />
        )}

        {tab === "appointments" && (
          <AppointmentsPanel
            doctorName={doctorName}
            booked={appointmentBooked}
            slotCards={cards.filter((card) => card.kind === "slot_select")}
            labCards={cards.filter((card) => card.kind === "lab_notification")}
            onSelectSlot={resolveSlot}
            onLabDecision={resolveLabDecision}
            doctorReady={doctorReady}
            doctorMessages={doctorMessages}
            doctorThinking={doctorThinking}
            consultationActive={consultationActive}
            onStartConsultation={startConsultation}
            onSendDoctorMessage={sendDoctorMessage}
          />
        )}

        {tab === "profile" && (
          <ProfilePanel profile={profile} reports={reports} onLogout={logout} />
        )}
      </main>
    </div>
  );
}
