import os
import re
from pathlib import Path

def generate_chart_pdf(appointment_id: str, department: str, doctor_name: str, patient_name: str, chart_content: str) -> str:
    try:
        from fpdf import FPDF
    except ImportError:
        FPDF = None

    if FPDF is None:
        return ""

    backend_dir = Path(__file__).resolve().parents[1]
    reports_dir = backend_dir / "reports" / (department or "general").lower()
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"consultation_chart_{appointment_id}.pdf"
    filepath = reports_dir / filename

    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "ALLY DIAGNOSTIC & CLINICAL LABS", ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, "Medical Consultation Chart", ln=True, align="C")
        pdf.ln(5)
        
        # Draw Patient & Appointment Info
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Patient Info", ln=True)
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
        pdf.ln(2)
        
        pdf.set_font("Arial", "", 10)
        
        # Sanitize variables for Latin-1
        p_name = patient_name.encode("latin-1", errors="replace").decode("latin-1")
        doc_name = doctor_name.encode("latin-1", errors="replace").decode("latin-1")
        dept_name = department.encode("latin-1", errors="replace").decode("latin-1").title()
        
        pdf.cell(0, 6, f"Patient Name: {p_name}", ln=True)
        pdf.cell(0, 6, f"Appointment ID: {appointment_id}", ln=True)
        pdf.cell(0, 6, f"Doctor: {doc_name}", ln=True)
        pdf.cell(0, 6, f"Department: {dept_name}", ln=True)
        pdf.ln(5)
        
        # Content
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "Intake & Discoveries", ln=True)
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
        pdf.ln(3)
        
        pdf.set_font("Arial", "", 10)
        # Remove Markdown syntax cleanly and sanitize
        clean_text = chart_content.replace("#", "").replace("*", "").replace("===", "")
        clean_text = clean_text.encode("latin-1", errors="replace").decode("latin-1")
        pdf.multi_cell(0, 6, clean_text)
        
        pdf.output(str(filepath))
        return f"/reports/{(department or 'general').lower()}/{filename}"
    except Exception:
        return ""
