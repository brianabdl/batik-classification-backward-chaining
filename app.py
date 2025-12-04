import copy
import os
import json
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO

# --------------------
# Configuration
# --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"}

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-in-production"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "batik.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)


# --------------------
# Models
# --------------------
class Rule(db.Model):
    """
    Store structured rules as JSON in 'conditions' and with a 'conclusion' string.
    Fields:
      - rule_type: 'technique' or 'quality'
      - priority: int (lower = checked earlier)
      - conditions: JSON string representing a dict where keys are input names and
                    values are expected values (True/False or special strings)
      - conclusion: textual conclusion (e.g., "Batik Tulis" or "Premium")
      - explanation: short explanation string or list (JSON)
    """
    id = db.Column(db.Integer, primary_key=True)
    rule_type = db.Column(db.String(32), nullable=False)
    priority = db.Column(db.Integer, default=100)
    conditions = db.Column(db.Text, nullable=False)  # JSON string
    conclusion = db.Column(db.String(128), nullable=False)
    explanation = db.Column(db.Text, nullable=True)  # JSON or plain text
    created_at = db.Column(db.DateTime, default=datetime.now)


class BatikRecord(db.Model):
    """
    Store classification results and references to uploaded images.
    """
    id = db.Column(db.Integer, primary_key=True)
    motif_name = db.Column(db.String(128))
    inputs = db.Column(db.Text)  # JSON string of the input facts
    technique = db.Column(db.String(64))
    quality = db.Column(db.String(64))
    exp_tech = db.Column(db.Text)  # JSON array or text
    exp_qual = db.Column(db.Text)
    image_path = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.now)


# --------------------
# Utils
# --------------------
def allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def load_rules(rule_type: str):
    rows = Rule.query.filter_by(rule_type=rule_type).order_by(Rule.priority.asc()).all()
    rules = []
    for r in rows:
        try:
            cond = json.loads(r.conditions)
        except Exception:
            cond = {}
        try:
            exp = json.loads(r.explanation) if r.explanation else [r.explanation or ""]
        except Exception:
            exp = [r.explanation] if r.explanation else []
        rules.append({"id": r.id, "priority": r.priority, "conditions": cond,
                      "conclusion": r.conclusion, "explanation": exp})
    return rules


def match_conditions(conditions: dict, facts: dict) -> bool:
    """
    Conditions is a dict of expected values. For simplicity:
    - If expected is True/False: direct equality
    - If expected is "any": always true
    - If expected is a string starting with "gte:" or "lte:" -> compare numeric fact value
    """
    for k, expected in conditions.items():
        if expected == "any":
            continue
        if isinstance(expected, bool):
            if facts.get(k) is None or facts.get(k) != expected:
                return False
            continue
        if isinstance(expected, str):
            if expected.startswith("gte:"):
                try:
                    val = float(str(facts.get(k, 0)))
                    threshold = float(expected.split(":", 1)[1])
                    if val < threshold:
                        return False
                except Exception:
                    return False
                continue
            if expected.startswith("lte:"):
                try:
                    val = float(str(facts.get(k, 0)))
                    threshold = float(expected.split(":", 1)[1])
                    if val > threshold:
                        return False
                except Exception:
                    return False
                continue
            # fallback: direct string match
            if str(facts.get(k)) != expected:
                return False
    return True


# --------------------
# Inference (Backward Chaining)
# --------------------
def backward_chain(rule_type: str, facts: dict, defect_count: int = 0):
    """
    General backward-chaining using rules stored in DB.
    For rule_type 'technique' or 'quality', returns (conclusion, explanations_list).
    The rules are checked by priority order; first rule that fully matches wins.
    """
    rules = load_rules(rule_type)
    for r in rules:
        cond = r["conditions"]
        # augment facts for numeric checks
        enriched_facts = dict(facts)
        enriched_facts["defect_count"] = defect_count
        if match_conditions(cond, enriched_facts):
            return r["conclusion"], r["explanation"]
    return "Undetermined", ["No rule matched the given facts."]


# --------------------
# Seed default rules if DB empty
# --------------------
def seed_default_rules():
    if Rule.query.count() > 0:
        return

    # Technique rules (priority lower = checked first)
    technique_rules = [
        {
            "rule_type": "technique",
            "priority": 10,
            "conditions": {
                "strokes_irregular": True,
                "wax_visible": True,
                "pattern_repeated": False
            },
            "conclusion": "Batik Tulis",
            "explanation": ["Irregular hand-drawn strokes detected.", "Wax traces visible suggesting manual canting."]
        },
        {
            "rule_type": "technique",
            "priority": 20,
            "conditions": {
                "pattern_repeated": True,
                "wax_visible": True,
                "strokes_irregular": False
            },
            "conclusion": "Batik Cap",
            "explanation": ["Highly repetitive pattern and uniform wax marks indicate stamping (cap)."]
        },
        {
            "rule_type": "technique",
            "priority": 30,
            "conditions": {
                "wax_visible": False,
                "machine_like": True,
                "pattern_repeated": True
            },
            "conclusion": "Batik Print",
            "explanation": ["No wax traces and machine-like uniformity indicate printed batik."]
        }
    ]

    # Quality rules
    quality_rules = [
        {
            "rule_type": "quality",
            "priority": 10,
            "conditions": {
                "color_sharp": True,
                "color_faded": False,
                "kain_halus": True,
                "defect_count": "lte:1"
            },
            "conclusion": "Premium",
            "explanation": ["Sharp color, smooth fabric, and minimal defects (≤1)."]
        },
        {
            "rule_type": "quality",
            "priority": 20,
            "conditions": {
                "color_faded": True,
            },
            "conclusion": "Reject",
            "explanation": ["Color appears faded which significantly lowers quality."]
        },
        {
            "rule_type": "quality",
            "priority": 25,
            "conditions": {
                "defect_count": "gte:3"
            },
            "conclusion": "Reject",
            "explanation": ["Multiple visible defects (≥3) make the product unacceptable."]
        },
        {
            "rule_type": "quality",
            "priority": 100,
            "conditions": {
                "any": "any"  # fallback (pattern uses 'any' marker)
            },
            "conclusion": "Standard",
            "explanation": ["Does not meet Premium criteria and not severe enough for Reject; hence Standard."]
        }
    ]

    for r in technique_rules + quality_rules:
        rule = Rule(
            rule_type=r["rule_type"],
            priority=r["priority"],
            conditions=json.dumps(r["conditions"]),
            conclusion=r["conclusion"],
            explanation=json.dumps(r["explanation"])
        )
        db.session.add(rule)
    db.session.commit()


# --------------------
# Routes
# --------------------
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        # helper to read both checkbox and radio 'yes'/'no' fields
        def rb(name: str) -> bool:
            val = request.form.get(name)
            return val == "yes" or val == "on"

        # gather inputs
        motif_name = request.form.get("motif_name", "").strip()
        facts = {
            "pattern_repeated": rb("pattern_repeated"),
            "strokes_irregular": rb("strokes_irregular"),
            "wax_visible": rb("wax_visible"),
            "machine_like": rb("machine_like"),
            "color_sharp": rb("color_sharp"),
            "color_faded": rb("color_faded"),
            "kain_halus": rb("fabric_smooth"),
        }
        try:
            defect_count = int(request.form.get("defect_count", "0"))
        except ValueError:
            defect_count = 0

        # handle file
        image_url = None
        file = request.files.get("image")
        if file and file.filename and allowed(file.filename):
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            image_url = url_for("static", filename=f"uploads/{filename}")

        # inference
        technique, exp_tech = backward_chain("technique", facts, defect_count)
        quality, exp_qual = backward_chain("quality", facts, defect_count)

        # store record
        rec = BatikRecord(
            motif_name=motif_name or None,
            inputs=json.dumps({**facts, "defect_count": defect_count}),
            technique=technique,
            quality=quality,
            exp_tech=json.dumps(exp_tech),
            exp_qual=json.dumps(exp_qual),
            image_path=image_url
        )
        db.session.add(rec)
        db.session.commit()

        result = {
            "record_id": rec.id,
            "technique": technique,
            "quality": quality,
            "motif_name": motif_name or "-",
            "exp_tech": exp_tech,
            "exp_qual": exp_qual,
            "image_url": image_url,
            "defect_count": defect_count
        }

    return render_template("index.html", result=result)


@app.route("/history")
def history():
    rows = BatikRecord.query.order_by(BatikRecord.created_at.desc()).all()
    # parse JSON fields for display
    for r in rows:
        try:
            r.inputs_parsed = json.loads(r.inputs)
        except Exception:
            r.inputs_parsed = {}
        try:
            r.exp_tech_parsed = json.loads(r.exp_tech or "[]")
        except Exception:
            r.exp_tech_parsed = []
        try:
            r.exp_qual_parsed = json.loads(r.exp_qual or "[]")
        except Exception:
            r.exp_qual_parsed = []
    return render_template("history.html", records=rows)


@app.route("/rules", methods=["GET", "POST"])
def rules_page():
    # list rules; also allow adding simple rules via form (admin)
    if request.method == "POST":
        rule_type = request.form.get("rule_type")
        priority = int(request.form.get("priority") or 100)
        # conditions input is expected as JSON in textarea; instructor can paste JSON
        cond_text = request.form.get("conditions", "{}")
        conclusion = request.form.get("conclusion")
        explanation_text = request.form.get("explanation", "[]")
        # Basic validation
        try:
            cond_json = json.loads(cond_text)
        except Exception:
            flash("Conditions must be valid JSON.", "error")
            return redirect(url_for("rules_page"))
        try:
            exp_json = json.loads(explanation_text)
        except Exception:
            exp_json = [explanation_text]
        rule = Rule(
            rule_type=rule_type,
            priority=priority,
            conditions=json.dumps(cond_json),
            conclusion=conclusion,
            explanation=json.dumps(exp_json)
        )
        db.session.add(rule)
        db.session.commit()
        flash("Rule added.", "success")
        return redirect(url_for("rules_page"))

    tech_rules = load_rules("technique")
    qual_rules = load_rules("quality")
    return render_template("rules.html", tech_rules=tech_rules, qual_rules=qual_rules)


@app.route("/rule/delete/<int:rule_id>", methods=["POST"])
def delete_rule(rule_id):
    r = Rule.query.get_or_404(rule_id)
    db.session.delete(r)
    db.session.commit()
    flash("Rule deleted.", "success")
    return redirect(url_for("rules_page"))


@app.route("/export-pdf/<int:record_id>")
def export_pdf(record_id):
    """Generate PDF report for a specific classification result"""
    record = BatikRecord.query.get_or_404(record_id)
    
    # Parse JSON fields
    try:
        inputs = json.loads(record.inputs)
    except:
        inputs = {}
    try:
        exp_tech = json.loads(record.exp_tech or "[]")
    except:
        exp_tech = []
    try:
        exp_qual = json.loads(record.exp_qual or "[]")
    except:
        exp_qual = []
    
    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=8,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=4,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=2
    )
    
    # Title
    story.append(Paragraph("Laporan Klasifikasi Batik", title_style))
    story.append(Paragraph(f"Tanggal: {record.created_at.strftime('%d %B %Y, %H:%M')}", normal_style))
    
    # Image if exists
    if record.image_path:
        try:
            img_path = os.path.join(BASE_DIR, 'static', 'uploads', os.path.basename(record.image_path))
            if os.path.exists(img_path):
                img = RLImage(img_path, width=3*inch, height=3*inch, kind='proportional')
                story.append(img)
        except:
            pass
    
    # Motif name
    if record.motif_name:
        story.append(Paragraph("Informasi Motif", heading_style))
        data = [["Nama Motif:", record.motif_name]]
        t = Table(data, colWidths=[2*inch, 4*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
        ]))
        story.append(t)
    
    # Classification Results
    story.append(Paragraph("Hasil Klasifikasi", heading_style))
    
    # Technique
    tech_color = colors.HexColor('#667eea')
    data = [
        ["Teknik Pembuatan:", Paragraph(f"<b>{record.technique}</b>", normal_style)]
    ]
    t = Table(data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#e0e7ff')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
    ]))
    story.append(t)
    
    # Quality
    qual_color = colors.HexColor('#10b981') if record.quality == 'Premium' else \
                 colors.HexColor('#ef4444') if record.quality == 'Reject' else \
                 colors.HexColor('#f59e0b')
    
    data = [
        ["Kualitas:", Paragraph(f"<b>{record.quality}</b>", normal_style)],
        ["Jumlah Cacat:", str(inputs.get('defect_count', 0))]
    ]
    t = Table(data, colWidths=[2*inch, 4*inch])
    bg_color = colors.HexColor('#dcfce7') if record.quality == 'Premium' else \
                colors.HexColor('#fee2e2') if record.quality == 'Reject' else \
                colors.HexColor('#fef3c7')
    
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), bg_color),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
    ]))
    story.append(t)
    
    # Technique Explanation
    story.append(Paragraph("Penjelasan Teknik", heading_style))
    for i, exp in enumerate(exp_tech, 1):
        story.append(Paragraph(f"{i}. {exp}", normal_style))
    
    # Quality Explanation
    story.append(Paragraph("Penjelasan Kualitas", heading_style))
    for i, exp in enumerate(exp_qual, 1):
        story.append(Paragraph(f"{i}. {exp}", normal_style))

    # Input Details
    story.append(Paragraph("Detail Input Karakteristik", heading_style))
    input_data = [
        ["Karakteristik", "Nilai"],
        ["Pola berulang teratur", "Ya" if inputs.get('pattern_repeated') else "Tidak"],
        ["Goresan tidak simetris", "Ya" if inputs.get('strokes_irregular') else "Tidak"],
        ["Malam (wax) terlihat", "Ya" if inputs.get('wax_visible') else "Tidak"],
        ["Pola seperti mesin", "Ya" if inputs.get('machine_like') else "Tidak"],
        ["Warna tajam/cerah", "Ya" if inputs.get('color_sharp') else "Tidak"],
        ["Warna pudar", "Ya" if inputs.get('color_faded') else "Tidak"],
        ["Kain halus", "Ya" if inputs.get('kain_halus') else "Tidak"],
        ["Jumlah cacat", str(inputs.get('defect_count', 0))]
    ]
    
    t = Table(input_data, colWidths=[3*inch, 2*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
    ]))
    story.append(t)
    # Footer
    story.append(Spacer(1,10))
    footer_text = f"<i>Generated by Batik Expert System - {datetime.now().strftime('%d %B %Y')}</i>"
    footer_style = copy.copy(normal_style)
    footer_style.alignment = TA_CENTER
    story.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    filename = f"klasifikasi_batik_{record.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')


# --------------------
# Init
# --------------------
with app.app_context():
    db.create_all()
    seed_default_rules()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
