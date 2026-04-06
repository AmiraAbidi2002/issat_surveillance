"""
rapports/generateur_pdf.py
Générateur PDF du planning de surveillance — ISSAT Sousse
Copiez ce fichier dans : issat_surveillance/rapports/generateur_pdf.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.platypus.flowables import KeepTogether
from io import BytesIO
from datetime import date
from collections import defaultdict

# ── Palette couleurs ISSAT ─────────────────────────────────────────────
BLEU_ISSAT  = colors.HexColor("#1F4E79")
BLEU_CLAIR  = colors.HexColor("#BDD7EE")
BLEU_MED    = colors.HexColor("#2E75B6")
VERT_OK     = colors.HexColor("#E2EFDA")
VERT_FONCE  = colors.HexColor("#375623")
ORANGE_WARN = colors.HexColor("#FCE4D6")
ORANGE_FONC = colors.HexColor("#833C00")
ROUGE_ALERT = colors.HexColor("#FFE4E4")
ROUGE_FONCE = colors.HexColor("#C00000")
GRIS_CLAIR  = colors.HexColor("#F2F2F2")
GRIS_MED    = colors.HexColor("#D9D9D9")
BLANC       = colors.white
NOIR        = colors.black

# ── Styles typographiques ──────────────────────────────────────────────
_base = getSampleStyleSheet()

def _style(name, parent='Normal', **kw):
    return ParagraphStyle(name, parent=_base[parent], **kw)

S_TITRE      = _style('Titre',     fontSize=20, textColor=BLEU_ISSAT,
                       alignment=TA_CENTER, spaceAfter=4,
                       fontName='Helvetica-Bold')
S_SOUS_TITRE = _style('SousTitre', fontSize=12, textColor=BLEU_MED,
                       alignment=TA_CENTER, spaceAfter=2)
S_SECTION    = _style('Section',   fontSize=13, textColor=BLANC,
                       fontName='Helvetica-Bold', alignment=TA_LEFT)
S_CELL       = _style('Cell',      fontSize=8.5, leading=11)
S_CELL_BOLD  = _style('CellBold',  fontSize=8.5,
                       fontName='Helvetica-Bold', leading=11)
S_CELL_CTR   = _style('CellCtr',   fontSize=8.5,
                       alignment=TA_CENTER, leading=11)
S_NOTE       = _style('Note',      fontSize=8,
                       textColor=colors.gray, alignment=TA_LEFT)
S_LEGENDE    = _style('Legende',   fontSize=8, leading=10)


# ══════════════════════════════════════════════════════════════════════
# HELPERS INTERNES
# ══════════════════════════════════════════════════════════════════════

def _header_footer(canvas, doc):
    """Bandeau haut + pied de page sur chaque page."""
    canvas.saveState()
    w, h = A4

    # Bandeau bleu en haut
    canvas.setFillColor(BLEU_ISSAT)
    canvas.rect(0, h - 1.4 * cm, w, 1.4 * cm, fill=1, stroke=0)
    canvas.setFillColor(BLANC)
    canvas.setFont('Helvetica-Bold', 10)
    canvas.drawString(1 * cm, h - 0.95 * cm,
                      "ISSAT Sousse — Planification des Surveillances")
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(w - 1 * cm, h - 0.95 * cm, doc.title or "")

    # Ligne décorative sous le bandeau
    canvas.setStrokeColor(BLEU_CLAIR)
    canvas.setLineWidth(2)
    canvas.line(0, h - 1.45 * cm, w, h - 1.45 * cm)

    # Pied de page
    canvas.setStrokeColor(GRIS_MED)
    canvas.setLineWidth(0.5)
    canvas.line(1 * cm, 1.1 * cm, w - 1 * cm, 1.1 * cm)
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(colors.gray)
    canvas.drawString(1 * cm, 0.65 * cm,
                      "Document généré automatiquement — ISSAT Sousse 2025/2026")
    canvas.drawRightString(w - 1 * cm, 0.65 * cm, f"Page {doc.page}")
    canvas.restoreState()


def _section_header(titre, couleur=BLEU_ISSAT):
    """Bloc titre de section avec fond coloré."""
    t = Table([[Paragraph(f"  {titre}", S_SECTION)]], colWidths=[19 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), couleur),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
    ]))
    return t


def _hex(c):
    """Convertit une couleur ReportLab en chaîne hex HTML."""
    return f"#{int(c.red*255):02X}{int(c.green*255):02X}{int(c.blue*255):02X}"


def _legende():
    """Barre de légende colorée pour la page de garde."""
    items = [
        (VERT_OK,     VERT_FONCE,  "Examen complet"),
        (ORANGE_WARN, ORANGE_FONC, "Examen incomplet"),
        (ROUGE_ALERT, ROUGE_FONCE, "Alerte"),
        (BLEU_CLAIR,  BLEU_ISSAT,  "Ligne paire"),
        (GRIS_CLAIR,  NOIR,        "Ligne impaire"),
    ]
    row = []
    for bg, fg, label in items:
        cell = [[Paragraph(
            f'<font color="{_hex(fg)}">&#9632;</font> {label}',
            S_LEGENDE)]]
        t = Table(cell, colWidths=[3.5 * cm])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), bg),
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('BOX',           (0, 0), (-1, -1), 0.5, GRIS_MED),
        ]))
        row.append(t)
    outer = Table([row], colWidths=[3.5 * cm] * 5)
    outer.setStyle(TableStyle([
        ('LEFTPADDING',  (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    return outer


# ══════════════════════════════════════════════════════════════════════
# GÉNÉRATEUR PRINCIPAL
# ══════════════════════════════════════════════════════════════════════

def generer_pdf_planning(surveillances_data, enseignants_data,
                          examens_data, alertes_data,
                          titre_doc="Planning des Surveillances"):
    """
    Génère le PDF complet et retourne un BytesIO.

    Paramètres
    ----------
    surveillances_data : list[dict]
        Clés : enseignant, date, horaire, salle, matiere, classe, role
    enseignants_data : list[dict]
        Clés : nom, dept, heures_ens, heures_abs, dues, effectuees
    examens_data : list[dict]
        Clés : matiere, classe, date, horaire, salle, nb_etudiants,
               nb_requis, surveillants, complet
    alertes_data : list[dict]
        Clés : enseignant, statut, ecart
    titre_doc : str
        Titre affiché en page de garde et en-tête.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1 * cm, rightMargin=1 * cm,
        topMargin=2 * cm,  bottomMargin=1.8 * cm,
        title=titre_doc,
        author="ISSAT Sousse"
    )
    doc.title = titre_doc
    story = []

    nb_examens     = len(examens_data)
    nb_couverts    = sum(1 for e in examens_data if e['complet'])
    nb_surv        = len(surveillances_data)
    nb_enseignants = len(enseignants_data)

    # ──────────────────────────────────────────────────────────────────
    # PAGE DE GARDE
    # ──────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("ISSAT Sousse", S_SOUS_TITRE))
    story.append(Paragraph(
        "Institut Supérieur des Sciences Appliquées"
        "<br/>et de Technologie de Sousse", S_SOUS_TITRE))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=2, color=BLEU_ISSAT))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(titre_doc, S_TITRE))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="60%", thickness=1, color=BLEU_CLAIR))
    story.append(Spacer(1, 1 * cm))

    stats = [
        ["Examens planifiés",     str(nb_examens)],
        ["Examens couverts",      f"{nb_couverts} / {nb_examens}"],
        ["Affectations totales",  str(nb_surv)],
        ["Enseignants impliqués", str(nb_enseignants)],
        ["Année universitaire",   "2025 / 2026"],
        ["Date de génération",    date.today().strftime("%d/%m/%Y")],
    ]
    t_stats = Table(stats, colWidths=[7 * cm, 5 * cm])
    t_stats.setStyle(TableStyle([
        ('BACKGROUND',     (0, 0), (0, -1), BLEU_CLAIR),
        ('BACKGROUND',     (1, 0), (1, -1), GRIS_CLAIR),
        ('TEXTCOLOR',      (0, 0), (0, -1), BLEU_ISSAT),
        ('FONTNAME',       (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME',       (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, -1), 10),
        ('ALIGN',          (0, 0), (0, -1), 'LEFT'),
        ('ALIGN',          (1, 0), (1, -1), 'CENTER'),
        ('TOPPADDING',     (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING',  (0, 0), (-1, -1), 7),
        ('LEFTPADDING',    (0, 0), (-1, -1), 10),
        ('BOX',            (0, 0), (-1, -1), 0.5, BLEU_MED),
        ('INNERGRID',      (0, 0), (-1, -1), 0.3, GRIS_MED),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [BLEU_CLAIR, GRIS_CLAIR]),
    ]))
    story.append(Table([[t_stats]], colWidths=[19 * cm],
                       style=[('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    story.append(Spacer(1, 1 * cm))
    story.append(_legende())
    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────
    # SECTION 1 — PLANNING PAR EXAMEN
    # ──────────────────────────────────────────────────────────────────
    story.append(_section_header("1.  Planning par examen"))
    story.append(Spacer(1, 0.3 * cm))

    hdrs1  = ["Matière", "Classe", "Date", "Horaire", "Salle",
               "Ét.", "Req.", "Surveillants assignés", "Statut"]
    col_w1 = [3.8*cm, 1.6*cm, 2*cm, 2.1*cm, 1.3*cm,
               0.8*cm, 0.8*cm, 5.2*cm, 1.4*cm]

    data1 = [[Paragraph(f"<b>{h}</b>", S_CELL_CTR) for h in hdrs1]]
    for exam in examens_data:
        fg   = VERT_FONCE if exam['complet'] else ORANGE_FONC
        stat = "Complet"  if exam['complet'] else "Incomplet"
        data1.append([
            Paragraph(exam['matiere'],          S_CELL),
            Paragraph(exam['classe'],           S_CELL_CTR),
            Paragraph(exam['date'],             S_CELL_CTR),
            Paragraph(exam['horaire'],          S_CELL_CTR),
            Paragraph(exam['salle'],            S_CELL_CTR),
            Paragraph(str(exam['nb_etudiants']),S_CELL_CTR),
            Paragraph(str(exam['nb_requis']),   S_CELL_CTR),
            Paragraph(exam['surveillants'],     S_CELL),
            Paragraph(f'<font color="{_hex(fg)}"><b>{stat}</b></font>',
                      S_CELL_CTR),
        ])

    t1 = Table(data1, colWidths=col_w1, repeatRows=1)
    ts1 = TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), BLEU_ISSAT),
        ('TEXTCOLOR',     (0, 0), (-1, 0), BLANC),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN',         (0, 0), (-1, 0), 'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('BOX',           (0, 0), (-1, -1), 0.5, BLEU_MED),
        ('INNERGRID',     (0, 0), (-1, -1), 0.3, GRIS_MED),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ])
    for i, exam in enumerate(examens_data, 1):
        ts1.add('BACKGROUND', (0, i), (-1, i),
                VERT_OK if exam['complet'] else ORANGE_WARN)
    t1.setStyle(ts1)
    story.append(t1)
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        f"<i>Total : {nb_examens} examens — {nb_couverts} couverts — "
        f"{nb_examens - nb_couverts} incomplets</i>", S_NOTE))
    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────
    # SECTION 2 — PLANNING PAR ENSEIGNANT
    # ──────────────────────────────────────────────────────────────────
    story.append(_section_header("2.  Planning par enseignant"))
    story.append(Spacer(1, 0.3 * cm))

    par_ens = defaultdict(list)
    for s in surveillances_data:
        par_ens[s['enseignant']].append(s)

    hdrs2  = ["Date", "Horaire", "Salle", "Matière", "Classe", "Rôle"]
    col_w2 = [2*cm, 2.2*cm, 1.5*cm, 4*cm, 1.8*cm, 2.2*cm]

    for nom_ens, surv_list in sorted(par_ens.items()):
        surv_list.sort(key=lambda x: (x['date'], x['horaire']))
        ens_info  = next((e for e in enseignants_data if e['nom'] == nom_ens), {})
        titre_ens = (f"{nom_ens}  —  {ens_info.get('dept', '')}"
                     f"  |  Dues : {ens_info.get('dues', 0)}h"
                     f"  |  Effectuées : {ens_info.get('effectuees', 0):.1f}h")

        block = [_section_header(titre_ens, BLEU_MED), Spacer(1, 0.15 * cm)]
        data2 = [[Paragraph(f"<b>{h}</b>", S_CELL_CTR) for h in hdrs2]]

        for i, s in enumerate(surv_list):
            if s['role'] == 'responsable':
                role_color = BLEU_ISSAT
            elif s['role'] == 'remplacant':
                role_color = colors.HexColor("#E07000")
            else:
                role_color = NOIR

            bg = BLEU_CLAIR if i % 2 == 0 else GRIS_CLAIR
            data2.append([
                Paragraph(s['date'],    S_CELL_CTR),
                Paragraph(s['horaire'], S_CELL_CTR),
                Paragraph(s['salle'],   S_CELL_CTR),
                Paragraph(s['matiere'], S_CELL),
                Paragraph(s['classe'],  S_CELL_CTR),
                Paragraph(
                    f'<font color="{_hex(role_color)}">'
                    f'<b>{s["role"].capitalize()}</b></font>',
                    S_CELL_CTR),
            ])

        t2 = Table(data2, colWidths=col_w2, repeatRows=1)
        ts2 = TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), BLEU_MED),
            ('TEXTCOLOR',     (0, 0), (-1, 0), BLANC),
            ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('BOX',           (0, 0), (-1, -1), 0.5, BLEU_MED),
            ('INNERGRID',     (0, 0), (-1, -1), 0.3, GRIS_MED),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ])
        for i in range(1, len(data2)):
            ts2.add('BACKGROUND', (0, i), (-1, i),
                    BLEU_CLAIR if i % 2 == 1 else GRIS_CLAIR)
        t2.setStyle(ts2)
        block += [t2, Spacer(1, 0.5 * cm)]
        story.append(KeepTogether(block))

    story.append(PageBreak())

    # ──────────────────────────────────────────────────────────────────
    # SECTION 3 — RÉCAPITULATIF DES CHARGES
    # ──────────────────────────────────────────────────────────────────
    story.append(_section_header("3.  Récapitulatif des charges de surveillance"))
    story.append(Spacer(1, 0.3 * cm))

    hdrs3  = ["Enseignant", "Département", "H. Enseignement\n/semaine",
               "H. Absence\nreportées", "H. Dues\ntotal",
               "H. Effectuées", "Écart", "Statut"]
    col_w3 = [3.5*cm, 2.8*cm, 2*cm, 2*cm, 1.8*cm, 2*cm, 1.5*cm, 2.4*cm]

    data3 = [[Paragraph(f"<b>{h}</b>", S_CELL_CTR) for h in hdrs3]]
    ens_tries = sorted(enseignants_data, key=lambda e: e['nom'])

    for ens in ens_tries:
        ecart = ens.get('effectuees', 0) - ens.get('dues', 0)
        if   ecart >  0.5: statut, sc = "Depassement", ROUGE_FONCE
        elif ecart < -0.5: statut, sc = "Insuffisant",  ORANGE_FONC
        else:              statut, sc = "OK",            VERT_FONCE

        data3.append([
            Paragraph(f"<b>{ens['nom']}</b>",       S_CELL_BOLD),
            Paragraph(ens.get('dept', ''),          S_CELL),
            Paragraph(str(ens.get('heures_ens', 0)),S_CELL_CTR),
            Paragraph(str(ens.get('heures_abs', 0)),S_CELL_CTR),
            Paragraph(str(ens.get('dues', 0)),      S_CELL_CTR),
            Paragraph(f"{ens.get('effectuees',0):.1f}", S_CELL_CTR),
            Paragraph(f"{ecart:+.1f}",              S_CELL_CTR),
            Paragraph(f'<font color="{_hex(sc)}"><b>{statut}</b></font>',
                      S_CELL_CTR),
        ])

    t3 = Table(data3, colWidths=col_w3, repeatRows=1)
    ts3 = TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), BLEU_ISSAT),
        ('TEXTCOLOR',     (0, 0), (-1, 0), BLANC),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('BOX',           (0, 0), (-1, -1), 0.5, BLEU_MED),
        ('INNERGRID',     (0, 0), (-1, -1), 0.3, GRIS_MED),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',         (2, 0), (-1, -1), 'CENTER'),
    ])
    for i, ens in enumerate(ens_tries, 1):
        ecart = ens.get('effectuees', 0) - ens.get('dues', 0)
        if   ecart >  0.5: ts3.add('BACKGROUND', (0, i), (-1, i), ROUGE_ALERT)
        elif ecart < -0.5: ts3.add('BACKGROUND', (0, i), (-1, i), ORANGE_WARN)
        else:              ts3.add('BACKGROUND', (0, i), (-1, i), VERT_OK)
    t3.setStyle(ts3)
    story.append(t3)
    story.append(Spacer(1, 0.5 * cm))

    # ──────────────────────────────────────────────────────────────────
    # SECTION 4 — ALERTES (optionnelle)
    # ──────────────────────────────────────────────────────────────────
    if alertes_data:
        story.append(_section_header("4.  Alertes", ROUGE_FONCE))
        story.append(Spacer(1, 0.3 * cm))

        hdrs4  = ["Enseignant", "Type d'alerte", "Écart (h)"]
        col_w4 = [6 * cm, 8 * cm, 5 * cm]
        data4  = [[Paragraph(f"<b>{h}</b>", S_CELL_CTR) for h in hdrs4]]
        for a in alertes_data:
            data4.append([
                Paragraph(a['enseignant'], S_CELL_BOLD),
                Paragraph(a['statut'],     S_CELL_CTR),
                Paragraph(str(a['ecart']), S_CELL_CTR),
            ])
        t4 = Table(data4, colWidths=col_w4, repeatRows=1)
        t4.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), ROUGE_FONCE),
            ('TEXTCOLOR',     (0, 0), (-1, 0), BLANC),
            ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND',    (0, 1), (-1, -1), ROUGE_ALERT),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('BOX',           (0, 0), (-1, -1), 0.5, ROUGE_FONCE),
            ('INNERGRID',     (0, 0), (-1, -1), 0.3, GRIS_MED),
            ('ALIGN',         (1, 0), (-1, -1), 'CENTER'),
        ]))
        story.append(t4)

    # ── Build ──────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    buffer.seek(0)
    return buffer


# ══════════════════════════════════════════════════════════════════════
# FONCTION DJANGO — lit la BDD et appelle generer_pdf_planning()
# ══════════════════════════════════════════════════════════════════════

def generer_pdf_depuis_bdd():
    """
    Récupère les données depuis la BDD Django et génère le PDF complet.
    Retourne un BytesIO prêt à être envoyé en FileResponse.
    Appelée par rapports/views.py → ExporterPlanningPDFView
    """
    from surveillances.models import Surveillance
    from examens.models import Examen
    from users.models import Enseignant

    # ── Examens ────────────────────────────────────────────────────────
    examens_data = []
    for exam in Examen.objects.all().order_by('date_exam', 'heure_debut'):
        surv_qs     = Surveillance.objects.filter(examen=exam).select_related('enseignant__user')
        nb_assignes = surv_qs.count()
        noms_surv   = []
        for s in surv_qs:
            label = {'responsable': 'Responsable',
                     'surveillant': 'Surveillant',
                     'remplacant':  'Remplaçant'}.get(s.role, s.role)
            noms_surv.append(f"{s.enseignant.user.get_full_name()} ({label})")

        examens_data.append({
            'matiere':      exam.matiere,
            'classe':       exam.classe,
            'date':         exam.date_exam.strftime('%d/%m/%Y'),
            'horaire':      (f"{exam.heure_debut.strftime('%H:%M')}"
                             f"-{exam.heure_fin.strftime('%H:%M')}"),
            'salle':        exam.salle,
            'nb_etudiants': exam.nb_etudiants,
            'nb_requis':    exam.nb_surveillants_requis,
            'surveillants': ', '.join(noms_surv) if noms_surv else 'Aucun',
            'complet':      nb_assignes >= exam.nb_surveillants_requis,
        })

    # ── Surveillances ──────────────────────────────────────────────────
    surveillances_data = []
    for s in Surveillance.objects.select_related(
            'enseignant__user', 'examen').order_by(
            'enseignant__user__last_name', 'examen__date_exam'):
        surveillances_data.append({
            'enseignant': s.enseignant.user.get_full_name(),
            'date':       s.examen.date_exam.strftime('%d/%m/%Y'),
            'horaire':    (f"{s.examen.heure_debut.strftime('%H:%M')}"
                           f"-{s.examen.heure_fin.strftime('%H:%M')}"),
            'salle':      s.examen.salle,
            'matiere':    s.examen.matiere,
            'classe':     s.examen.classe,
            'role':       s.role,
        })

    # ── Enseignants ────────────────────────────────────────────────────
    enseignants_data = []
    for ens in Enseignant.objects.select_related('user', 'departement').all():
        heures_abs = max(0, ens.heures_surveillance_dues - ens.heures_enseignement)
        enseignants_data.append({
            'nom':        ens.user.get_full_name(),
            'dept':       ens.departement.nom if ens.departement else '',
            'heures_ens': ens.heures_enseignement,
            'heures_abs': round(heures_abs, 2),
            'dues':       ens.heures_surveillance_dues,
            'effectuees': round(ens.heures_effectuees, 2),
        })

    # ── Alertes ────────────────────────────────────────────────────────
    alertes_data = []
    for ens in Enseignant.objects.select_related('user').all():
        ecart = ens.heures_effectuees - ens.heures_surveillance_dues
        if ecart > 0.5:
            alertes_data.append({
                'enseignant': ens.user.get_full_name(),
                'statut':     'Dépassement de charge',
                'ecart':      round(ecart, 2),
            })
        elif ecart < -0.5:
            alertes_data.append({
                'enseignant': ens.user.get_full_name(),
                'statut':     'Charge insuffisante',
                'ecart':      round(ecart, 2),
            })

    return generer_pdf_planning(
        surveillances_data, enseignants_data,
        examens_data, alertes_data
    )