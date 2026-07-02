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
    consultationChart,
  } = useChatSocket(userId);
  const activeTab: SidebarTab = tab;

  const handleStartConsultation = () => {
    setTab("appointments");
    startConsultation();
  };

  useEffect(() => {
    if (doctorReady) {
      setTab("appointments");
    }
  }, [doctorReady]);

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

  const logout = () => {
    clearProfile();
    window.localStorage.removeItem("token");
    router.replace("/login");
  };

  if (!ready || !profile) return null;

  return (
    <div className="h-screen overflow-hidden bg-[#c9edf2] px-4 py-4 sm:px-6 lg:px-8">
      <div className="mx-auto grid h-[calc(100vh-2rem)] max-w-[1600px] gap-4 lg:grid-cols-[16rem_1fr]">
        <Sidebar
          active={activeTab}
          onChange={setTab}
          patientName={profile.name}
          unreadCount={unreadCount}
        />

        <main className="flex min-h-0 flex-col overflow-hidden rounded-[2rem] border border-white/70 bg-white/88 shadow-[0_30px_100px_rgba(15,23,42,0.12)] backdrop-blur">
          {activeTab === "chat" && (
            <div className="flex min-h-0 flex-1 flex-col">
              <ChatHeader connected={connected} />
              <ChatThread
                messages={messages}
                doctorMessages={doctorMessages}
                cards={cards}
                thinking={thinking}
                doctorThinking={doctorThinking}
                connected={connected}
                onSelectDoctor={selectDoctor}
                onSelectSlot={resolveSlot}
                onLabDecision={resolveLabDecision}
              />
              <ChatComposer onSend={sendText} disabled={!connected} />
            </div>
          )}

          {activeTab === "inbox" && (
            <InboxPanel
              notifications={inbox}
              connected={connected}
              onMarkRead={markInboxRead}
              onViewReports={() => setTab("reports")}
              onViewAppointments={() => setTab("appointments")}
              onLabDecision={resolveLabDecision}
            />
          )}

          {activeTab === "reports" && (
            <LabReportsPanel reports={reports} onAddSampleReport={addSampleReport} />
          )}

          {activeTab === "appointments" && (
            <AppointmentsPanel
              doctorName={doctorName}
              booked={appointmentBooked}
              slotCards={cards.filter((card) => card.kind === "slot_select")}
              onSelectSlot={resolveSlot}
              doctorReady={doctorReady}
              doctorMessages={doctorMessages}
              doctorThinking={doctorThinking}
              consultationActive={consultationActive}
              onStartConsultation={handleStartConsultation}
              onSendDoctorMessage={sendDoctorMessage}
              consultationChart={consultationChart}
              userId={userId}
            />
          )}

          {activeTab === "profile" && (
            <ProfilePanel profile={profile} reports={reports} onLogout={logout} />
          )}
        </main>
      </div>
    </div>
  );
}
