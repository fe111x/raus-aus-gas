"""
Design-System – Strava-inspiriert: klare Typografie, kräftige Akzente, viel Weißraum.
Farbpalette: Orange/Coral als Primärfarbe, Navy/Charcoal für Text, Grün für positive Metriken.
"""

# Strava-inspiriertes Farbsystem
COLORS = {
    # Primär: energetisches Orange
    "primary": "#FC5200",
    "primary_dark": "#CC4200",
    "primary_light": "#FF6B2C",
    # Akzent: Erfolg, positive Metriken
    "success": "#1DB954",
    "success_dark": "#169C46",
    # Warnung / Gas
    "warning": "#F25C54",
    # Neutrals
    "bg": "#FAFBFC",
    "bg_card": "#FFFFFF",
    "text": "#1A1D21",
    "text_muted": "#6B7280",
    "border": "#E5E7EB",
    "border_light": "#F3F4F6",
    # Chart-Farben (kohärent)
    "chart_1": "#FC5200",   # primary
    "chart_2": "#1DB954",   # success
    "chart_3": "#3B82F6",   # blau
    "chart_4": "#8B5CF6",   # violett
    "chart_5": "#F59E0B",   # amber
    "chart_6": "#64748B",   # slate
}

FONT_PRIMARY = '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
FONT_DISPLAY = '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'


def get_css() -> str:
    """Gibt das vollständige CSS für die App zurück."""
    c = COLORS
    return f'''
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    :root {{
        --primary: {c["primary"]};
        --primary-dark: {c["primary_dark"]};
        --success: {c["success"]};
        --bg: {c["bg"]};
        --bg-card: {c["bg_card"]};
        --text: {c["text"]};
        --text-muted: {c["text_muted"]};
        --border: {c["border"]};
    }}

    .stApp {{
        background: {c["bg"]} !important;
    }}

    .main .block-container {{
        padding: 2rem 2.5rem 3rem;
        max-width: 1280px;
    }}

    h1, h2, h3 {{
        font-family: {FONT_PRIMARY} !important;
        color: {c["text"]} !important;
        font-weight: 700 !important;
    }}

    h1 {{ font-size: 1.75rem !important; letter-spacing: -0.02em; }}
    h2 {{ font-size: 1.35rem !important; margin-top: 2rem !important; letter-spacing: -0.01em; }}
    h3 {{ font-size: 1.1rem !important; font-weight: 600 !important; }}

    p, li, span, label, .stMarkdown {{
        font-family: {FONT_PRIMARY} !important;
        color: {c["text"]} !important;
    }}

    label {{ color: {c["text"]} !important; font-weight: 500 !important; }}
    .stCaption {{ color: {c["text_muted"]} !important; font-size: 0.85rem !important; }}

    a {{
        color: {c["primary"]} !important;
        font-weight: 600 !important;
        text-decoration: none !important;
    }}
    a:hover {{ color: {c["primary_dark"]} !important; }}

    /* Header – Hero-Style */
    .raus-header {{
        background: linear-gradient(135deg, {c["primary"]} 0%, {c["primary_dark"]} 100%);
        border-radius: 20px;
        padding: 2rem 2.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 4px 24px rgba(252, 82, 0, 0.25);
        color: white !important;
    }}
    .raus-header h1 {{ color: white !important; margin: 0 !important; font-size: 1.9rem !important; }}
    .raus-header p {{ color: rgba(255,255,255,0.9) !important; margin: 0.4rem 0 0 0 !important; font-size: 0.95rem; }}

    /* Cards */
    .raus-card {{
        background: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: 16px;
        padding: 1.5rem 1.75rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: box-shadow 0.2s ease;
    }}
    .raus-card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.06); }}

    /* KPI-Kacheln */
    .raus-kpi {{
        background: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: 14px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .raus-kpi .value {{
        font-size: 1.75rem;
        font-weight: 700;
        color: {c["text"]} !important;
        letter-spacing: -0.02em;
        font-family: {FONT_PRIMARY} !important;
    }}
    .raus-kpi .label {{
        font-size: 0.8rem;
        color: {c["text_muted"]} !important;
        margin-top: 0.35rem;
        font-weight: 500;
    }}

    /* Szenario-Liste */
    .raus-scenario-item {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem 1.25rem;
        background: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: 12px;
        margin-bottom: 0.75rem;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }}
    .raus-scenario-item:hover {{
        border-color: {c["primary"]};
        box-shadow: 0 2px 8px rgba(252, 82, 0, 0.08);
    }}
    .raus-scenario-item.selected {{
        border-color: {c["primary"]};
        background: rgba(252, 82, 0, 0.04);
    }}

    /* Info-Box */
    .raus-info {{
        background: linear-gradient(90deg, rgba(252, 82, 0, 0.06) 0%, rgba(252, 82, 0, 0.02) 100%);
        border-left: 4px solid {c["primary"]};
        border-radius: 0 12px 12px 0;
        padding: 1rem 1.25rem;
        margin: 1rem 0;
        color: {c["text"]} !important;
    }}

    /* Sidebar */
    .stSidebar {{
        background: {c["bg_card"]} !important;
        border-right: 1px solid {c["border"]} !important;
    }}
    .stSidebar [data-testid="stSidebarNav"] {{ padding-top: 1rem; }}

    /* Buttons – Primary */
    .stButton > button[kind="primary"] {{
        background: {c["primary"]} !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.25rem !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: {c["primary_dark"]} !important;
    }}

    /* Expander */
    [data-testid="stExpander"] {{
        background: {c["bg_card"]} !important;
        border: 1px solid {c["border"]} !important;
        border-radius: 14px !important;
    }}

    /* Hide Streamlit branding */
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
</style>
'''
