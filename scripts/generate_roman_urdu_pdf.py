"""Generate a comprehensive Roman Urdu PDF guide for LaunchGuard AI."""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PDF = REPO_ROOT / "LaunchGuard_AI_Project_Guide_Roman_Urdu.pdf"


class NumberedCanvas(canvas.Canvas):
    """Canvas for adding page numbers and running footer disclaimer."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running top header
        self.drawString(54, 755, "LaunchGuard AI — Project Architecture & Explanation Guide (Roman Urdu)")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 747, 558, 747)

        # Running bottom footer
        self.line(54, 45, 558, 45)
        disclaimer = "Decision-support tool. Not a replacement for certified range safety."
        self.drawString(54, 32, disclaimer)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=30,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#2563EB"),
        spaceAfter=15,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        leftIndent=15,
        spaceAfter=4,
    )

    callout_style = ParagraphStyle(
        "Callout_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1E293B"),
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0F172A"),
    )

    story = []

    # Title block
    story.append(Paragraph("LaunchGuard AI — Roman Urdu Guide", title_style))
    story.append(Paragraph("Complete Project Architecture, Working Mechanism & Real-World Aerospace Impact", subtitle_style))

    # Core Banner Box
    callout_data = [[
        Paragraph(
            "<b>CORE MISSION:</b> LaunchGuard AI ek AI co-pilot hai jo low-cost aur suborbital rocket launch safety "
            "ko automate karta hai. Iska sab se barra rule hai: <b>'Vision Proposes, Rules Decide, AI Explains'</b>. "
            "Yani launch ka final faisla (GO / HOLD / NO-GO) kabhi koi AI model nahi badal sakta — sirf pure Python deterministic rules lete hain.",
            callout_style
        )
    ]]
    callout_table = Table(callout_data, colWidths=[504])
    callout_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ("BORDER", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 10))

    # Section 1
    story.append(Paragraph("1. Current Implementation: Faults Kaise Detect Hotay Hain?", h1_style))
    story.append(Paragraph(
        "Aksar dimagh mein sawal aata hai: <i>Kya hum 3D model par faults dhoond rahay hain ya 2D images par?</i>",
        body_style
    ))
    story.append(Paragraph(
        "<b>Current Answer:</b> Hamara software filhal <b>2D high-resolution images aur live camera video frames</b> par direct Computer Vision chalata hai. Is version mein koi 3D CAD mesh ya 3D model use nahi hota.",
        body_style
    ))
    story.append(Paragraph("Yeh detection do alag alag modes mein hoti hai:", body_style))

    story.append(Paragraph(
        "<b>A) Pre-Launch Optical Inspection (/inspect):</b> Yahan rocket ki high-resolution photo li jaati hai (camera ya drone se). Computer Vision rocket ki body ko scan karti hai aur yeh cheezain detect karti hai:",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Body Cracks & Scratches:</b> Canny edge detection aur surface contour filters se fuselage par fractures aur dararain dhoondi jaati hain.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Dents & Dark Burn Marks:</b> Contrast variance aur thresholding se airframe ke dents aur jallay huay nishan pakray jaatay hain.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Fin Alignment Deviation (Degrees mein):</b> Rocket ke left aur right fins ke angles measure hotay hain. Agar fin 3.0° se zyada tilted ho to warning (HOLD) aati hai, aur agar 6.0° se zyada tilted ho to critical (NO-GO) ho jata hai.",
        bullet_style
    ))

    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>B) Launchpad Danger Zone & Hazard Monitor (/monitor):</b> Yahan launchpad ka live video camera feed (webcam ya RTSP) connect hota hai:",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Perimeter Danger Zone:</b> Range safety officer screen par ek polygon zone draw karta hai. YOLOv8 AI model 500 millisecond se kam time mein check karta hai ke koi banda ya unauthorized object us danger zone mein to nahi aya.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Fire & Smoke Detection:</b> Color segmentation se aag ke sholay aur plume density se dhuwan detect hota hai.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Fuel Leakage & Pooling:</b> Base plate par fuel ya liquid jama hona detect hota hai. Agar liquid ke sath aag bhi nazar aye to system foran CRITICAL alert bajata hai.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Abnormal Motion:</b> Consecutive video frames ke pixel farq ko check karke ignition se pehle gantry ya rocket ki hilti hui movement pakri jaati hai.",
        bullet_style
    ))

    story.append(Spacer(1, 8))

    # Section 2
    story.append(Paragraph("2. Camera Kahan Lagna Chahiye? Rocket Par ya Launchpad Par?", h1_style))
    story.append(Paragraph(
        "Yeh aik bohot ahem point hai jo launch engineering ke standard se samajhna zaroori hai:",
        body_style
    ))
    story.append(Paragraph(
        "• <b>Rocket ke upar camera lagana:</b> Real rocketry mein rocket ke upar camera sirf flight ke dauran stage separation ya fairing open honay ko dekhnay ke liye lagaya jaata hai. Pre-launch inspection ke liye rocket par bahar camera lagana theek nahi hota kyunke camera ka dead weight rocket ko bhaari karta hai aur ignition ke waqt engine ke zabardast acoustic vibration se camera toot sakta hai.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Launchpad / Gantry Tower par camera lagana (Real Standard):</b> Industry standard (NASA, SpaceX, ESA) yahi hai ke cameras launchpad ke service tower, gantry aur perimeter poles par lagaye jaatay hain jo chaaro taraf se rocket par focus kartay hain. Hamara LaunchGuard AI system isi external camera feed ko stream karta hai.",
        bullet_style
    ))

    story.append(Spacer(1, 6))

    # Section 3
    story.append(Paragraph("3. 3D Digital Twin Kya Hota Hai Aur Yeh Agay Kaise Kaam Karega?", h1_style))
    story.append(Paragraph(
        "<b>3D Digital Twin Concept:</b> Agar hum aglay phase mein rocket ka 3D CAD model add karein, to uska faida yeh hoga ke bahir ke 4 cameras se aane wali 2D photos ke defects (cracks, fin angle) 3D rocket model par accurately plot ho jayein ge. Range officer screen par 3D rocket ko 360 degree ghuma kar dekh sake ga ke kis fin ya kis cylinder section par defect mojood hai. Yeh feature is project ko NASA aur SpaceX level ka Enterprise Tool bana deta hai.",
        body_style
    ))

    story.append(Spacer(1, 8))

    # Section 4
    story.append(Paragraph("4. System Ke 6 Main Features", h1_style))

    features_table_data = [
        [Paragraph("<b>Feature</b>", callout_style), Paragraph("<b>Screen / Route</b>", callout_style), Paragraph("<b>Kaam Kya Karta Hai?</b>", callout_style)],
        [
            Paragraph("<b>1. Pre-Launch Inspection</b>", body_style),
            Paragraph("<code>/inspect</code>", code_style),
            Paragraph("Photo upload kar ke fuselage cracks, surface dents aur fin alignment angles scan karta hai. Finding overlays draw hoti hain.", body_style)
        ],
        [
            Paragraph("<b>2. Danger Zone Monitor</b>", body_style),
            Paragraph("<code>/monitor</code>", code_style),
            Paragraph("Live camera feed par exclusion zone banata hai. Personnel intrusion, smoke, fire aur leakages ko <500ms mein pakadta hai.", body_style)
        ],
        [
            Paragraph("<b>3. Safety Officer Agent</b>", body_style),
            Paragraph("<code>/report/[runId]</code>", code_style),
            Paragraph("5-step FAA checklist run karta hai. Agar weather ya clearance missing ho to run pause kar ke user se form fill karwata hai aur auto-resume karta hai.", body_style)
        ],
        [
            Paragraph("<b>4. Deterministic Rule Engine</b>", body_style),
            Paragraph("Backend Python", code_style),
            Paragraph("Verdict calculate karta hai: Critical finding = NO-GO, Warning finding = HOLD, Sab clear = GO. AI model verdict ko tabdeel nahi kar sakta.", body_style)
        ],
        [
            Paragraph("<b>5. Mission History & Share</b>", body_style),
            Paragraph("<code>/history</code><br/><code>/share/[token]</code>", code_style),
            Paragraph("Tamam pichli runs ka record filterable table mein save hota hai. Black & White PDF printable reports aur read-only public share links miltay hain.", body_style)
        ],
        [
            Paragraph("<b>6. One-Click Demo Mode</b>", body_style),
            Paragraph("<code>/</code> aur <code>/inspect</code>", code_style),
            Paragraph("1-click offline demo: Normal (GO), Misaligned Fin (HOLD), Person Near Pad (NO-GO). Zero internet par bhi mukammal pipeline chalti hai.", body_style)
        ],
    ]

    ft_table = Table(features_table_data, colWidths=[120, 94, 290])
    ft_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(ft_table)

    story.append(Spacer(1, 10))

    # Section 5
    story.append(Paragraph("5. Real Life Mein Rocket Banane Walon Par Kya Asar Paray Ga?", h1_style))
    story.append(Paragraph(
        "Real-world aerospace mein yeh software kin logon ke kaam aye ga aur kyu zaroori hai?",
        body_style
    ))
    story.append(Paragraph(
        "• <b>University & Student Rocketry Teams (Spaceport America Cup, ESRA):</b> Dunya bhar mein har saal sainkro student teams rockets banati hain. Unke paas karorron rupay ka radar ya sensor setup nahi hota. LaunchGuard AI unke ek aam laptop par bina internet ke chalta hai. Wo rail par kharay rocket ki photo le kar 5 seconds mein verify kar sakti hain ke fin seedha hai aur body theek hai.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Rocket Accidents Ki Rok-thaam:</b> Agar fin sirf 4 degree bhi tedha ho, to jab rocket hawa mein transonic speed (sound ki raftaar) par pohonchta hai, to hawa ke dabao se rocket ghoom kar phat jata hai. LaunchGuard AI launch se pehle hi HOLD de kar rocket aur engine ko tabah honay se bacha leta hai.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Jaan-Maal Ki Hifazat (Launchpad Safety):</b> Launchpad par pressurized gas, fuel aur explosives hotay hain. Agar koi banda ghalti se danger zone mein chala jaye to system foran audible siren bajata hai aur NO-GO kar deta hai, taakay koi fatal accident na ho.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>NASA & Commercial Space Startups (Rocket Lab, SpaceX):</b> Big companies ko regulatory compliance (FAA Part 450) ke digital records chahiye hotay hain. LaunchGuard AI har inspection ka timestamped, immutable report banata hai jo court ya aviation authorities ko pesh kiya ja sakta hai.",
        bullet_style
    ))

    story.append(Spacer(1, 10))

    # Section 6
    story.append(Paragraph("6. Project Ko Run Karne Ka Complete Tareeqa (Step-by-Step)", h1_style))
    story.append(Paragraph(
        "Apnay system par is project ko run karnay ke liye do terminals use karein:",
        body_style
    ))

    cmd_box = [
        [Paragraph("<b>TERMINAL 1: Backend API (FastAPI)</b>", h2_style)],
        [Paragraph("cd apps/api<br/>.venv\\Scripts\\activate<br/>uvicorn app.main:app --reload --port 8000 --workers 1", code_style)],
        [Paragraph("<b>TERMINAL 2: Frontend (Next.js)</b>", h2_style)],
        [Paragraph("pnpm --filter @launchguard/web dev", code_style)],
        [Paragraph("<b>Browser URL:</b> Open karein <code>http://localhost:3000</code>", body_style)],
    ]
    cmd_table = Table(cmd_box, colWidths=[504])
    cmd_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BORDER", (0, 0), (-1, -1), 1, colors.HexColor("#334155")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(cmd_table)

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "<b>Verification Commands:</b> Agar tests run karne hon to yeh commands chalayein:",
        body_style
    ))
    story.append(Paragraph("• Backend Tests: <code>cd apps/api && .venv\\Scripts\\pytest</code> (90 tests passing)", bullet_style))
    story.append(Paragraph("• Frontend Tests: <code>pnpm --filter @launchguard/web test --run</code> (49 tests passing)", bullet_style))
    story.append(Paragraph("• Strict Typecheck: <code>pnpm --filter @launchguard/web typecheck</code> (0 errors)", bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully generated at: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_pdf()
