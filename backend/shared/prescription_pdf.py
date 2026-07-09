import re
from pathlib import Path
from datetime import datetime


def generate_prescription_pdf(appointment_id: str) -> dict:
    """
    Generate a consolidated Prescription/Summary PDF for the given appointment.

    Pulls data from:
      - appointments + users + doctors + departments  (patient & doctor info)
      - consultation_contexts.clinical_intake_record   (chief complaint, symptoms)
      - consultation_contexts.metadata                 (full consultation_summary,
                                                        conversation_history, consultation_chart)
      - lab_reports                                    (pdf_name / pdf_path – actual columns only)

    Saves the PDF under backend/reports/<department>/prescription_<appointment_id>.pdf
    and returns a metadata dict.
    """
    try:
        from backend.db.pgvector_tracker import _conn
    except ImportError:
        try:
            from db.pgvector_tracker import _conn  # type: ignore
        except Exception:
            _conn = None

    if not _conn:
        return {}

    # ── Defaults ──────────────────────────────────────────────────────────────
    patient_name = "Unknown Patient"
    patient_id   = "Unknown"
    age          = "N/A"
    gender       = "N/A"
    visit_date   = "Unknown"
    doctor_name  = "Unknown Doctor"
    department   = "general"

    chief_complaint     = "Not recorded"
    initial_symptoms    = "Not recorded"
    clinical_assessment = "Not recorded"
    possible_diagnosis  = "Not recorded"
    doctor_reasoning    = "Not recorded"
    next_steps          = "Not recorded"
    recommended_tests   = []          # list of {name, reason}
    consultation_chart  = ""

    conversation_history: list[dict] = []   # actual doctor ↔ patient chat
    lab_report_files:     list[dict] = []   # {pdf_name, pdf_path, appointment_id}

    # ── DB fetch ──────────────────────────────────────────────────────────────
    try:
        with _conn() as conn:
            with conn.cursor() as cur:

                # 1. Patient / appointment / doctor info
                cur.execute(
                    """
                    SELECT
                        COALESCE(u.name, c.patient_reference, 'Patient #' || a.user_id)  AS patient_name,
                        COALESCE(u.age::text, 'N/A')                                     AS age,
                        COALESCE(u.gender, 'N/A')                                        AS gender,
                        a.user_id,
                        a.booked_at,
                        COALESCE(doc.name, 'Unknown Doctor')                              AS doctor_name,
                        COALESCE(dept.name, 'general')                                   AS department,
                        u.id                                                             AS patient_uuid
                    FROM appointments a
                    LEFT JOIN consultation_contexts c
                           ON a.id::text = c.appointment_id
                    LEFT JOIN users u
                           ON a.user_id = u.id::text
                           OR (u.go_user_id IS NOT NULL AND u.go_user_id::text = a.user_id)
                    LEFT JOIN doctors doc   ON a.doctor_id       = doc.id
                    LEFT JOIN departments dept ON doc.department_id = dept.id
                    WHERE a.id = %s
                    LIMIT 1
                    """,
                    (int(appointment_id) if str(appointment_id).isdigit() else 0,),
                )
                row = cur.fetchone()
                if row:
                    patient_name = row[0] or patient_name
                    age          = row[1] or age
                    gender       = row[2] or gender
                    patient_id   = str(row[7]) if row[7] else str(row[3])
                    visit_date   = row[4].strftime("%d %b %Y, %H:%M") if row[4] else visit_date
                    doctor_name  = row[5] or doctor_name
                    department   = (row[6] or department).lower()

                # 2. Consultation context — intake + metadata
                cur.execute(
                    """
                    SELECT clinical_intake_record, metadata
                    FROM   consultation_contexts
                    WHERE  appointment_id = %s
                    LIMIT 1
                    """,
                    (str(appointment_id),),
                )
                ctx = cur.fetchone()
                if ctx:
                    intake = ctx[0] or {}
                    meta   = ctx[1] or {}

                    # Chief complaint & symptoms from intake record
                    chief_complaint  = (
                        intake.get("chief_complaint")
                        or meta.get("chief_complaint")
                        or chief_complaint
                    )
                    syms = intake.get("symptoms") or []
                    if isinstance(syms, list):
                        initial_symptoms = ", ".join(s for s in syms if s) or initial_symptoms
                    elif isinstance(syms, str):
                        initial_symptoms = syms or initial_symptoms

                    # Full structured summary saved by the doctor agent
                    summary = meta.get("consultation_summary") or {}
                    if summary:
                        clinical_assessment = (
                            summary.get("clinical_assessment")
                            or summary.get("assessment")
                            or clinical_assessment
                        )
                        possible_diagnosis = (
                            summary.get("possible_diagnosis")
                            or summary.get("diagnosis")
                            or possible_diagnosis
                        )
                        doctor_reasoning = (
                            summary.get("doctor_reasoning")
                            or summary.get("reasoning")
                            or doctor_reasoning
                        )
                        next_steps = summary.get("next_steps") or next_steps

                        # Symptoms from summary if intake didn't have them
                        if initial_symptoms == "Not recorded":
                            initial_symptoms = summary.get("symptoms") or initial_symptoms

                        recs = summary.get("lab_recommendations") or summary.get("recommended_tests") or []
                        if isinstance(recs, list):
                            recommended_tests = [
                                r for r in recs
                                if isinstance(r, dict) and r.get("name")
                            ]

                    # Doctor name override from metadata if DB join missed it
                    if meta.get("doctor_name") and doctor_name == "Unknown Doctor":
                        doctor_name = meta["doctor_name"]

                    # Patient name override
                    if meta.get("patient_name") and patient_name == "Unknown Patient":
                        patient_name = meta["patient_name"]

                    # Consultation chart (freeform text the doctor emitted)
                    consultation_chart = meta.get("consultation_chart") or ""

                    # Real conversation history: list of {role, content} dicts
                    raw_hist = meta.get("conversation_history") or []
                    if isinstance(raw_hist, list):
                        conversation_history = [
                            m for m in raw_hist
                            if isinstance(m, dict) and m.get("role") and m.get("content")
                        ]

                # 3. Lab reports — only use the columns that actually exist:
                #    id, appointment_id, user_id, pdf_name, pdf_path, status
                cur.execute(
                    """
                    SELECT pdf_name, pdf_path, status
                    FROM   lab_reports
                    WHERE  appointment_id = %s
                    ORDER  BY id
                    """,
                    (int(appointment_id) if str(appointment_id).isdigit() else 0,),
                )
                for lr in cur.fetchall():
                    lab_report_files.append({
                        "pdf_name":  lr[0],
                        "pdf_path":  lr[1],
                        "status":    lr[2],
                    })

    except Exception as exc:
        print("Failed to fetch prescription database info:", exc)

    # ── PDF generation ────────────────────────────────────────────────────────
    try:
        from fpdf import FPDF
    except ImportError:
        print("fpdf not available — cannot generate prescription PDF")
        return {}

    # backend/reports/<department>/prescription_<id>.pdf
    # __file__ = backend/shared/prescription_pdf.py  → parents[1] = backend/
    backend_dir = Path(__file__).resolve().parents[1]
    reports_dir = backend_dir / "reports" / (department or "general")
    reports_dir.mkdir(parents=True, exist_ok=True)

    filename = f"prescription_{appointment_id}.pdf"
    filepath = reports_dir / filename

    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # ── Header ────────────────────────────────────────────────────────────
        pdf.set_font("Arial", "B", 18)
        pdf.cell(0, 10, "ALLY HOSPITAL", ln=True, align="C")
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 7, "Medical Prescription & Consultation Summary", ln=True, align="C")
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}", ln=True, align="C")
        pdf.ln(4)
        pdf.set_draw_color(100, 100, 100)
        pdf.set_line_width(0.5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        # ── Helper: section heading ────────────────────────────────────────────
        def section(title: str) -> None:
            pdf.set_font("Arial", "B", 11)
            pdf.set_fill_color(230, 240, 255)
            # sanitize for Latin-1
            clean_title = title.encode("latin-1", errors="replace").decode("latin-1")
            pdf.cell(0, 8, f"  {clean_title}", ln=True, fill=True)
            pdf.set_line_width(0.3)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(3)
            pdf.set_font("Arial", "", 10)

        def row(label: str, value: str) -> None:
            pdf.set_font("Arial", "B", 10)
            pdf.cell(50, 6, label, ln=False)
            pdf.set_font("Arial", "", 10)
            clean = str(value).strip() or "-"
            # strip multi-byte unicode that fpdf Latin-1 can't encode
            clean = clean.encode("latin-1", errors="replace").decode("latin-1")
            pdf.multi_cell(0, 6, clean)

        # ── 1. Patient Information ─────────────────────────────────────────────
        section("PATIENT INFORMATION")
        row("Name:",       patient_name)
        row("Age:",        age)
        row("Gender:",     gender)
        row("Patient ID:", patient_id)
        row("Visit Date:", visit_date)
        pdf.ln(4)

        # ── 2. Receptionist Assessment ────────────────────────────────────────
        section("INTAKE - RECEPTIONIST ASSESSMENT")
        row("Chief Complaint:", chief_complaint)
        row("Initial Symptoms:", initial_symptoms)
        row("Department:",      department.title())
        pdf.ln(4)

        # ── 3. Doctor Consultation ────────────────────────────────────────────
        section(f"DOCTOR CONSULTATION - {doctor_name.upper()}")
        row("Clinical Assessment:", clinical_assessment)
        row("Possible Diagnosis:",  possible_diagnosis)
        row("Doctor Reasoning:",    doctor_reasoning)
        row("Next Steps:",          next_steps)

        if recommended_tests:
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, "Recommended Tests:", ln=True)
            pdf.set_font("Arial", "", 10)
            for t in recommended_tests:
                name   = t.get("name", "")
                reason = t.get("reason", "Routine follow-up")
                line   = f"  - {name}  |  {reason}"
                line   = line.encode("latin-1", errors="replace").decode("latin-1")
                pdf.multi_cell(0, 6, line)
        pdf.ln(4)

        # ── 4. Consultation Transcript (real chat) ────────────────────────────
        if conversation_history:
            section("CONSULTATION TRANSCRIPT")
            pdf.set_font("Arial", "", 9)
            for msg in conversation_history:
                role    = str(msg.get("role", "")).strip()
                content = str(msg.get("content", "")).strip()
                if not content:
                    continue
                label = "Doctor:" if role == "assistant" else "Patient:"
                pdf.set_font("Arial", "B", 9)
                pdf.cell(18, 5, label, ln=False)
                pdf.set_font("Arial", "", 9)
                if len(content) > 500:
                    content = content[:497] + "..."
                # sanitise for Latin-1
                content = content.encode("latin-1", errors="replace").decode("latin-1")
                pdf.multi_cell(0, 5, content)
                pdf.ln(1)
            pdf.ln(3)

        # ── 5. Consultation Chart (free-text if present) ──────────────────────
        if consultation_chart and consultation_chart.strip():
            section("CLINICAL CHART NOTES")
            pdf.set_font("Arial", "", 9)
            chart_text = consultation_chart.strip()
            if len(chart_text) > 1200:
                chart_text = chart_text[:1197] + "..."
            chart_text = chart_text.encode("latin-1", errors="replace").decode("latin-1")
            pdf.multi_cell(0, 5, chart_text)
            pdf.ln(3)

        # ── 6. Lab Reports ────────────────────────────────────────────────────
        section("LAB REPORTS")
        if not lab_report_files:
            pdf.set_font("Arial", "I", 10)
            pdf.cell(0, 6, "No lab reports generated for this appointment.", ln=True)
        else:
            for idx, lr in enumerate(lab_report_files, 1):
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 6, f"  {idx}.  {lr['pdf_name']}", ln=True)
                pdf.set_font("Arial", "", 9)
                pdf.cell(0, 5, f"       Status: {lr['status'].title()}  |  File: {lr['pdf_path']}", ln=True)
                pdf.ln(2)
        pdf.ln(4)

        # ── Footer ────────────────────────────────────────────────────────────
        pdf.set_line_width(0.3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)
        pdf.set_font("Arial", "I", 8)
        pdf.multi_cell(
            0, 5,
            "This document is generated by Ally Hospital's AI-assisted clinical system. "
            "It is intended for informational purposes only and should be reviewed by a "
            "licensed medical professional before acting upon it.",
            align="C"
        )

        pdf.output(str(filepath))

        return {
            "pdf_path":    f"/reports/{department}/{filename}",
            "doctor_name": doctor_name,
            "patient_id":  patient_id,
            "department":  department,
        }

    except Exception as exc:
        print("Failed to render prescription PDF:", exc)
        return {}


def save_prescription_notification_and_emit(
    appointment_id: str,
    pdf_path: str,
    doctor_name: str,
    patient_id: str,
    department: str,
    emit=None,
):
    """
    Persist the prescription notification to PostgreSQL and push a
    report_ready WebSocket event to the patient's connected browser.
    """
    try:
        from backend.db.pgvector_tracker import create_notification
    except Exception:
        try:
            from db.pgvector_tracker import create_notification  # type: ignore
        except Exception:
            create_notification = None

    if create_notification:
        notif = {
            "notification_id":   f"prescription_notif:{appointment_id}",
            "patient_id":        patient_id,
            "appointment_id":    appointment_id,
            "notification_type": "REPORT_READY",
            "title":             "Medical Prescription Ready",
            "message":           f"Your medical prescription and consultation summary from {doctor_name} are ready.",
            "metadata": {
                "report_id":    f"prescription_{appointment_id}",
                "report_url":   pdf_path,
                "download_url": pdf_path,
                "source":       "doctor_agent",
                "status":       "COMPLETED",
            },
            "status": "PENDING",
        }
        try:
            create_notification(notif)
        except Exception as exc:
            print("Failed to save prescription notification:", exc)

    # Build the WS event payload once so both emit paths share it
    report_event_payload = {
        "report_id":      f"prescription_{appointment_id}",
        "doctor":         doctor_name,
        "report_url":     pdf_path,
        "download_url":   pdf_path,
        "tests":          [],
        "appointment_id": appointment_id,
        "session_id":     str(appointment_id),
    }
    chat_msg = (
        f"Your medical prescription and consultation summary have been generated. "
        f"You can download it from the Reports tab."
    )

    # ── Path A: called from inside a running agent emit context ──────────────
    if emit:
        try:
            from backend.models.session_state import WSEvent
        except Exception:
            from models.session_state import WSEvent  # type: ignore
        try:
            emit(WSEvent(type="report_ready", payload=report_event_payload))
            emit(WSEvent(type="text", payload={"content": chat_msg, "from": doctor_name}))
        except Exception as exc:
            print("Failed to emit prescription via local emitter:", exc)
        return

    # ── Path B: called from the /internal/report_ready webhook ───────────────
    try:
        from backend.ws.router import notify_user_event
        from backend.models.session_state import WSEvent
    except Exception:
        try:
            from ws.router import notify_user_event       # type: ignore
            from models.session_state import WSEvent      # type: ignore
        except Exception:
            notify_user_event, WSEvent = None, None

    if notify_user_event and WSEvent and patient_id and patient_id != "Unknown":
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            ev   = WSEvent(type="report_ready", payload=report_event_payload)
            chat = WSEvent(type="text", payload={"content": chat_msg, "from": doctor_name})
            loop.create_task(notify_user_event(str(patient_id), ev))
            loop.create_task(notify_user_event(str(patient_id), chat))
        except Exception as exc:
            print("Failed to notify patient over WebSocket:", exc)
