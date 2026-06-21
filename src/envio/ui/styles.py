"""CSS global da aplicação."""

from src.envio.config.theme import BG, BORDER, CARD, INK, MUTED, NEON, NEON_SOFT


def build_global_css() -> str:
  return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800;900&family=Inter:wght@400;500;600&display=swap');

    :root {{ color-scheme: light; }}

    html, body, [class*="css"], .stApp {{
        font-family: 'Inter', sans-serif;
        background-color: {BG} !important;
        color: {INK} !important;
    }}

    h1, h2, h3, h4 {{
        font-family: 'Poppins', sans-serif !important;
        font-weight: 800 !important;
        color: {INK} !important;
        letter-spacing: -0.02em;
    }}
    h1 {{ font-weight: 900 !important; }}

    .block-container {{ padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1400px; }}

    .hero {{
        background: linear-gradient(120deg, #ffffff 0%, #F2FFF9 60%, {NEON_SOFT}33 100%);
        border: 1px solid {NEON}55;
        border-radius: 20px;
        padding: 22px 28px;
        margin-bottom: 18px;
        box-shadow: 0 8px 30px rgba(57,255,156,0.08);
    }}
    .hero h1 {{ margin: 0; font-size: 2rem; }}
    .hero p  {{ margin: 4px 0 0 0; color: {MUTED}; font-size: 0.95rem; }}

    .metric-card {{
        background: {CARD};
        border: 1px solid {BORDER};
        border-left: 6px solid {NEON};
        border-radius: 16px;
        padding: 18px 20px;
        box-shadow: 0 4px 18px rgba(15,27,45,0.04);
        height: 100%;
    }}
    .metric-card .label {{
        color: {MUTED};
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}
    .metric-card .value {{
        font-family: 'Poppins', sans-serif;
        font-weight: 900;
        font-size: 1.9rem;
        color: {INK};
        margin-top: 4px;
        line-height: 1.1;
    }}
    .metric-card .sub {{
        font-size: 0.8rem;
        color: {MUTED};
        margin-top: 4px;
    }}
    .metric-card .accent {{ color: #0C8560; font-weight: 700; }}

    .goal-card {{
        background: linear-gradient(135deg, {NEON}15, #ffffff);
        border: 1px solid {NEON};
        border-radius: 16px;
        padding: 18px 22px;
    }}
    .progress-track {{
        background: #EAF3EE;
        height: 14px;
        border-radius: 999px;
        overflow: hidden;
        margin-top: 10px;
    }}
    .progress-fill {{
        height: 100%;
        background: linear-gradient(90deg, {NEON}, #0C8560);
        border-radius: 999px;
    }}

    .section-card {{
        background: {CARD};
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 20px 22px;
        box-shadow: 0 4px 18px rgba(15,27,45,0.04);
        margin-bottom: 8px;
    }}
    .section-card .section-title {{
        font-family: 'Poppins', sans-serif;
        font-weight: 800;
        font-size: 1.05rem;
        color: {INK};
        margin: 0 0 4px 0;
    }}
    .section-card .section-caption {{
        color: {MUTED};
        font-size: 0.82rem;
        margin: 0 0 14px 0;
    }}


    section[data-testid="stSidebar"] {{
        background: #ffffff !important;
        border-right: 1px solid #ECEFF3;
    }}
    section[data-testid="stSidebar"] > div {{ background: #ffffff !important; }}
    section[data-testid="stSidebar"] h2 {{ font-size: 1rem; }}

    [data-testid="stWidgetLabel"] p,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stCaptionContainer"] p,
    .stRadio label p,
    label[data-testid="stWidgetLabel"] {{ color: {INK} !important; }}

    input, textarea, select {{ color-scheme: light !important; }}

    [data-baseweb="base-input"],
    [data-baseweb="input"],
    [data-baseweb="textarea"] {{
        background-color: {CARD} !important;
        color: {INK} !important;
        border-color: {BORDER} !important;
    }}

    [data-baseweb="select"] > div,
    div[data-baseweb="select"] > div[role="button"] {{
        background-color: {CARD} !important;
        color: {INK} !important;
        border-color: {BORDER} !important;
    }}
    [data-baseweb="select"] svg {{ fill: {MUTED} !important; }}

    [data-baseweb="tag"] {{
        background-color: {NEON}33 !important;
        color: {INK} !important;
        border: 1px solid {NEON}66 !important;
    }}
    [data-baseweb="tag"] span {{ color: {INK} !important; }}

    [data-testid="stDateInput"] input,
    [data-testid="stNumberInput"] input {{
        background-color: {CARD} !important;
        color: {INK} !important;
        border: 1px solid {BORDER} !important;
    }}
    [data-testid="stNumberInput"] button {{
        background-color: #F2FFF9 !important;
        color: {INK} !important;
        border-color: {BORDER} !important;
    }}

    .stRadio > div {{ background: transparent !important; }}
    .stRadio label[data-baseweb="radio"] > div:first-child {{
        background-color: {CARD} !important;
        border-color: {BORDER} !important;
    }}
    .stRadio label[data-baseweb="radio"][aria-checked="true"] > div:first-child {{
        background-color: {NEON} !important;
        border-color: #0C8560 !important;
    }}

    [data-testid="stFileUploader"] section {{
        background: #F8FCFA !important;
        border: 1px dashed {NEON}66 !important;
        border-radius: 12px !important;
    }}
    [data-testid="stFileUploader"] section span,
    [data-testid="stFileUploader"] section small {{ color: {MUTED} !important; }}
    [data-testid="stFileUploader"] button {{
        background-color: {NEON} !important;
        color: {INK} !important;
        border: none !important;
        font-weight: 600 !important;
    }}

    div[data-baseweb="popover"],
    ul[data-baseweb="menu"] {{
        background-color: {CARD} !important;
        border: 1px solid {BORDER} !important;
    }}
    li[data-baseweb="option"] {{
        background-color: {CARD} !important;
        color: {INK} !important;
    }}
    li[data-baseweb="option"]:hover {{ background-color: #F2FFF9 !important; }}

    .stDownloadButton button,
    .stButton > button {{
        background-color: {NEON} !important;
        color: {INK} !important;
        border: 1px solid #0C856055 !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }}
    .stDownloadButton button:hover,
    .stButton > button:hover {{
        background-color: {NEON_SOFT} !important;
        box-shadow: 0 4px 14px rgba(57,255,156,0.35) !important;
    }}

    [data-testid="stPlotlyChart"] {{
        background: {CARD};
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 8px 12px 4px 12px;
        margin-bottom: 16px;
        box-shadow: 0 4px 18px rgba(15,27,45,0.04);
    }}
    [data-testid="stPlotlyChart"] .g-gtitle,
    [data-testid="stPlotlyChart"] .infolayer .g-gtitle {{
        display: none !important;
    }}

    .custom-table-wrapper {{
        background: {CARD};
        border: 1px solid {BORDER};
        border-radius: 14px;
        overflow: auto;
        max-height: 520px;
    }}
    .custom-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.84rem;
    }}
    .custom-table thead th {{
        background: #0C8560 !important;
        color: #FFFFFF !important;
        font-weight: 700;
        text-transform: uppercase;
        font-size: 0.68rem;
        letter-spacing: 0.07em;
        padding: 13px 14px;
        border-bottom: 2px solid #0C8560;
        position: sticky;
        top: 0;
        z-index: 2;
        white-space: nowrap;
        text-align: left;
    }}
    .custom-table thead th.num {{
        text-align: center;
    }}
    .custom-table tbody tr.even {{ background: #FAFCFB; }}
    .custom-table tbody tr.odd  {{ background: {CARD}; }}
    .custom-table tbody tr:hover {{ background: #F2FFF9 !important; }}
    .custom-table td {{
        padding: 11px 14px;
        border-bottom: 1px solid #ECEFF3;
        color: {INK};
        vertical-align: middle;
        text-align: left;
    }}
    .custom-table td.num {{
        font-variant-numeric: tabular-nums;
        font-weight: 600;
        color: #0C8560;
        text-align: center;
    }}
    .custom-table td.date {{ color: {MUTED}; font-size: 0.8rem; text-align: center; }}
    .badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
        background: {NEON}28;
        color: #047857;
        border: 1px solid {NEON}55;
    }}
    .badge-warn {{
        background: #FFF7ED;
        color: #C2410C;
        border-color: #FDBA74;
    }}
    </style>
    """
