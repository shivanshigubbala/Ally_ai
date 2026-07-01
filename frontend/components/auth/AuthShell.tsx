import type { ReactNode } from "react";
import MedicalTeamIllustration from "@/components/illustration/MedicalTeamIllustration";

type AuthShellProps = {
  eyebrow?: string;
  title: string;
  description: string;
  panelTitle: string;
  panelDescription: string;
  panelChildren: ReactNode;
  footer?: ReactNode;
};

export default function AuthShell({
  eyebrow,
  title,
  description,
  panelTitle,
  panelDescription,
  panelChildren,
  footer,
}: AuthShellProps) {
  return (
    <main className="min-h-[100dvh] overflow-y-auto bg-[#c9edf2] px-4 py-4 sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-full max-w-6xl items-center justify-center py-2 sm:py-4">
        <div className="grid w-full gap-5 overflow-hidden rounded-[2rem] bg-white/78 p-4 shadow-[0_28px_90px_rgba(14,116,144,0.16)] backdrop-blur md:p-5 lg:grid-cols-[1.1fr_0.9fr] lg:p-6">
          <section className="relative overflow-hidden rounded-[1.75rem] bg-[linear-gradient(180deg,#eefbfe_0%,#d9f2f7_100%)] px-5 py-5 sm:px-7 sm:py-7 lg:px-8 lg:py-8">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.9),transparent_20%),radial-gradient(circle_at_bottom_left,rgba(34,211,238,0.16),transparent_22%)]" />
            <div className="relative z-10 flex h-full flex-col justify-between gap-4">
              <div className="max-w-xl">
                {eyebrow ? (
                  <div className="mb-4 inline-flex rounded-full border border-white/90 bg-white/75 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-700 shadow-sm">
                    {eyebrow}
                  </div>
                ) : null}
                <h1 className="max-w-lg text-[2.3rem] font-semibold tracking-tight text-slate-900 sm:text-5xl">
                  {title}
                </h1>
                <p className="mt-4 max-w-xl text-base leading-7 text-slate-600 sm:text-[1.05rem]">
                  {description}
                </p>
              </div>

              <div className="mx-auto w-full max-w-[420px] rounded-[2rem] border border-white/80 bg-white/75 p-3 shadow-[0_22px_65px_rgba(8,47,73,0.1)]">
                <MedicalTeamIllustration />
              </div>
            </div>
          </section>

          <section className="flex items-center px-1 py-1 sm:px-3 lg:px-1">
            <div className="mx-auto w-full max-w-md py-2 sm:py-4">
              <div className="mb-4">
                <div className="mb-3 inline-flex rounded-full bg-cyan-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-800">
                  Ally AI
                </div>
                <h2 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
                  {panelTitle}
                </h2>
                <p className="mt-3 text-sm leading-6 text-slate-500">
                  {panelDescription}
                </p>
              </div>

              <div className="rounded-[1.5rem] border border-slate-200/80 bg-white p-4 shadow-[0_18px_45px_rgba(15,23,42,0.08)]">
                {panelChildren}
              </div>

              {footer ? <div className="mt-4">{footer}</div> : null}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
