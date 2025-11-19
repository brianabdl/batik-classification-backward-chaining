from flask import Flask, render_template, request
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXT = {"png", "jpg", "jpeg"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def classify_batik(pattern_repeated, strokes_irregular, wax_visible,
                   machine_like, color_sharp, color_faded,
                   defect_count, fabric_smooth):

    # --- Technique Classification ---
    explanation_technique = []
    technique = "Tidak Diketahui"

    # Rule: Batik Tulis
    if strokes_irregular and wax_visible and not pattern_repeated:
        technique = "Batik Tulis"
        explanation_technique.append(
            "Goresan tidak simetris dan bervariasi, serta terdapat malam, "
            "menunjukkan proses digambar manual (tulis)."
        )

    # Rule: Batik Cap
    elif pattern_repeated and not strokes_irregular and wax_visible:
        technique = "Batik Cap"
        explanation_technique.append(
            "Pola berulang sempurna tanpa variasi goresan, dengan malam terlihat, "
            "menunjukkan penggunaan cap."
        )

    # Rule: Batik Print
    elif not wax_visible and machine_like:
        technique = "Batik Print"
        explanation_technique.append(
            "Tidak ada malam dan pola sangat seragam seperti cetakan mesin, "
            "menunjukkan batik print."
        )

    else:
        explanation_technique.append(
            "Ciri-ciri tidak sepenuhnya cocok dengan aturan utama, sehingga teknik tidak pasti."
        )

    # --- Quality Classification ---
    explanation_quality = []
    quality = "Standard"

    # Premium
    if color_sharp and (not color_faded) and defect_count <= 1 and fabric_smooth:
        quality = "Premium"
        explanation_quality.append(
            "Warna tajam, tidak pudar, cacat sangat sedikit (≤1), dan kain halus."
        )

    # Reject
    elif color_faded or defect_count >= 3:
        quality = "Reject"
        if color_faded:
            explanation_quality.append("Warna terlihat pudar.")
        if defect_count >= 3:
            explanation_quality.append(
                f"Terdapat cacat motif cukup banyak (≥3), tercatat {defect_count} cacat."
            )

    # Standard
    else:
        quality = "Standard"
        explanation_quality.append(
            "Kualitas masih layak, dengan warna dan cacat dalam batas wajar."
        )

    return technique, quality, " ".join(explanation_technique), " ".join(explanation_quality)


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    image_url = None

    if request.method == "POST":

        def rb(value):
            return value == "yes"

        # Radio fields
        pattern_repeated = rb(request.form.get("pattern_repeated"))
        strokes_irregular = rb(request.form.get("strokes_irregular"))
        wax_visible = rb(request.form.get("wax_visible"))
        machine_like = rb(request.form.get("machine_like"))
        color_sharp = rb(request.form.get("color_sharp"))
        color_faded = rb(request.form.get("color_faded"))
        fabric_smooth = rb(request.form.get("fabric_smooth"))

        motif_name = request.form.get("motif_name", "").strip()

        try:
            defect_count = int(request.form.get("defect_count", "0"))
        except ValueError:
            defect_count = 0

        # -------------------------
        # IMAGE UPLOAD HANDLER
        # -------------------------
        file = request.files.get("image")

        if file and allowed(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            image_url = save_path
        else:
            image_url = None

        # -------------------------
        # Classification
        # -------------------------
        technique, quality, exp_tech, exp_qual = classify_batik(
            pattern_repeated,
            strokes_irregular,
            wax_visible,
            machine_like,
            color_sharp,
            color_faded,
            defect_count,
            fabric_smooth,
        )

        result = {
            "technique": technique,
            "quality": quality,
            "motif_name": motif_name if motif_name else "-",
            "exp_tech": exp_tech,
            "exp_qual": exp_qual,
            "image_url": image_url,
        }

    return render_template("index.html", result=result)

if __name__ == "__main__":
    # For local development
    app.run(host="0.0.0.0", port=5000)
