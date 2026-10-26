"""Wanderlust-inspired CSS injected into the Streamlit page."""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600&display=swap');

:root {
  --teal: #0E7C86;
  --teal-dark: #0A5C63;
  --coral: #F6774F;
  --sun: #FFB547;
  --sand: #FFF6EC;
  --ink: #1F2A37;
  --muted: #6B7280;
  --card: #FFFFFF;
  --line: #EDE4D8;
}

html, body, [class*="css"], .stMarkdown, .stText, button, input, textarea, select {
  font-family: 'Poppins', system-ui, sans-serif;
}
.stApp {
  background:
    radial-gradient(1200px 400px at 100% -10%, rgba(246,119,79,0.10), transparent 60%),
    radial-gradient(900px 400px at -10% 0%, rgba(14,124,134,0.10), transparent 60%),
    #FFFCF8;
}
h1, h2, h3 { font-family: 'Playfair Display', Georgia, serif !important; color: var(--ink); }
.block-container { padding-top: 1.6rem; max-width: 1250px; }

section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0E7C86 0%, #0A5C63 100%);
}
section[data-testid="stSidebar"] * { color: #F7FBFB; }
section[data-testid="stSidebar"] input, section[data-testid="stSidebar"] textarea,
section[data-testid="stSidebar"] [data-baseweb="input"] *, section[data-testid="stSidebar"] [data-baseweb="base-input"] *,
section[data-testid="stSidebar"] [data-baseweb="select"] *, section[data-testid="stSidebar"] [data-testid="stDateInput"] *:not(label):not(label *) {
  color: var(--ink) !important; -webkit-text-fill-color: var(--ink) !important;
}
section[data-testid="stSidebar"] [data-testid="stDateInput"] label,
section[data-testid="stSidebar"] [data-testid="stDateInput"] label * { color: #F7FBFB !important; -webkit-text-fill-color: #F7FBFB !important; }
section[data-testid="stSidebar"] [data-baseweb="tag"] { background: var(--coral) !important; }
section[data-testid="stSidebar"] [data-baseweb="tag"] * { color: #fff !important; }
section[data-testid="stSidebar"] .stButton button {
  background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.45); color: #fff;
}
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.25); }

.hero {
  position: relative; overflow: hidden;
  background: linear-gradient(120deg, #0E7C86 0%, #13A3A0 45%, #F6774F 100%);
  border-radius: 22px; padding: 28px 32px; color: #fff; margin-bottom: 18px;
  box-shadow: 0 18px 40px -22px rgba(14,124,134,0.65);
}
.hero::after {
  content: "✈"; position: absolute; right: 28px; top: 6px; font-size: 92px; opacity: 0.16;
  transform: rotate(-18deg);
}
.hero h1 { color: #fff !important; font-size: 2.15rem; margin: 0 0 4px 0; }
.hero p { margin: 0; opacity: 0.93; font-weight: 300; }
.chips { margin-top: 14px; display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
  display: inline-block; padding: 4px 12px; border-radius: 999px; font-size: 0.78rem;
  background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.35); color: #fff;
}
.pill {
  display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.72rem; font-weight: 500;
  background: #E6F4F5; color: var(--teal-dark); margin: 2px 4px 2px 0;
}
.pill.coral { background: #FFE9E1; color: #B4472A; }
.pill.sun { background: #FFF1D6; color: #8A5A00; }
.pill.ok { background: #E3F6E8; color: #1E7B3A; }

.card {
  background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 18px 20px;
  box-shadow: 0 10px 30px -24px rgba(31,42,55,0.45); height: 100%;
}
.rec-card h3 { margin: 4px 0 2px 0; font-size: 1.45rem; }
.rec-rank { font-size: 0.75rem; letter-spacing: .12em; text-transform: uppercase; color: var(--coral); font-weight: 600; }
.score-bar { height: 8px; border-radius: 99px; background: #F1ECE4; overflow: hidden; margin: 10px 0 6px; }
.score-bar > span { display: block; height: 100%; background: linear-gradient(90deg, var(--teal), var(--coral)); }
.muted { color: var(--muted); font-size: 0.86rem; }

.metric {
  background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 14px 16px;
}
.metric .label { font-size: 0.74rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }
.metric .value { font-size: 1.35rem; font-weight: 600; color: var(--ink); line-height: 1.3; }
.metric .sub { font-size: 0.76rem; color: var(--teal); }

.day-head { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; }
.timeline { border-left: 3px dashed #E2D6C6; margin: 8px 0 4px 10px; padding-left: 18px; }
.slot {
  position: relative; background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  padding: 12px 14px; margin-bottom: 10px;
}
.slot::before {
  content: ""; position: absolute; left: -27px; top: 16px; width: 14px; height: 14px; border-radius: 50%;
  background: var(--dot, var(--teal)); border: 3px solid #FFFCF8;
}
.slot .time { font-size: 0.78rem; color: var(--muted); font-weight: 500; }
.slot .name { font-weight: 600; font-size: 1.02rem; color: var(--ink); }
.slot .desc { font-size: 0.86rem; color: #4B5563; margin-top: 2px; }
.slot .meta { font-size: 0.78rem; color: var(--teal-dark); margin-top: 6px; }
.slot.meal { background: #FFFBF4; }
.slot.free { background: repeating-linear-gradient(45deg, #FFFFFF, #FFFFFF 10px, #FBF7F1 10px, #FBF7F1 20px); }
.tip { font-size: 0.84rem; color: #5B4A2E; background: #FFF6E2; border-radius: 10px; padding: 6px 10px; margin: 4px 0; }
.legend span { display: inline-flex; align-items: center; gap: 6px; margin-right: 14px; font-size: 0.8rem; }
.legend i { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }

.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] {
  background: #FFFFFF; border: 1px solid var(--line); border-radius: 12px 12px 0 0; padding: 8px 16px;
}
.stTabs [aria-selected="true"] { background: var(--sand); border-bottom-color: var(--coral); }
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"] {
  background: linear-gradient(90deg, var(--coral), #F89A5B); border: none; color: #fff; font-weight: 600;
}
footer { visibility: hidden; }
</style>
"""
