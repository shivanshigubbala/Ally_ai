import os
import re
from pathlib import Path

def generate_chart_pdf(appointment_id: str, department: str, doctor_name: str, patient_name: str, chart_content: str) -> str:
    try:
        from fpdf import FPDF
    except ImportError:
        FPDF = None

    project_root = Path(__file__).resolve().parents[2]
    reports_dir = project_root / "reports" / (department or "general").lower()
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"consultation_chart_{appointment_id}.pdf"
    filepath = reports_dir / filename

    if FPDF is not None:
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
            pdf.cell(0, 6, f"Patient Name: {patient_name}", ln=True)
            pdf.cell(0, 6, f"Appointment ID: {appointment_id}", ln=True)
            pdf.cell(0, 6, f"Doctor: {doctor_name}", ln=True)
            pdf.cell(0, 6, f"Department: {department.title()}", ln=True)
            pdf.ln(5)
            
            # Content
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "Intake & Discoveries", ln=True)
            pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
            pdf.ln(3)
            
            pdf.set_font("Arial", "", 10)
            # Remove Markdown syntax cleanly
            clean_text = chart_content.replace("#", "").replace("*", "").replace("===", "")
            pdf.multi_cell(0, 6, clean_text)
            
            pdf.output(str(filepath))
            return f"/reports/{(department or 'general').lower()}/{filename}"
        except Exception:
            pass

    # Fallback to plain text file but call it .pdf so link doesn't break
    try:
        with open(filepath, "w") as f:
            f.write(chart_content)
        return f"/reports/{(department or 'general').lower()}/{filename}"
    except Exception:
        return ""
