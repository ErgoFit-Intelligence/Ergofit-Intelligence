from __future__ import annotations

import html
import io
import os
from pathlib import Path
from typing import Any

from PIL import Image as PILImage, ImageOps
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor("#0B1F3A")
GOLD = colors.HexColor("#C6A15B")
LIGHT_GOLD = colors.HexColor("#F3EBDD")
LIGHT_BLUE = colors.HexColor("#EEF3F8")
TEXT = colors.HexColor("#222A35")
MUTED = colors.HexColor("#667085")
BORDER = colors.HexColor("#D6DCE5")
WHITE = colors.white


def _t(lang: str, en: str, el: str, sl: str) -> str:
    if lang == "el":
        return el
    if lang == "sl":
        return sl
    return en


def _font_paths() -> tuple[str | None, str | None]:
    regular_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    bold_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    regular = next((p for p in regular_candidates if os.path.exists(p)), None)
    bold = next((p for p in bold_candidates if os.path.exists(p)), None)
    return regular, bold


def _register_fonts() -> tuple[str, str]:
    regular, bold = _font_paths()
    if regular:
        try:
            pdfmetrics.registerFont(TTFont("ErgoFitSans", regular))
            pdfmetrics.registerFont(TTFont("ErgoFitSansBold", bold or regular))
            return "ErgoFitSans", "ErgoFitSansBold"
        except Exception:
            pass
    return "Helvetica", "Helvetica-Bold"


def _escape(value: Any) -> str:
    if value is None:
        return "-"
    return html.escape(str(value)).replace("\n", "<br/>")


def _yes_no(value: Any, lang: str) -> str:
    if value is True:
        return _t(lang, "Yes", "Ναι", "Da")
    if value is False:
        return _t(lang, "No", "Όχι", "Ne")
    return "-"


def _sex_label(value: str, lang: str) -> str:
    labels = {
        "female": _t(lang, "Female", "Γυναίκα", "Ženska"),
        "male": _t(lang, "Male", "Άνδρας", "Moški"),
        "other": _t(lang, "Other / prefer not to say", "Άλλο / δεν επιθυμώ", "Drugo / ne želim navesti"),
    }
    return labels.get(value, value or "-")


def _duration_label(value: str, lang: str) -> str:
    labels = {
        "not_recorded": "-",
        "<1_week": _t(lang, "<1 week", "<1 εβδομάδα", "<1 teden"),
        "1_6_weeks": _t(lang, "1-6 weeks", "1-6 εβδομάδες", "1-6 tednov"),
        "6_12_weeks": _t(lang, "6-12 weeks", "6-12 εβδομάδες", "6-12 tednov"),
        ">12_weeks": _t(lang, ">12 weeks", ">12 εβδομάδες", ">12 tednov"),
    }
    return labels.get(value, "-")


def _frequency_label(value: str, lang: str) -> str:
    labels = {
        "not_recorded": "-",
        "occasional": _t(lang, "Occasional", "Περιστασιακά", "Občasno"),
        "1_2_days_week": _t(lang, "1-2 days/week", "1-2 ημέρες/εβδομάδα", "1-2 dni/teden"),
        "3_5_days_week": _t(lang, "3-5 days/week", "3-5 ημέρες/εβδομάδα", "3-5 dni/teden"),
        "daily": _t(lang, "Daily / almost daily", "Καθημερινά / σχεδόν καθημερινά", "Vsak dan / skoraj vsak dan"),
    }
    return labels.get(value, "-")


def _region_label(region: str, item: dict[str, Any], lang: str) -> str:
    labels = {
        "Neck": _t(lang, "Neck", "Αυχένας", "Vrat"),
        "Shoulder(s)": _t(lang, "Shoulder(s)", "Ώμος/ώμοι", "Rama/ramena"),
        "Elbow / forearm / wrist / hand": _t(lang, "Elbow / forearm / wrist / hand", "Αγκώνας / αντιβράχιο / καρπός / χέρι", "Komolec / podlaket / zapestje / roka"),
        "Low back": _t(lang, "Low back", "Μέση / οσφυϊκή περιοχή", "Križ / ledveni del"),
        "Lower limbs": _t(lang, "Lower limbs", "Κάτω άκρα", "Spodnji udi"),
    }
    return labels.get(region, item.get("label", region))


def _region_exposure(region: str, ctx: dict[str, Any], lang: str) -> str:
    factors: list[str] = []
    rosa_final = int((ctx.get("rosa") or {}).get("final", ctx.get("rosa_final", 0)) or 0)
    posture_keys = {item.get("key") for item in (ctx.get("posture_out") or []) if isinstance(item, dict)}
    chair_issues = bool(ctx.get("chair_failed"))

    if region in {"Neck", "Shoulder(s)"}:
        if max(float(ctx.get("computer_hours", 0) or 0), float(ctx.get("mouse_hours", 0) or 0)) > 4:
            factors.append(_t(lang, "computer/mouse >4 h", "Η/Υ ή ποντίκι >4 ώρες", "računalnik/miška >4 h"))
        if ctx.get("forearm_support") is False:
            factors.append(_t(lang, "limited forearm support", "περιορισμένη στήριξη αντιβραχίων", "omejena podpora podlakti"))
        if region == "Shoulder(s)" and ctx.get("arm_elevation"):
            factors.append(_t(lang, "sustained arm elevation", "παρατεταμένη ανύψωση βραχίονα", "dolgotrajno dvignjena roka"))
        if {"shoulders_relaxed", "elbows_close", "forearms_supported"} & posture_keys:
            factors.append(_t(lang, "posture finding", "εύρημα στάσης", "ugotovitev glede drže"))
    elif region == "Elbow / forearm / wrist / hand":
        if ctx.get("high_repetition"):
            factors.append(_t(lang, "high repetition", "υψηλή επανάληψη", "visoka ponavljajočnost"))
        if ctx.get("hand_force"):
            factors.append(_t(lang, "hand force", "δύναμη χεριού", "sila roke"))
        if ctx.get("forearm_rotation"):
            factors.append(_t(lang, "forearm rotation", "στροφή αντιβραχίου", "rotacija podlakti"))
        if ctx.get("forearm_support") is False:
            factors.append(_t(lang, "limited forearm support", "περιορισμένη στήριξη αντιβραχίων", "omejena podpora podlakti"))
    elif region == "Low back":
        if float(ctx.get("sitting_hours", 0) or 0) >= 6:
            factors.append(_t(lang, "high sitting exposure*", "υψηλή καθιστική έκθεση*", "visoka izpostavljenost sedenju*"))
        if ctx.get("long_sitting_bout") in {"60–120 min", ">120 min"}:
            factors.append(_t(lang, "long static bouts", "μεγάλα στατικά διαστήματα", "dolga statična obdobja"))
        if chair_issues:
            factors.append(_t(lang, "chair-fit findings", "ευρήματα προσαρμογής καρέκλας", "ugotovitve glede prilagoditve stola"))
        if {"dynamic_posture", "back_supported"} & posture_keys:
            factors.append(_t(lang, "posture/movement finding", "εύρημα στάσης/κίνησης", "ugotovitev glede drže/gibanja"))
    elif region == "Lower limbs":
        if {"feet_supported", "leg_clearance"} & posture_keys:
            factors.append(_t(lang, "support/clearance finding", "εύρημα στήριξης/ελεύθερου χώρου", "ugotovitev glede podpore/prostora"))

    if rosa_final >= 5 and region in {"Neck", "Shoulder(s)", "Elbow / forearm / wrist / hand", "Low back"}:
        factors.append(_t(lang, "ROSA action level", "ROSA σε επίπεδο δράσης", "akcijska raven ROSA"))

    return " | ".join(dict.fromkeys(factors)) if factors else _t(
        lang,
        "No specific ergonomic factor identified",
        "Δεν εντοπίστηκε ειδικός εργονομικός παράγοντας",
        "Ni ugotovljenega specifičnega ergonomskega dejavnika",
    )


def _region_action(region: str, item: dict[str, Any], ctx: dict[str, Any], lang: str) -> str:
    severity = int(item.get("severity", 0) or 0)
    has_symptom = severity > 0
    work_impact = (
        item.get("interference") is True
        or item.get("work_modification") is True
        or int(item.get("absence_days_4w", 0) or 0) > 0
    )
    persistent_or_recurrent = (
        item.get("duration") == ">12_weeks"
        or item.get("previous_episode") is True
        or item.get("frequency") == "daily"
    )
    no_specific = _t(lang, "No specific", "Δεν εντοπίστηκε", "Ni ugotovljeno")
    exposure_present = not _region_exposure(region, ctx, lang).startswith(no_specific)

    if has_symptom and (work_impact or persistent_or_recurrent):
        return _t(
            lang,
            "Ergonomic intervention + follow-up; clinical/occupational-health review if persistent or worsening",
            "Εργονομική παρέμβαση + επανέλεγχος· αξιολόγηση από κατάλληλο επαγγελματία υγείας αν επιμένει ή επιδεινώνεται",
            "Ergonomski ukrep + spremljanje; klinična ocena oziroma ocena medicine dela, če simptomi vztrajajo ali se slabšajo",
        )
    if has_symptom and exposure_present:
        return _t(lang, "Ergonomic review + symptom monitoring", "Εργονομικός έλεγχος + παρακολούθηση συμπτωμάτων", "Ergonomski pregled + spremljanje simptomov")
    if has_symptom:
        return _t(lang, "Monitor symptoms and reassess if persistent/worsening", "Παρακολούθηση συμπτωμάτων και επανέλεγχος αν επιμένουν/επιδεινώνονται", "Spremljanje simptomov in ponovna ocena ob vztrajanju/poslabšanju")
    if exposure_present:
        return _t(lang, "Prevention / exposure management", "Πρόληψη / διαχείριση έκθεσης", "Preprečevanje / obvladovanje izpostavljenosti")
    return _t(lang, "Maintain current conditions", "Διατήρηση καλών συνθηκών", "Ohrani trenutne ustrezne pogoje")


def _normalise_photo(blob: bytes) -> io.BytesIO | None:
    try:
        with PILImage.open(io.BytesIO(blob)) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode in ("RGBA", "LA"):
                bg = PILImage.new("RGB", im.size, "white")
                alpha = im.getchannel("A")
                bg.paste(im.convert("RGB"), mask=alpha)
                im = bg
            else:
                im = im.convert("RGB")
            im.thumbnail((1800, 1800))
            out = io.BytesIO()
            im.save(out, format="JPEG", quality=86, optimize=True)
            out.seek(0)
            return out
    except Exception:
        return None


def _photo_flowable(photo: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    data = photo.get("data")
    if not data:
        return []
    img_io = _normalise_photo(data)
    if img_io is None:
        return []

    with PILImage.open(img_io) as im:
        w, h = im.size
    img_io.seek(0)
    max_w = 160 * mm
    max_h = 105 * mm
    scale = min(max_w / w, max_h / h, 1)
    img = Image(img_io, width=w * scale, height=h * scale)
    img.hAlign = "CENTER"
    caption = str(photo.get("comment", "") or "").strip()
    name = str(photo.get("name", "") or "")
    items: list[Any] = [
        Paragraph(f"<b>{_escape(name)}</b>", styles["body"]),
        Spacer(1, 2 * mm),
        img,
    ]
    if caption:
        items += [Spacer(1, 2 * mm), Paragraph(_escape(caption), styles["body"])]
    items += [Spacer(1, 5 * mm)]
    return items


def _styles() -> tuple[dict[str, ParagraphStyle], str, str]:
    regular, bold = _register_fonts()
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("EFTitle", parent=base["Title"], fontName=bold, fontSize=23, leading=28, textColor=NAVY, alignment=TA_LEFT, spaceAfter=8),
        "subtitle": ParagraphStyle("EFSubtitle", parent=base["Normal"], fontName=regular, fontSize=10.5, leading=15, textColor=MUTED),
        "h1": ParagraphStyle("EFH1", parent=base["Heading1"], fontName=bold, fontSize=15, leading=19, textColor=NAVY, spaceBefore=8, spaceAfter=7),
        "h2": ParagraphStyle("EFH2", parent=base["Heading2"], fontName=bold, fontSize=11.5, leading=15, textColor=NAVY, spaceBefore=6, spaceAfter=5),
        "body": ParagraphStyle("EFBody", parent=base["BodyText"], fontName=regular, fontSize=9, leading=13, textColor=TEXT),
        "small": ParagraphStyle("EFSmall", parent=base["BodyText"], fontName=regular, fontSize=7.5, leading=10, textColor=MUTED),
        "cover_label": ParagraphStyle("EFCoverLabel", parent=base["BodyText"], fontName=bold, fontSize=9, leading=12, textColor=GOLD),
    }
    return styles, regular, bold


def _kv_table(rows: list[tuple[str, Any]], styles: dict[str, ParagraphStyle], bold_font: str) -> Table:
    data = [[Paragraph(f"<b>{_escape(k)}</b>", styles["body"]), Paragraph(_escape(v), styles["body"])] for k, v in rows]
    table = Table(data, colWidths=[48 * mm, 122 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.35, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("FONTNAME", (0, 0), (0, -1), bold_font),
    ]))
    return table


def _section_title(text: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    return [
        Spacer(1, 3 * mm),
        Paragraph(_escape(text), styles["h1"]),
        Table([[""]], colWidths=[170 * mm], rowHeights=[1.2 * mm], style=[("BACKGROUND", (0, 0), (-1, -1), GOLD)]),
        Spacer(1, 3 * mm),
    ]


def _page_header_footer(canvas, doc, logo_path: str | None, regular_font: str, bold_font: str):
    canvas.saveState()
    width, height = A4
    if doc.page > 1:
        if logo_path and os.path.exists(logo_path):
            try:
                canvas.drawImage(logo_path, 18 * mm, height - 18 * mm, width=32 * mm, height=9 * mm, preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
        canvas.setStrokeColor(NAVY)
        canvas.setLineWidth(0.8)
        canvas.line(18 * mm, height - 20 * mm, width - 18 * mm, height - 20 * mm)

    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(18 * mm, 15 * mm, width - 18 * mm, 15 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(regular_font, 7.5)
    canvas.drawString(18 * mm, 9 * mm, "Ergonomics - Health & Safety - Wellbeing")
    canvas.setFont(bold_font, 7.5)
    canvas.drawRightString(width - 18 * mm, 9 * mm, str(doc.page))
    canvas.restoreState()


def build_assessment_pdf(
    report_payload: dict[str, Any],
    photos: list[dict[str, Any]] | None = None,
    logo_path: str | Path | None = None,
    lang: str = "en",
) -> bytes:
    """Build a branded worker-level ErgoFit PDF report.

    Photos are intentionally passed separately from report_payload so image bytes are
    not serialised into the Google Sheets JSON cell.
    """
    photos = photos or []
    ctx = report_payload.get("assessment", {}) or {}
    findings = report_payload.get("findings", []) or []
    recommendations = report_payload.get("recommendations", []) or []
    comparison = report_payload.get("comparison", {}) or {}

    styles, regular_font, bold_font = _styles()
    logo_path = str(logo_path) if logo_path else None

    out = io.BytesIO()
    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=26 * mm,
        bottomMargin=20 * mm,
        title=_t(lang, "Ergonomic Assessment Report", "Έκθεση Εργονομικής Αξιολόγησης", "Poročilo o ergonomski oceni"),
        author="ErgoFit Intelligence",
    )

    story: list[Any] = []

    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=54 * mm, height=18 * mm)
            logo.hAlign = "LEFT"
            story += [logo, Spacer(1, 14 * mm)]
        except Exception:
            pass
    story += [
        Paragraph(_t(lang, "ERGONOMIC ASSESSMENT REPORT", "ΕΚΘΕΣΗ ΕΡΓΟΝΟΜΙΚΗΣ ΑΞΙΟΛΟΓΗΣΗΣ", "POROČILO O ERGONOMSKI OCENI"), styles["cover_label"]),
        Spacer(1, 2 * mm),
        Paragraph(_t(lang, "Office Ergonomics - Individual Assessment", "Εργονομία Γραφείου - Ατομική Αξιολόγηση", "Pisarniška ergonomija - individualna ocena"), styles["title"]),
        Paragraph(_t(
            lang,
            "Structured summary of ergonomic exposure, reported symptoms, ROSA findings and proposed actions.",
            "Δομημένη σύνοψη εργονομικής έκθεσης, αναφερόμενων συμπτωμάτων, ευρημάτων ROSA και προτεινόμενων ενεργειών.",
            "Strukturiran povzetek ergonomskih izpostavljenosti, prijavljenih simptomov, ugotovitev ROSA in predlaganih ukrepov.",
        ), styles["subtitle"]),
        Spacer(1, 14 * mm),
    ]

    stage = ctx.get("assessment_stage", "baseline")
    cover_rows = [
        (_t(lang, "Employee / code", "Εργαζόμενος / κωδικός", "Zaposleni / koda"), ctx.get("subject_id") or ctx.get("client_name_or_code") or "-"),
        (_t(lang, "Company", "Εταιρεία", "Podjetje"), ctx.get("company") or "-"),
        (_t(lang, "Department", "Τμήμα", "Oddelek"), ctx.get("department") or "-"),
        (_t(lang, "Job title", "Θέση εργασίας", "Delovno mesto"), ctx.get("job_title") or "-"),
        (_t(lang, "Assessment", "Αξιολόγηση", "Ocena"), _t(lang, "1st assessment", "1η αξιολόγηση", "1. ocena") if stage == "baseline" else _t(lang, "2nd assessment / reassessment", "2η αξιολόγηση / επαναξιολόγηση", "2. ocena / ponovna ocena")),
        (_t(lang, "Date", "Ημερομηνία", "Datum"), ctx.get("assessment_date") or "-"),
    ]
    story += [_kv_table(cover_rows, styles, bold_font), Spacer(1, 10 * mm)]
    story += [
        Paragraph(_t(
            lang,
            "This report supports ergonomic decision-making. It does not diagnose disease or calculate an individual's probability of developing a disorder.",
            "Η παρούσα έκθεση υποστηρίζει τη λήψη εργονομικών αποφάσεων. Δεν αποτελεί διάγνωση και δεν υπολογίζει ατομική πιθανότητα εμφάνισης πάθησης.",
            "Poročilo podpira ergonomsko odločanje. Ne postavlja diagnoze in ne izračunava individualne verjetnosti za razvoj bolezni.",
        ), styles["small"]),
        PageBreak(),
    ]

    story += _section_title(_t(lang, "Assessment data", "Στοιχεία αξιολόγησης", "Podatki ocene"), styles)
    profile_rows = [
        (_t(lang, "Age", "Ηλικία", "Starost"), ctx.get("age", "-")),
        (_t(lang, "Sex", "Φύλο", "Spol"), _sex_label(str(ctx.get("sex", "")), lang)),
        (_t(lang, "Height", "Ύψος", "Telesna višina"), f"{ctx.get('height', '-')} cm"),
        (_t(lang, "Weight", "Βάρος", "Telesna masa"), f"{ctx.get('weight', '-')} kg"),
        (_t(lang, "BMI", "ΔΜΣ", "ITM"), f"{float(ctx.get('bmi', 0) or 0):.1f} kg/m²" if ctx.get("bmi") else "-"),
        (_t(lang, "Computer use", "Χρήση Η/Υ", "Uporaba računalnika"), f"{ctx.get('computer_hours', 0)} h/day"),
        (_t(lang, "Sitting exposure", "Καθιστική εργασία", "Izpostavljenost sedenju"), f"{ctx.get('sitting_hours', 0)} h/day"),
        (_t(lang, "Active breaks / posture changes", "Ενεργά διαλείμματα / αλλαγές στάσης", "Aktivni odmori / spremembe drže"), _yes_no(ctx.get("active_breaks"), lang)),
    ]
    story += [_kv_table(profile_rows, styles, bold_font)]

    story += _section_title(_t(lang, "Overall picture", "Συνολική εικόνα", "Skupna slika"), styles)
    priority_count = sum(isinstance(f, dict) and f.get("status") == "priority" for f in findings)
    attention_count = sum(isinstance(f, dict) and f.get("status") == "attention" for f in findings)
    symptom_details = ctx.get("symptom_details", {}) or {}
    symptom_count = sum(int(item.get("severity", 0) or 0) > 0 for item in symptom_details.values() if isinstance(item, dict))
    rosa = ctx.get("rosa", {}) or {}
    overall = [
        [_t(lang, "ROSA", "ROSA", "ROSA"), str(rosa.get("final", ctx.get("rosa_final", 0)) or _t(lang, "Not assessed", "Δεν αξιολογήθηκε", "Ni ocenjeno"))],
        [_t(lang, "High-priority issues", "Θέματα άμεσης προτεραιότητας", "Težave visoke prioritete"), str(priority_count)],
        [_t(lang, "Issues needing attention", "Θέματα που χρειάζονται προσοχή", "Težave, ki zahtevajo pozornost"), str(attention_count)],
        [_t(lang, "Symptomatic regions", "Περιοχές με συμπτώματα", "Območja s simptomi"), str(symptom_count)],
    ]
    ot = Table(overall, colWidths=[85 * mm, 85 * mm])
    ot.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR", (0, 0), (0, -1), WHITE),
        ("FONTNAME", (0, 0), (0, -1), bold_font),
        ("FONTNAME", (1, 0), (1, -1), bold_font),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story += [ot, Spacer(1, 4 * mm)]

    if int(rosa.get("final", 0) or 0) >= 5:
        story += [Paragraph(_t(
            lang,
            "<b>ROSA:</b> the validated action level (>=5) was reached; further ergonomic investigation/intervention is indicated.",
            "<b>ROSA:</b> επιτεύχθηκε το τεκμηριωμένο επίπεδο δράσης (>=5)· ενδείκνυται περαιτέρω εργονομική διερεύνηση/παρέμβαση.",
            "<b>ROSA:</b> dosežena je validirana akcijska raven (>=5); indicirana sta nadaljnja ergonomska analiza in ukrepanje.",
        ), styles["body"])]
    elif rosa.get("action") != "not_assessed":
        story += [Paragraph(_t(
            lang,
            "<b>ROSA:</b> below the action level of 5. This does not mean that all ergonomic issues or symptoms are absent.",
            "<b>ROSA:</b> κάτω από το επίπεδο δράσης 5. Αυτό δεν σημαίνει ότι απουσιάζουν όλα τα εργονομικά ζητήματα ή συμπτώματα.",
            "<b>ROSA:</b> pod akcijsko ravnjo 5. To ne pomeni, da drugih ergonomskih težav ali simptomov ni.",
        ), styles["body"])]

    story += _section_title(_t(lang, "Musculoskeletal profile and proposed action", "Μυοσκελετικό προφίλ και προτεινόμενη ενέργεια", "Mišično-skeletni profil in predlagani ukrep"), styles)
    profile_data = [[
        Paragraph(f"<b>{_t(lang, 'Region', 'Περιοχή', 'Predel')}</b>", styles["small"]),
        Paragraph(f"<b>{_t(lang, 'Symptoms', 'Συμπτώματα', 'Simptomi')}</b>", styles["small"]),
        Paragraph(f"<b>{_t(lang, 'Work impact', 'Επίδραση στην εργασία', 'Vpliv na delo')}</b>", styles["small"]),
        Paragraph(f"<b>{_t(lang, 'Ergonomic exposure/findings', 'Εργονομική έκθεση / ευρήματα', 'Ergonomska izpostavljenost / ugotovitve')}</b>", styles["small"]),
        Paragraph(f"<b>{_t(lang, 'Proposed action', 'Προτεινόμενη ενέργεια', 'Predlagani ukrep')}</b>", styles["small"]),
    ]]
    for region, item in symptom_details.items():
        if not isinstance(item, dict) or int(item.get("severity", 0) or 0) <= 0:
            continue
        symptom_text = f"{int(item.get('severity', 0) or 0)}/10"
        dur = _duration_label(str(item.get("duration", "not_recorded")), lang)
        freq = _frequency_label(str(item.get("frequency", "not_recorded")), lang)
        if dur != "-":
            symptom_text += f" | {dur}"
        if freq != "-":
            symptom_text += f" | {freq}"

        impact: list[str] = []
        if item.get("interference") is True:
            impact.append(_t(lang, "affects work", "επηρεάζει την εργασία", "vpliva na delo"))
        elif item.get("interference") is False:
            impact.append(_t(lang, "no reported interference", "δεν αναφέρθηκε επίδραση", "ni poročanega vpliva"))
        if item.get("work_modification") is True:
            impact.append(_t(lang, "task/pace modified", "αλλαγή ρυθμού/εργασίας", "spremenjena naloga/tempo"))
        absence = int(item.get("absence_days_4w", 0) or 0)
        if absence > 0:
            impact.append(_t(lang, f"{absence} absence day(s)/4 weeks", f"{absence} ημέρες απουσίας/4 εβδομάδες", f"{absence} dni odsotnosti/4 tedne"))

        profile_data.append([
            Paragraph(_escape(_region_label(region, item, lang)), styles["small"]),
            Paragraph(_escape(symptom_text), styles["small"]),
            Paragraph(_escape(" | ".join(impact) if impact else "-"), styles["small"]),
            Paragraph(_escape(_region_exposure(region, ctx, lang)), styles["small"]),
            Paragraph(_escape(_region_action(region, item, ctx, lang)), styles["small"]),
        ])

    if len(profile_data) > 1:
        pt = Table(profile_data, colWidths=[27 * mm, 31 * mm, 31 * mm, 39 * mm, 42 * mm], repeatRows=1)
        pt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.35, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BLUE]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story += [pt, Spacer(1, 2 * mm)]
    else:
        story += [Paragraph(_t(lang, "No musculoskeletal symptoms were reported.", "Δεν αναφέρθηκαν μυοσκελετικά συμπτώματα.", "Mišično-skeletni simptomi niso bili navedeni."), styles["body"])]

    story += [Paragraph(_t(
        lang,
        "*The >=6 h/day sitting flag is an operational screening flag, not a validated causal threshold.",
        "*Η ένδειξη >=6 ώρες/ημέρα καθιστικής εργασίας είναι λειτουργική ένδειξη screening και όχι επικυρωμένο αιτιώδες όριο.",
        "*Oznaka >=6 ur/dan sedenja je operativna presejalna oznaka in ne validiran vzročni prag.",
    ), styles["small"])]

    story += _section_title(_t(lang, "Identified ergonomic factors", "Εντοπισμένοι εργονομικοί παράγοντες", "Ugotovljeni ergonomski dejavniki"), styles)
    status_titles = [
        ("priority", _t(lang, "Immediate priority", "Άμεση προτεραιότητα", "Takojšnja prioriteta")),
        ("attention", _t(lang, "Needs attention", "Χρειάζεται προσοχή", "Zahteva pozornost")),
        ("information", _t(lang, "Additional context", "Πρόσθετες πληροφορίες", "Dodatni kontekst")),
    ]
    any_finding = False
    for status, title in status_titles:
        subset = [f for f in findings if isinstance(f, dict) and f.get("status") == status]
        if not subset:
            continue
        any_finding = True
        story += [Paragraph(_escape(title), styles["h2"])]
        for finding in subset:
            story += [Paragraph(f"<b>{_escape(finding.get('title', ''))}</b><br/>{_escape(finding.get('detail', ''))}", styles["body"]), Spacer(1, 2 * mm)]
    if not any_finding:
        story += [Paragraph(_t(lang, "No priority ergonomic exposure was identified from the entered information.", "Δεν εντοπίστηκε εργονομικός παράγοντας υψηλής προτεραιότητας από τα στοιχεία που καταχωρίστηκαν.", "Iz vnesenih podatkov ni bila ugotovljena ergonomska izpostavljenost visoke prioritete."), styles["body"])]

    story += _section_title(_t(lang, "Preventive and improvement measures", "Μέτρα πρόληψης και βελτίωσης", "Preventivni ukrepi in izboljšave"), styles)
    priority_titles = [
        ("now", _t(lang, "Implement first", "Να εφαρμοστούν πρώτα", "Izvedi najprej")),
        ("soon", _t(lang, "Next actions", "Επόμενες ενέργειες", "Naslednji ukrepi")),
        ("maintain", _t(lang, "Good practices to maintain", "Καλές πρακτικές που πρέπει να διατηρηθούν", "Dobre prakse, ki jih je treba ohraniti")),
    ]
    for key, title in priority_titles:
        subset = [r for r in recommendations if isinstance(r, dict) and r.get("priority") == key]
        if not subset:
            continue
        story += [Paragraph(_escape(title), styles["h2"])]
        for rec in subset:
            card = Table(
                [[Paragraph(f"<b>{_escape(rec.get('title', ''))}</b>", styles["body"])],
                 [Paragraph(_escape(rec.get("action", "")), styles["body"])],
                 [Paragraph(f"<b>{_t(lang, 'Why', 'Γιατί', 'Zakaj')}:</b> {_escape(rec.get('rationale', ''))}", styles["small"])]],
                colWidths=[170 * mm],
            )
            card.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GOLD if key == "now" else LIGHT_BLUE),
                ("BOX", (0, 0), (-1, -1), 0.35, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story += [card, Spacer(1, 3 * mm)]

    story += _section_title(_t(lang, "ROSA results", "Αποτελέσματα ROSA", "Rezultati ROSA"), styles)
    rosa_rows = [
        (_t(lang, "Chair ROSA", "ROSA καρέκλας", "ROSA - stol"), rosa.get("chair", "-")),
        (_t(lang, "Section B", "Ενότητα B", "Razdelek B"), rosa.get("section_b", "-")),
        (_t(lang, "Section C", "Ενότητα C", "Razdelek C"), rosa.get("section_c", "-")),
        (_t(lang, "Monitor & peripherals", "Οθόνη & περιφερειακά", "Zaslon in periferne naprave"), rosa.get("monitor_peripherals", "-")),
        (_t(lang, "ROSA final", "Τελικό ROSA", "Končni ROSA"), rosa.get("final", "-")),
    ]
    story += [_kv_table(rosa_rows, styles, bold_font)]

    if photos:
        story += _section_title(_t(lang, "Assessment photographs and comments", "Φωτογραφίες αξιολόγησης και σχόλια", "Fotografije ocene in komentarji"), styles)
        for idx, photo in enumerate(photos, start=1):
            photo_items = _photo_flowable(photo, styles)
            if not photo_items:
                continue
            story += [Paragraph(f"{_t(lang, 'Photo', 'Φωτογραφία', 'Fotografija')} {idx}", styles["h2"])]
            story += photo_items

    if comparison:
        story += _section_title(_t(lang, "Before vs after interventions", "Σύγκριση πριν και μετά τις παρεμβάσεις", "Primerjava pred in po ukrepih"), styles)
        comp_rows = [
            (_t(lang, "Baseline ROSA", "ROSA πριν", "ROSA prej"), comparison.get("baseline_rosa", "-")),
            (_t(lang, "Follow-up ROSA", "ROSA μετά", "ROSA po ukrepih"), comparison.get("followup_rosa", "-")),
            (_t(lang, "High-priority issues before / after", "Θέματα άμεσης προτεραιότητας πριν / μετά", "Težave visoke prioritete prej / potem"), f"{comparison.get('baseline_priority_findings', '-')} -> {comparison.get('followup_priority_findings', '-')}"),
            (_t(lang, "Attention issues before / after", "Θέματα προσοχής πριν / μετά", "Težave, ki zahtevajo pozornost, prej / potem"), f"{comparison.get('baseline_attention_findings', '-')} -> {comparison.get('followup_attention_findings', '-')}"),
        ]
        story += [_kv_table(comp_rows, styles, bold_font)]
        if comparison.get("interventions_notes"):
            story += [Paragraph(_t(lang, "Interventions implemented", "Παρεμβάσεις που εφαρμόστηκαν", "Izvedeni ukrepi"), styles["h2"]),
                      Paragraph(_escape(comparison.get("interventions_notes")), styles["body"])]
        for key, heading in [
            ("improvements", _t(lang, "Observed improvements", "Βελτιώσεις που καταγράφηκαν", "Zabeležene izboljšave")),
            ("new_issues", _t(lang, "New issues identified", "Νέα ζητήματα που εντοπίστηκαν", "Nove ugotovljene težave")),
            ("remaining_issues", _t(lang, "Issues still requiring attention", "Ζητήματα που εξακολουθούν να χρειάζονται προσοχή", "Težave, ki še vedno zahtevajo pozornost")),
        ]:
            values = comparison.get(key) or []
            if values:
                story += [Paragraph(_escape(heading), styles["h2"])]
                for value in values:
                    story += [Paragraph(f"- {_escape(value)}", styles["body"])]

    story += _section_title(_t(lang, "Conclusion", "Συμπέρασμα", "Zaključek"), styles)
    story += [Paragraph(_t(
        lang,
        "This report should be interpreted together with the observed task, worker feedback and organisational context. Proposed actions are intended to reduce modifiable ergonomic exposures and support follow-up. Persistent, worsening or function-limiting symptoms should follow the appropriate occupational-health or clinical pathway.",
        "Η έκθεση πρέπει να ερμηνεύεται μαζί με την παρατήρηση της εργασίας, την ανατροφοδότηση του εργαζομένου και το οργανωτικό πλαίσιο. Οι προτεινόμενες ενέργειες στοχεύουν στη μείωση τροποποιήσιμων εργονομικών εκθέσεων και στην υποστήριξη της επανεκτίμησης. Επίμονα, επιδεινούμενα ή λειτουργικά περιοριστικά συμπτώματα πρέπει να ακολουθούν την κατάλληλη οδό επαγγελματικής υγείας ή κλινικής αξιολόγησης.",
        "Poročilo je treba razlagati skupaj z opazovanjem naloge, povratnimi informacijami zaposlenega in organizacijskim kontekstom. Predlagani ukrepi so namenjeni zmanjšanju spremenljivih ergonomskih izpostavljenosti in podpori ponovni oceni. Vztrajni, slabšajoči se ali funkcionalno omejujoči simptomi naj sledijo ustrezni poti medicine dela oziroma klinične obravnave.",
    ), styles["body"])]

    doc.build(
        story,
        onFirstPage=lambda canvas, d: _page_header_footer(canvas, d, logo_path, regular_font, bold_font),
        onLaterPages=lambda canvas, d: _page_header_footer(canvas, d, logo_path, regular_font, bold_font),
    )
    return out.getvalue()
