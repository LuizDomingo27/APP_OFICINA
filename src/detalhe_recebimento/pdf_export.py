"""
pdf_export.py
=============
Geração do PDF executivo do painel "Detalhe do Recebimento".

Layout "moderno" reaproveitando o mesmo padrão visual (cores e estilo de
tabela) já usado em toda a aplicação — verde neon-aqua (#0E9F6E /
#0C8560) sobre fundo claro, cabeçalho de tabela em verde com texto
branco, linhas zebradas.

Usa reportlab (Platypus) — biblioteca pura Python, sem dependências de
sistema, já usada em outros relatórios internos da operação.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Table, TableStyle, Paragraph,
    Spacer, HRFlowable, FrameBreak,
)
from reportlab.platypus.flowables import KeepTogether

# ---------------------------------------------------------------------------
# Paleta (idêntica à do app — ver config.py)
# ---------------------------------------------------------------------------
COR_PRIMARIA   = colors.HexColor("#0E9F6E")
COR_SECUNDARIA = colors.HexColor("#0C8560")
COR_TEXTO      = colors.HexColor("#1A2E25")
COR_MUTED      = colors.HexColor("#6B8F7E")
COR_BORDA      = colors.HexColor("#D0F0E5")
COR_FUNDO_CARD = colors.HexColor("#F0FDF8")
COR_ZEBRA      = colors.HexColor("#FAFCFB")
COR_BRANCO     = colors.white

_ACCENTS = [
    colors.HexColor("#0E9F6E"), colors.HexColor("#00B4D8"),
    colors.HexColor("#14B8A6"), colors.HexColor("#2DD4BF"),
    colors.HexColor("#00897B"), colors.HexColor("#5EEAD4"),
    colors.HexColor("#0C8560"), colors.HexColor("#43AA8B"),
]


def _fmt_int(v) -> str:
    try:
        return f"{int(round(float(v))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def _styles():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "TituloPDF", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=18, textColor=COR_BRANCO, alignment=TA_LEFT, leading=22,
        ),
        "subtitulo": ParagraphStyle(
            "SubtituloPDF", parent=base["Normal"], fontName="Helvetica",
            fontSize=10, textColor=COR_BRANCO, alignment=TA_LEFT, leading=13,
        ),
        "secao": ParagraphStyle(
            "SecaoPDF", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=12.5, textColor=COR_TEXTO, spaceBefore=14, spaceAfter=6,
        ),
        "card_label": ParagraphStyle(
            "CardLabel", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7.7, textColor=COR_MUTED, alignment=TA_LEFT,
        ),
        "card_value": ParagraphStyle(
            "CardValue", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=16, textColor=COR_TEXTO, alignment=TA_LEFT, leading=18,
        ),
        "card_sub": ParagraphStyle(
            "CardSub", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.3, textColor=COR_MUTED, alignment=TA_LEFT,
        ),
        "rodape": ParagraphStyle(
            "Rodape", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.5, textColor=COR_MUTED, alignment=TA_LEFT,
        ),
        "th": ParagraphStyle(
            "TH", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8, textColor=COR_BRANCO, alignment=TA_LEFT,
        ),
        "th_num": ParagraphStyle(
            "THNum", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8, textColor=COR_BRANCO, alignment=TA_CENTER,
        ),
        "td": ParagraphStyle(
            "TD", parent=base["Normal"], fontName="Helvetica",
            fontSize=8.3, textColor=COR_TEXTO, alignment=TA_LEFT,
        ),
        "td_num": ParagraphStyle(
            "TDNum", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8.3, textColor=COR_PRIMARIA, alignment=TA_CENTER,
        ),
        "td_total": ParagraphStyle(
            "TDTotal", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8.6, textColor=COR_TEXTO, alignment=TA_LEFT,
        ),
        "td_total_num": ParagraphStyle(
            "TDTotalNum", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8.6, textColor=COR_SECUNDARIA, alignment=TA_CENTER,
        ),
    }


def _header_band(styles, periodo_label: str, filtros_label: str, largura: float):
    """Faixa colorida de topo com título e período filtrado."""
    cell = [
        Paragraph("Detalhe do Recebimento", styles["titulo"]),
        Spacer(1, 4),
        Paragraph(f"Período (Envio): {periodo_label}", styles["subtitulo"]),
    ]
    if filtros_label:
        cell.append(Paragraph(filtros_label, styles["subtitulo"]))
    cell.append(Spacer(1, 2))
    cell.append(Paragraph(
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle("ts", parent=styles["subtitulo"], fontSize=8, textColor=colors.HexColor("#D7F5EA")),
    ))

    tbl = Table([[cell]], colWidths=[largura])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COR_PRIMARIA),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    return tbl


def _kpi_cards(styles, resumo, largura: float):
    """Linha de cards de indicadores gerais (peças, minutos, ordens, operações)."""
    cartoes = [
        ("TOTAL DE PEÇAS", _fmt_int(resumo.total_pecas), f"{resumo.total_ordens} ordens no período"),
        ("TOTAL DE MINUTOS", _fmt_int(resumo.total_minutos), f"≈ {resumo.total_minutos/60:,.0f}h".replace(",", ".")),
        ("OPERAÇÕES", str(resumo.qtd_operacoes), "status distintos"),
        ("DIAS NO PERÍODO", str(resumo.dias_periodo), "dias com envio"),
    ]
    col_w = largura / 4
    linha = []
    for label, valor, sub in cartoes:
        conteudo = [
            Paragraph(label, styles["card_label"]),
            Spacer(1, 3),
            Paragraph(valor, styles["card_value"]),
            Spacer(1, 2),
            Paragraph(sub, styles["card_sub"]),
        ]
        linha.append(conteudo)

    tbl = Table([linha], colWidths=[col_w] * 4)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, -1), COR_FUNDO_CARD),
        ("BOX", (0, 0), (0, 0), 0.75, COR_BORDA),
        ("BOX", (1, 0), (1, 0), 0.75, COR_BORDA),
        ("BOX", (2, 0), (2, 0), 0.75, COR_BORDA),
        ("BOX", (3, 0), (3, 0), 0.75, COR_BORDA),
        ("LINEBEFORE", (0, 0), (0, 0), 3, COR_PRIMARIA),
        ("LINEBEFORE", (1, 0), (1, 0), 3, colors.HexColor("#00B4D8")),
        ("LINEBEFORE", (2, 0), (2, 0), 3, colors.HexColor("#14B8A6")),
        ("LINEBEFORE", (3, 0), (3, 0), 3, colors.HexColor("#0C8560")),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    tbl.setStyle(TableStyle(estilo))
    return tbl


def _tabela_resumo_operacao(styles, df_op: pd.DataFrame, largura: float):
    """Tabela 'Resumo por Operação' — Operação | Peças | Minutos | Ordens."""
    header = [
        Paragraph("Operação", styles["th"]),
        Paragraph("Peças", styles["th_num"]),
        Paragraph("Minutos", styles["th_num"]),
        Paragraph("Ordens", styles["th_num"]),
    ]
    linhas = [header]
    for _, row in df_op.iterrows():
        linhas.append([
            Paragraph(str(row["operacao"]), styles["td"]),
            Paragraph(_fmt_int(row["pecas"]), styles["td_num"]),
            Paragraph(_fmt_int(row["minutos"]), styles["td_num"]),
            Paragraph(_fmt_int(row["ordens"]), styles["td_num"]),
        ])

    total_pecas = df_op["pecas"].sum() if not df_op.empty else 0
    total_min = df_op["minutos"].sum() if not df_op.empty else 0
    total_ordens = df_op["ordens"].sum() if not df_op.empty else 0
    linhas.append([
        Paragraph("TOTAL", styles["td_total"]),
        Paragraph(_fmt_int(total_pecas), styles["td_total_num"]),
        Paragraph(_fmt_int(total_min), styles["td_total_num"]),
        Paragraph(_fmt_int(total_ordens), styles["td_total_num"]),
    ])

    col_w = [largura * 0.46, largura * 0.18, largura * 0.18, largura * 0.18]
    tbl = Table(linhas, colWidths=col_w, repeatRows=1)
    tbl.setStyle(_estilo_tabela(len(linhas)))
    return tbl


def _fmt_data(v) -> str:
    try:
        if pd.isna(v):
            return "-"
        return pd.Timestamp(v).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return "-"


def _tabela_detalhada(styles, df_detalhe: pd.DataFrame, col_recebimento: str,
                       col_mp: str, col_oficina: str, col_ordem_mestre: str,
                       col_envio: str, col_qtd: str, col_minutos: str,
                       largura: float):
    """Tabela 'Detalhamento por Operação, MP, Oficina, OM e Data do Envio'
    (item 2/3 do pedido do gestor) — 1 linha por ordem, sem agregação."""
    header = [
        Paragraph("Operação", styles["th"]),
        Paragraph("MP", styles["th"]),
        Paragraph("Oficina", styles["th"]),
        Paragraph("OM", styles["th"]),
        Paragraph("Data do Envio", styles["th"]),
        Paragraph("Peças", styles["th_num"]),
        Paragraph("Minutos", styles["th_num"]),
    ]
    linhas = [header]
    for _, row in df_detalhe.iterrows():
        om = row[col_ordem_mestre]
        linhas.append([
            Paragraph(str(row[col_recebimento]), styles["td"]),
            Paragraph(str(row[col_mp]), styles["td"]),
            Paragraph(str(row[col_oficina]), styles["td"]),
            Paragraph(str(om) if om else "-", styles["td"]),
            Paragraph(_fmt_data(row[col_envio]), styles["td"]),
            Paragraph(_fmt_int(row[col_qtd]), styles["td_num"]),
            Paragraph(_fmt_int(row[col_minutos]), styles["td_num"]),
        ])

    total_pecas = df_detalhe[col_qtd].sum() if not df_detalhe.empty else 0
    total_min = df_detalhe[col_minutos].sum() if not df_detalhe.empty else 0
    linhas.append([
        Paragraph("TOTAL GERAL", styles["td_total"]),
        Paragraph("", styles["td_total"]),
        Paragraph("", styles["td_total"]),
        Paragraph("", styles["td_total"]),
        Paragraph("", styles["td_total"]),
        Paragraph(_fmt_int(total_pecas), styles["td_total_num"]),
        Paragraph(_fmt_int(total_min), styles["td_total_num"]),
    ])

    col_w = [
        largura * 0.18, largura * 0.09, largura * 0.29, largura * 0.13,
        largura * 0.13, largura * 0.09, largura * 0.09,
    ]
    tbl = Table(linhas, colWidths=col_w, repeatRows=1)
    tbl.setStyle(_estilo_tabela(len(linhas)))
    return tbl


def _estilo_tabela(n_linhas: int) -> TableStyle:
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), COR_PRIMARIA),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, COR_SECUNDARIA),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, colors.HexColor("#ECEFF3")),
        ("LINEABOVE", (0, -1), (-1, -1), 1.2, COR_SECUNDARIA),
        ("BACKGROUND", (0, -1), (-1, -1), COR_FUNDO_CARD),
    ]
    # Zebra striping nas linhas de dados (entre o cabeçalho e o total)
    for i in range(1, n_linhas - 1):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), COR_ZEBRA))
    return TableStyle(cmds)


def gerar_pdf_detalhe_recebimento(
    df_op: pd.DataFrame,
    df_detalhe: pd.DataFrame,
    resumo,
    periodo_label: str,
    filtros_label: str,
    col_recebimento: str,
    col_mp: str,
    col_oficina: str,
    col_ordem_mestre: str,
    col_envio: str,
    col_qtd: str,
    col_minutos: str,
) -> bytes:
    """Gera o PDF executivo completo e retorna os bytes do arquivo.

    Parâmetros
    ----------
    df_op       : saída de metrics.agg_by_operacao() — operacao/pecas/minutos/ordens
    df_detalhe  : saída de metrics.agg_detalhado()   — 1 linha por ordem, com
                  Operação/MP/Oficina/OM/Envio/Peças/Minutos
    resumo      : metrics.ResumoGeral do período filtrado
    periodo_label, filtros_label : textos descritivos exibidos no cabeçalho
    col_*       : nomes reais das colunas em df_detalhe (config.COL_*)
    """
    buf = BytesIO()
    page_size = landscape(A4)
    margem = 16 * mm
    largura_util = page_size[0] - 2 * margem

    doc = BaseDocTemplate(
        buf, pagesize=page_size,
        leftMargin=margem, rightMargin=margem,
        topMargin=margem, bottomMargin=margem,
        title="Detalhe do Recebimento",
    )
    frame = Frame(margem, margem, largura_util, page_size[1] - 2 * margem, id="main")

    def _rodape(canvas, _doc):
        canvas.saveState()
        canvas.setStrokeColor(COR_BORDA)
        canvas.setLineWidth(0.6)
        y = margem - 6
        canvas.line(margem, y, page_size[0] - margem, y)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(COR_MUTED)
        canvas.drawString(margem, y - 11, "Central das Oficinas — Painel de Recebimento")
        canvas.drawRightString(page_size[0] - margem, y - 11, f"Página {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_rodape)])

    styles = _styles()
    elementos = []

    elementos.append(_header_band(styles, periodo_label, filtros_label, largura_util))
    elementos.append(Spacer(1, 14))

    elementos.append(_kpi_cards(styles, resumo, largura_util))
    elementos.append(Spacer(1, 18))

    elementos.append(Paragraph("Resumo por Operação", styles["secao"]))
    elementos.append(_tabela_resumo_operacao(styles, df_op, largura_util))
    elementos.append(Spacer(1, 18))

    elementos.append(Paragraph("Detalhamento por Operação, MP, Oficina, OM e Data do Envio", styles["secao"]))
    elementos.append(_tabela_detalhada(
        styles, df_detalhe, col_recebimento, col_mp, col_oficina,
        col_ordem_mestre, col_envio, col_qtd, col_minutos,
        largura_util,
    ))

    doc.build(elementos)
    return buf.getvalue()
