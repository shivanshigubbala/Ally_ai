import os
import re
from pathlib import Path
from datetime import datetime

def generate_prescription_pdf(appointment_id: str) -> dict:
    """
    Generate a consolidated Prescription/Summary PDF for the given appointment.
    Queries the database for patient, receptionist, doctor, and lab reports data.
    Saves the PDF under reports/<department>/prescription_<appointment_id>.pdf,
    and returns metadata describing the report path and details.
    """
    try:
        from backend.db.pgvector_tracker import _conn
    except ImportError:
        try:
            from db.pgvector_tracker import _conn
        except Exception:
            _conn = None

    if not _conn:
        return {}

    # Initialize variables with default values
    patient_name = "Unknown"
    patient_id = "Unknown"
    age = "Unknown"
    gender = "Unknown"
    visit_date = "Unknown"
    
    chief_complaint = "Not recorded"
    initial_symptoms = "Not recorded"
    department = "general"
    
    doctor_name = "Unknown"
    symptom_summary = "Not recorded"
    diagnosis = "Not recorded"
    clinical_reasoning = "Not recorded"
    recommended_tests = "None"
    
    lab_reports = []

    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                # 1. Fetch appointment, user, and context details using SQL coalescing
                cur.execute(
                    """
                    SELECT 
                        COALESCE(u.name, c.patient_reference, 'Patient #' || a.user_id) as patient_name,
                        COALESCE(u.age::text, 'N/A') as age,
                        COALESCE(u.gender, 'Not Specified') as gender,
                        a.user_id,
                        a.booked_at,
                        doc.name,
                        dept.name
                    FROM appointments a
                    LEFT JOIN consultation_contexts c ON a.id::text = c.appointment_id
                    LEFT JOIN users u ON a.user_id = u.id::text OR (u.go_user_id::text = a.user_id)
                    LEFT JOIN doctors doc ON a.doctor_id = doc.id
                    LEFT JOIN departments dept ON doc.department_id = dept.id
                    WHERE a.id = %s
                    """,
                    (int(appointment_id) if str(appointment_id).isdigit() else 0,)
                )
                row = cur.fetchone()
                if row:
                    patient_name = row[0]
                    age = row[1]
                    gender = row[2]
                    patient_id = str(row[3])
                    visit_date = row[4].strftime("%Y-%m-%d %H:%M:%S") if row[4] else "Unknown"
                    doctor_name = row[5]
                    department = row[6]

                # 2. Fetch consultation context details
                cur.execute("SELECT clinical_intake_record, metadata FROM consultation_contexts WHERE appointment_id = %s", (str(appointment_id),))
                ctx_row = cur.fetchone()
                if ctx_row:
                    intake = ctx_row[0] or {}
                    meta = ctx_row[1] or {}
                    
                    chief_complaint = intake.get("chief_complaint") or meta.get("chief_complaint") or chief_complaint
                    initial_symptoms = ", ".join(intake.get("symptoms", [])) if intake.get("symptoms") else initial_symptoms
                    
                    # Doctor evaluation details
                    summary = meta.get("consultation_summary") or {}
                    diagnosis = summary.get("possible_diagnosis") or diagnosis
                    clinical_reasoning = summary.get("clinical_assessment") or clinical_reasoning
                    
                    symptom_summary = meta.get("symptom_summary") or symptom_summary
                    if not symptom_summary or symptom_summary == "Not recorded":
                        symptom_summary = summary.get("notes") or symptom_summary
                        
                    recs = meta.get("consultation_recommendations") or []
                    if recs:
                        recommended_tests = ", ".join(r.get("name", "") for r in recs if isinstance(r, dict))
                
                # 3. Fetch lab reports completed for this appointment
                cur.execute(
                    "SELECT test_name, test_values, reference_range, observation FROM lab_reports WHERE appointment_id = %s",
                    (int(appointment_id) if str(appointment_id).isdigit() else 0,)
                )
                lab_rows = cur.fetchall()
                for lr in lab_rows:
                    lab_reports.append({
                        "test_name": lr[0],
                        "test_values": lr[1],
                        "reference_range": lr[2],
                        "observation": lr[3]
                    })
    except Exception as e:
        print("Failed to fetch prescription database info:", e)

    # Now generate the PDF
    try:
        from fpdf import FPDF
    except ImportError:
        FPDF = None

    project_root = Path(__file__).resolve().parents[2]
    reports_dir = project_root / "reports" / (department or "general").lower()
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"prescription_{appointment_id}.pdf"
    filepath = reports_dir / filename

    if FPDF is not None:
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 18)
            pdf.cell(0, 10, "ALLY DIAGNOSTIC & CLINICAL LABS", ln=True, align="C")
            pdf.set_font("Arial", "B", 13)
            pdf.cell(0, 8, "OFFICIAL MEDICAL PRESCRIPTION & SUMMARY", ln=True, align="C")
            pdf.ln(5)
            
            # Draw Patient Info Table / Block
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "PATIENT INFORMATION", ln=True)
            pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
            pdf.ln(2)
            
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 6, f"Name: {patient_name}", ln=True)
            pdf.cell(0, 6, f"Age: {age}", ln=True)
            pdf.cell(0, 6, f"Gender: {gender}", ln=True)
            pdf.cell(0, 6, f"Patient ID: {patient_id}", ln=True)
            pdf.cell(0, 6, f"Visit Date: {visit_date}", ln=True)
            pdf.ln(4)
            
            # Receptionist Assessment
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "RECEPTIONIST ASSESSMENT", ln=True)
            pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
            pdf.ln(2)
            
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 6, f"Chief Complaint: {chief_complaint}")
            pdf.multi_cell(0, 6, f"Initial Symptoms: {initial_symptoms}")
            pdf.cell(0, 6, f"Department Assigned: {department.title()}", ln=True)
            pdf.ln(4)
            
            # Doctor Consultation
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "DOCTOR CONSULTATION", ln=True)
            pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
            pdf.ln(2)
            
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 6, f"Consulting Doctor: {doctor_name}", ln=True)
            pdf.multi_cell(0, 6, f"Symptom Summary: {symptom_summary}")
            pdf.multi_cell(0, 6, f"Diagnosis: {diagnosis}")
            pdf.multi_cell(0, 6, f"Clinical Reasoning: {clinical_reasoning}")
            pdf.multi_cell(0, 6, f"Recommended Tests: {recommended_tests}")
            pdf.ln(4)
            
            # Lab Reports
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "LAB REPORTS", ln=True)
            pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
            pdf.ln(2)
            
            pdf.set_font("Arial", "", 10)
            if not lab_reports:
                pdf.cell(0, 6, "No lab tests completed / reports generated yet.", ln=True)
            else:
                for idx, lr in enumerate(lab_reports, 1):
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 6, f"{idx}. {lr['test_name']} Report", ln=True)
                    pdf.set_font("Arial", "", 10)
                    pdf.cell(0, 6, f"   - Test Values: {lr['test_values']}", ln=True)
                    pdf.cell(0, 6, f"   - Reference Range: {lr['reference_range']}", ln=True)
                    pdf.multi_cell(0, 6, f"   - Observation: {lr['observation']}")
                    pdf.ln(2)
            
            pdf.output(str(filepath))
            return {
                "pdf_path": f"/reports/{(department or 'general').lower()}/{filename}",
                "doctor_name": doctor_name,
                "patient_id": patient_id,
                "department": department
            }
        except Exception as e:
            print("Failed to render PDF using FPDF:", e)

    # Fallback to plain text file
    try:
        fallback_content = (
            f"PRESCRIPTION:\n"
            f"------------------------\n"
            f"PATIENT INFORMATION\n"
            f"-------------------\n"
            f"Name: {patient_name}\n"
            f"Age: {age}\n"
            f"Gender: {gender}\n"
            f"Patient ID: {patient_id}\n"
            f"Visit Date: {visit_date}\n\n"
            f"-----------------------------------------\n\n"
            f"RECEPTIONIST ASSESSMENT\n"
            f"-----------------------\n"
            f"Chief Complaint: {chief_complaint}\n"
            f"Initial Symptoms: {initial_symptoms}\n"
            f"Department Assigned: {department}\n\n"
            f"-----------------------------------------\n\n"
            f"DOCTOR CONSULTATION\n"
            f"-------------------\n"
            f"Symptom Summary: {symptom_summary}\n"
            f"Diagnosis: {diagnosis}\n"
            f"Clinical Reasoning: {clinical_reasoning}\n"
            f"Recommended Tests: {recommended_tests}\n\n"
            f"-----------------------------------------\n\n"
            f"LAB REPORTS\n"
            f"--------------------\n"
        )
        for idx, lr in enumerate(lab_reports, 1):
            fallback_content += (
                f"{lr['test_name']} Report\n"
                f"Test Values: {lr['test_values']}\n"
                f"Reference Range: {lr['reference_range']}\n"
                f"Observation: {lr['observation']}\n\n"
            )
        if not lab_reports:
            fallback_content += "No lab reports generated.\n"
            
        with open(filepath, "w") as f:
            f.write(fallback_content)
        return {
            "pdf_path": f"/reports/{(department or 'general').lower()}/{filename}",
            "doctor_name": doctor_name,
            "patient_id": patient_id,
            "department": department
        }
    except Exception as e:
        print("Failed to save fallback prescription text:", e)
        return {}


def save_prescription_notification_and_emit(appointment_id: str, pdf_path: str, doctor_name: str, patient_id: str, department: str, emit=None):
    """
    Persist the prescription notification to PostgreSQL, record it in message history, and notify the client.
    """
    try:
        from backend.db.pgvector_tracker import create_notification
    except Exception:
        try:
            from db.pgvector_tracker import create_notification
        except Exception:
            create_notification = None

    if create_notification:
        notif = {
            "notification_id": f"prescription_notif:{appointment_id}",
            "patient_id": patient_id,
            "appointment_id": appointment_id,
            "notification_type": "REPORT_READY",
            "title": "Medical Prescription Ready",
            "message": f"Your medical prescription and consolidated report from {doctor_name} are ready.",
            "metadata": {
                "report_id": f"prescription_{appointment_id}",
                "report_url": pdf_path,
                "download_url": pdf_path,
                "source": "doctor_agent",
                "status": "COMPLETED",
            },
            "status": "PENDING",
        }
        try:
            create_notification(notif)
        except Exception as e:
            print("Failed to save prescription notification:", e)

    chat_msg = f"Your final Medical Prescription has been generated! You can download it here: [Download Prescription PDF]({pdf_path})"
    
    try:
        from backend.db.pgvector_tracker import save_message
    except Exception:
        try:
            from db.pgvector_tracker import save_message
        except Exception:
            save_message = None

    if save_message and patient_id != "Unknown":
        try:
            save_message(
                user_id=patient_id,
                role="assistant",
                content=chat_msg,
                session_id=f"doctor:{patient_id}:{appointment_id}"
            )
        except Exception as e:
            print("Failed to persist prescription message inside chat history database:", e)

    if emit:
        try:
            from backend.models.session_state import WSEvent
        except Exception:
            from models.session_state import WSEvent
        try:
            emit(WSEvent(type="report_ready", payload={
                "report_id": f"prescription_{appointment_id}",
                "doctor": doctor_name,
                "report_url": pdf_path,
                "tests": [],
                "appointment_id": appointment_id,
            }))
            emit(WSEvent(type="text", payload={"content": chat_msg, "from": doctor_name}))
        except Exception as e:
            print("Failed to emit prescription over local websocket emitter:", e)
    else:
        try:
            from backend.ws.router import notify_user_event
            from backend.models.session_state import WSEvent
        except Exception:
            try:
                from ws.router import notify_user_event
                from models.session_state import WSEvent
            except Exception:
                notify_user_event, WSEvent = None, None

        if notify_user_event and WSEvent and patient_id != "Unknown":
            try:
                ev = WSEvent(type="report_ready", payload={
                    "report_id": f"prescription_{appointment_id}",
                    "doctor": doctor_name,
                    "report_url": pdf_path,
                    "tests": [],
                    "appointment_id": appointment_id,
                })
                import asyncio
                asyncio.create_task(notify_user_event(str(patient_id), ev))
                
                chat_ev = WSEvent(type="text", payload={"content": chat_msg, "from": doctor_name})
                asyncio.create_task(notify_user_event(str(patient_id), chat_ev))
            except Exception as e:
                print("Failed to notify user over global router websocket event loop:", e)
