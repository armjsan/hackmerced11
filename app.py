from flask import Flask, render_template, request, send_file
from fpdf import FPDF
from datetime import datetime
import io
import json

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate-pdf", methods=["POST"])
def generate_pdf():
    data = request.get_json()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 15, "Medical Intake Report", new_x="LMARGIN", new_y="NEXT", align="C")

    # Date
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(127, 140, 141)
    date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    pdf.cell(0, 8, f"Generated: {date_str}", new_x="LMARGIN", new_y="NEXT", align="C")

    # Divider
    pdf.ln(5)
    pdf.set_draw_color(52, 152, 219)
    pdf.set_line_width(0.8)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(8)

    # Report sections
    sections = [
        ("1. Primary Symptoms", data.get("symptomCategory", "Not provided")),
        ("2. Specific Symptoms", data.get("specificSymptom", "Not provided")),
        ("3. Pain Level", data.get("painLevel", "Not provided")),
        ("4. Pain Location", data.get("painLocation", "Not provided")),
        ("5. Current Medication Status", data.get("medicationStatus", "Not provided")),
        ("6. Allergies", data.get("allergies", "Not provided")),
        ("7. Diagnosed Conditions", data.get("conditions", "Not provided")),
        ("8. Supplements / Medications", data.get("supplements", "Not provided")),
        ("9. Home Remedies Tried", data.get("homeRemedies", "Not provided")),
        ("10. Surgical History", data.get("surgeryHistory", "Not provided")),
        ("11. Visit Expectations", data.get("expectations", "Not provided")),
        ("12. Medications to Avoid / Side Effects", data.get("sideEffects", "Not provided")),
        ("13. Provider Satisfaction", data.get("doctorSatisfaction", "Not provided")),
    ]

    for label, value in sections:
        # Section label
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 9, label, new_x="LMARGIN", new_y="NEXT")

        # Section value
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(52, 73, 94)
        pdf.multi_cell(0, 7, f"  {value}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # Footer divider
    pdf.ln(5)
    pdf.set_draw_color(52, 152, 219)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(8)

    # Disclaimer
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(149, 165, 166)
    pdf.multi_cell(
        0,
        5,
        "This report is for informational purposes to assist your healthcare provider. "
        "It is not a medical diagnosis. Please share it with your doctor during your appointment "
        "to help make the visit more efficient, as appointments are professional and typically limited in time.",
        align="C",
    )

    # Output PDF to bytes
    pdf_bytes = pdf.output()
    buffer = io.BytesIO(pdf_bytes)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"medical_intake_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
