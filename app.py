import os
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Folder penyimpanan gambar upload
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


# =========================================================
#  BACKWARD CHAINING – TEKNIK BATIK
# =========================================================
def backward_chain_technique(facts):
    """
    Menentukan teknik batik dengan backward chaining.
    facts: dict berisi fakta boolean, misalnya:
        {
            "goresan_tidak_simetris": True,
            "variasi_tekanan_garis": True,
            "malam_terlihat": True,
            ...
        }
    """

    # Hipotesis 1: Batik Tulis
    rules_tulis = [
        ("goresan_tidak_simetris", True,
         "Goresan tampak tidak simetris / bervariasi."),
        ("variasi_tekanan_garis", True,
         "Tekanan goresan malam bervariasi seperti digambar manual."),
        ("malam_terlihat", True,
         "Malam (wax) terlihat jelas pada permukaan kain."),
    ]
    if all(facts.get(k) == expected for k, expected, _ in rules_tulis):
        return "Batik Tulis", [msg for _, _, msg in rules_tulis]

    # Hipotesis 2: Batik Cap
    rules_cap = [
        ("pola_berulang_sangat_rapi", True,
         "Pola berulang sangat teratur dan konsisten."),
        ("malam_terlihat", True,
         "Malam (wax) masih tampak pada pola."),
        ("goresan_tidak_simetris", False,
         "Goresan tidak menunjukkan ketidakteraturan seperti tulis.")
    ]
    if all(facts.get(k) == expected for k, expected, _ in rules_cap):
        return "Batik Cap", [msg for _, _, msg in rules_cap]

    # Hipotesis 3: Batik Print
    rules_print = [
        ("malam_terlihat", False,
         "Tidak terlihat malam (wax) pada permukaan kain."),
        ("warna_sangat_rata", True,
         "Sebaran warna sangat rata dan homogen."),
        ("pola_seragam_mesin", True,
         "Pola tampak sangat seragam seperti hasil cetakan mesin."),
    ]
    if all(facts.get(k) == expected for k, expected, _ in rules_print):
        return "Batik Print", [msg for _, _, msg in rules_print]

    # Jika tidak ada hipotesis yang sepenuhnya terbukti
    return "Tidak Dapat Ditentukan", [
        "Ciri-ciri yang diberikan tidak cukup kuat untuk menentukan teknik secara pasti."
    ]


# =========================================================
#  BACKWARD CHAINING – KUALITAS BATIK
# =========================================================
def backward_chain_quality(facts, defect_count: int):
    """
    Menentukan kualitas batik (Premium / Standard / Reject) dengan backward chaining.
    facts mencakup:
        "warna_tajam", "warna_pudar", "kain_halus",
        "cacat_rendah", "cacat_tinggi"
    defect_count dipakai untuk memperjelas penjelasan.
    """

    explanations = []

    # Hipotesis 1: Premium
    rules_premium = [
        ("warna_tajam", True,
         "Warna terlihat tajam dan cerah."),
        ("warna_pudar", False,
         "Tidak terdapat indikasi warna yang pudar."),
        ("cacat_rendah", True,
         "Jumlah cacat motif sangat sedikit (≤ 1)."),
        ("kain_halus", True,
         "Kain terasa halus saat diraba.")
    ]
    if all(facts.get(k) == expected for k, expected, _ in rules_premium):
        return "Premium", [msg for _, _, msg in rules_premium]

    # Hipotesis 2: Reject
    # Aturan Reject cukup kuat jika salah satu kondisi berat terpenuhi
    reject_conditions = []
    if facts.get("warna_pudar"):
        reject_conditions.append(
            "Warna sudah terlihat pudar sehingga menurunkan kualitas visual."
        )
    if facts.get("cacat_tinggi"):
        reject_conditions.append(
            f"Jumlah cacat motif cukup banyak (≥ 3), tercatat sekitar {defect_count} cacat."
        )

    if reject_conditions:
        return "Reject", reject_conditions

    # Jika bukan Premium dan tidak memenuhi kriteria Reject → Standard
    explanations.append(
        "Kualitas masih layak pakai, dengan kondisi warna dan cacat dalam batas wajar."
    )
    if defect_count == 2:
        explanations.append("Terdapat cacat motif ringan sekitar 2 titik.")
    return "Standard", explanations


# =========================================================
#  ROUTE FLASK
# =========================================================
@app.route("/", methods=["GET", "POST"])
def index():
    result = None

    if request.method == "POST":
        print("Form submitted.")
        def rb(name: str) -> bool:
            return request.form.get(name) == "yes"

        # Radio input (Ya/Tidak)
        pattern_repeated = rb("pattern_repeated")
        strokes_irregular = rb("strokes_irregular")
        wax_visible = rb("wax_visible")
        machine_like = rb("machine_like")
        color_sharp = rb("color_sharp")
        color_faded = rb("color_faded")
        fabric_smooth = rb("fabric_smooth")

        motif_name = request.form.get("motif_name", "").strip()

        try:
            defect_count = int(request.form.get("defect_count", "0"))
        except ValueError:
            defect_count = 0

        # -------------------------
        #  HANDLE IMAGE UPLOAD
        # -------------------------
        image_url = None
        file = request.files.get("image")
        if file and file.filename and allowed(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            # untuk template, cukup gunakan path relatif
            image_url = "/" + save_path.replace("\\", "/")

        # -------------------------
        #  BANGUN FAKTA UNTUK BACKWARD CHAINING
        # -------------------------
        facts = {
            # Teknik
            "goresan_tidak_simetris": strokes_irregular,
            # diasumsikan variasi tekanan garis sejalan dengan strokes_irregular
            "variasi_tekanan_garis": strokes_irregular,
            "malam_terlihat": wax_visible,
            "pola_berulang_sangat_rapi": pattern_repeated,
            "warna_sangat_rata": color_sharp and not color_faded,
            "pola_seragam_mesin": machine_like,

            # Kualitas
            "warna_tajam": color_sharp,
            "warna_pudar": color_faded,
            "kain_halus": fabric_smooth,
            "cacat_rendah": defect_count <= 1,
            "cacat_tinggi": defect_count >= 3,
        }

        technique, exp_tech_list = backward_chain_technique(facts)
        quality, exp_qual_list = backward_chain_quality(facts, defect_count)

        result = {
            "technique": technique,
            "quality": quality,
            "motif_name": motif_name if motif_name else "-",
            "exp_tech": exp_tech_list,
            "exp_qual": exp_qual_list,
            "image_url": image_url,
            "defect_count": defect_count,
        }
        
        # Kirim data form kembali agar tetap terisi
        form_data = {
            "pattern_repeated": "yes" if pattern_repeated else "no",
            "strokes_irregular": "yes" if strokes_irregular else "no",
            "wax_visible": "yes" if wax_visible else "no",
            "machine_like": "yes" if machine_like else "no",
            "color_sharp": "yes" if color_sharp else "no",
            "color_faded": "yes" if color_faded else "no",
            "fabric_smooth": "yes" if fabric_smooth else "no",
            "motif_name": motif_name,
            "defect_count": defect_count,
        }
        
        return render_template("index.html", result=result, form_data=form_data)

    print("Form not submitted.")
    return render_template("index.html", result=None, form_data=None)


if __name__ == "__main__":
    app.run(port=5000, debug=True)
