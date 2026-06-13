import os
import re
import csv
import io
import json
import time
import joblib
import numpy as np
from scipy.sparse import hstack, csr_matrix
from nicegui import ui, events

# ----------------------------------------------------------------------
# 1. BACKEND (your exact code – unchanged)
# ----------------------------------------------------------------------
try:
    from utils.feature_extractor import extract_features
    print("✅ feature_extractor loaded")
except Exception as e:
    print(f"❌ Failed to load feature_extractor: {e}")
    extract_features = None

model = None
vectorizer = None
try:
    model = joblib.load('models/hybrid_model.pkl')
    vectorizer = joblib.load('models/tfidf_vectorizer.pkl')
    print("✅ Model and vectorizer loaded")
except Exception as e:
    print(f"❌ Failed to load model: {e}")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
analysis_results = []

def predict_document(text):
    if model is None or vectorizer is None or extract_features is None:
        return "ERROR", 0.0, {"error": "Model or feature extractor not loaded"}
    try:
        struct = extract_features(text)
        struct_arr = [[struct['amount'], struct['date_consistent'], struct['length_of_stay'],
                       struct['amount_deviation'], struct['treatment_match']]]
        X_struct = csr_matrix(struct_arr)
        X_text = vectorizer.transform([text])
        X_combined = hstack([X_text, X_struct])
        proba = model.predict_proba(X_combined)[0]
        pred = model.predict(X_combined)[0]
        confidence = proba[1] if pred == 1 else proba[0]
        verdict = "SUSPICIOUS" if pred == 1 else "GENUINE"
        return verdict, confidence, struct
    except Exception as e:
        return "ERROR", 0.0, {"error": str(e)}

def generate_flags_and_explanation(features, verdict, confidence):
    reasoning = []
    flags = []
    amount = features.get('amount', 0)
    dev = features.get('amount_deviation', 0)
    if dev > 1.5:
        flags.append(f"⚠️ Amount ₹{amount:,} is {dev:.1f}x above expected range")
        reasoning.append(f"amount ₹{amount:,} is unusually high (deviation {dev:.1f})")
    else:
        reasoning.append(f"amount ₹{amount:,} is within the typical range")
    if features.get('date_consistent', False):
        reasoning.append("dates are logically ordered")
    else:
        flags.append("❌ Discharge before admission")
        reasoning.append("discharge date is before admission – a clear forgery sign")
    if features.get('treatment_match', False):
        reasoning.append("treatment matches diagnosis")
    else:
        flags.append("❌ Treatment does not match diagnosis")
        reasoning.append("treatment is not appropriate for the given diagnosis")
    los = features.get('length_of_stay', 0)
    if los <= 7:
        reasoning.append(f"stay of {los} days is typical")
    else:
        flags.append(f"⚠️ Long stay ({los} days)")
        reasoning.append(f"stay of {los} days is unusually long")
    if verdict == "GENUINE":
        reasoning_summary = "✅ This document appears GENUINE. " + ". ".join(reasoning) + "."
    else:
        reasoning_summary = "⚠️ This document is SUSPICIOUS. " + ". ".join(reasoning) + "."
    if not flags:
        flags.append("✅ No obvious anomalies")
    return flags, reasoning_summary

# ----------------------------------------------------------------------
# 2. UI STATE & HELPER FUNCTIONS
# ----------------------------------------------------------------------
state = {'filter': 'all', 'sort': 'newest', 'query': ''}

def filtered_results():
    out = [r for r in analysis_results
           if (state['filter'] == 'all' or r['verdict'].lower() == state['filter'])
           and state['query'].lower() in r['filename'].lower()]
    if state['sort'] == 'confidence':
        out.sort(key=lambda r: r['confidence'], reverse=True)
    elif state['sort'] == 'filename':
        out.sort(key=lambda r: r['filename'].lower())
    else:
        out.sort(key=lambda r: r['ts'], reverse=True)
    return out

def render_kpis():
    kpi_container.clear()
    total = len(analysis_results)
    genuine = sum(1 for r in analysis_results if r['verdict'] == 'GENUINE')
    suspicious = sum(1 for r in analysis_results if r['verdict'] == 'SUSPICIOUS')
    avg_conf = np.mean([r['confidence'] for r in analysis_results]) if total else 0
    with kpi_container:
        with ui.row().classes('w-full gap-4 flex-wrap justify-stretch'):
            for label, value, color in [("Total", total, "blue"), ("Genuine", genuine, "emerald"),
                                        ("Suspicious", suspicious, "rose"), ("Avg Conf", f"{avg_conf:.0%}", "indigo")]:
                with ui.card().classes(f'flex-1 min-w-[120px] p-4 rounded-2xl shadow-sm border-t-4 border-{color}-400'):
                    ui.label(str(value)).classes('text-2xl font-bold')
                    ui.label(label).classes('text-xs text-gray-500 uppercase')

def render_results():
    results_container.clear()
    items = filtered_results()
    if not analysis_results:
        with results_container:
            ui.label("No documents analyzed yet.").classes('text-gray-500 p-8 text-center')
        return
    if not items:
        with results_container:
            ui.label("No documents match current filters.").classes('text-gray-500 p-4')
        return
    with results_container:
        for res in items:
            with ui.card().classes('w-full mb-6 rounded-2xl shadow-md overflow-hidden'):
                # Header row
                with ui.row().classes('items-center justify-between p-4 bg-gray-50 border-b'):
                    ui.label(f"📄 {res['filename']}").classes('font-bold text-lg')
                    ui.label(f"Confidence: {res['confidence']:.0%}").classes('text-md font-mono')
                # Verdict badge
                if res['verdict'] == 'GENUINE':
                    ui.html('<div class="p-3 text-center bg-green-100 text-green-800 font-bold text-xl">✅ GENUINE</div>')
                elif res['verdict'] == 'SUSPICIOUS':
                    ui.html('<div class="p-3 text-center bg-red-100 text-red-800 font-bold text-xl">⚠️ SUSPICIOUS</div>')
                else:
                    ui.html('<div class="p-3 text-center bg-gray-200 text-gray-800 font-bold text-xl">❌ ERROR</div>')
                # Reasoning summary
                with ui.card_section():
                    ui.label("🧠 Reasoning Summary").classes('font-semibold text-lg mb-2')
                    ui.label(res['reasoning']).classes('text-gray-700 bg-gray-50 p-3 rounded-lg')
                # Structured features
                with ui.card_section():
                    ui.label("📊 Structured Analysis").classes('font-semibold text-lg mb-2')
                    feats = res['features']
                    if "error" in feats:
                        ui.label(f"Error: {feats['error']}").classes('text-red-600')
                    else:
                        with ui.grid(columns=2).classes('w-full gap-3'):
                            ui.label("💰 Total Amount:").classes('font-medium')
                            ui.label(f"₹{feats.get('amount',0):,}")
                            ui.label("📅 Length of Stay:").classes('font-medium')
                            ui.label(f"{feats.get('length_of_stay',0)} days")
                            ui.label("✅ Date Consistency:").classes('font-medium')
                            ui.label("Yes" if feats.get('date_consistent') else "No")
                            ui.label("💊 Treatment Match:").classes('font-medium')
                            ui.label("Yes" if feats.get('treatment_match') else "No")
                            ui.label("📈 Amount Deviation:").classes('font-medium')
                            dev = feats.get('amount_deviation', 0)
                            ui.progress(value=min(1.0, dev), size='20px').classes('w-full')
                            ui.label(f"{dev:.2f} (suspicious > 1.5)").classes('text-sm text-gray-500')
                # Flags
                if res['flags']:
                    with ui.card_section():
                        ui.label("🚨 Flags").classes('font-semibold text-lg mb-2')
                        for flag in res['flags']:
                            ui.label(flag).classes('text-red-600')
                # Raw text expandable
                with ui.expansion("📄 View extracted text (first 500 chars)"):
                    ui.label(res.get('text_preview', '')[:500]).classes('font-mono text-sm')

def refresh():
    render_kpis()
    render_results()
    render_ghost_panel()

# ----------------------------------------------------------------------
# 3. GHOST PATIENT PANEL (persistent, instead of notifications)
# ----------------------------------------------------------------------
ghost_panel = None

def render_ghost_panel():
    ghost_panel.clear()
    patient_map = {}
    alerts = []
    for res in analysis_results:
        text = res.get('text_preview', '')
        pid = re.search(r"Patient ID:\s*(\S+)", text)
        name = re.search(r"Patient Name:\s*(.+)", text)
        if pid and name:
            pid_val = pid.group(1)
            name_val = name.group(1).strip()
            if pid_val in patient_map and patient_map[pid_val] != name_val:
                alerts.append(f"🚨 Ghost patient: ID **{pid_val}** has conflicting names “{patient_map[pid_val]}” vs “{name_val}” in **{res['filename']}**")
            else:
                patient_map[pid_val] = name_val
    with ghost_panel:
        if alerts:
            with ui.card().classes('w-full bg-rose-50 border-l-8 border-rose-500 p-4 rounded-2xl mb-4'):
                ui.label("👻 Ghost Patient Alerts").classes('font-bold text-rose-800 mb-2')
                for alert in alerts:
                    ui.html(f'<div class="text-rose-700 text-sm mb-1">• {alert}</div>')
        else:
            with ui.card().classes('w-full bg-emerald-50 border-l-8 border-emerald-500 p-4 rounded-2xl mb-4'):
                ui.label("✅ No ghost patient conflicts found.").classes('text-emerald-700')

def cross_reference_manual():
    render_ghost_panel()   # just refreshes the panel (it's already persistent, but we call to update)
    ui.notify("Ghost patient check updated", type='info')

# ----------------------------------------------------------------------
# 4. EXPORT & CLEAR
# ----------------------------------------------------------------------
def export_json():
    data = json.dumps([{k: v for k, v in r.items() if k != 'text_preview'} for r in analysis_results],
                      indent=2, default=str)
    ui.download(data.encode(), 'medforge_results.json')

def export_csv():
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['filename','verdict','confidence','amount','length_of_stay','date_consistent','treatment_match','amount_deviation'])
    for r in analysis_results:
        f = r['features']
        w.writerow([r['filename'], r['verdict'], f"{r['confidence']:.3f}",
                    f.get('amount',''), f.get('length_of_stay',''),
                    f.get('date_consistent',''), f.get('treatment_match',''),
                    f.get('amount_deviation','')])
    ui.download(buf.getvalue().encode(), 'medforge_results.csv')

def clear_all():
    global analysis_results
    analysis_results = []
    refresh()
    ui.notify("All results cleared", type='info')

# ----------------------------------------------------------------------
# 5. UPLOAD HANDLER (with timestamp)
# ----------------------------------------------------------------------
async def handle_upload(event: events.UploadEventArguments):
    file_name = event.file.name
    ui.notify(f'Analyzing {file_name}...', type='info')
    content = await event.file.read()
    text = content.decode('utf-8')
    verdict, confidence, feats = predict_document(text)
    flags, reasoning = generate_flags_and_explanation(feats, verdict, confidence)
    analysis_results.append({
        'filename': file_name,
        'ts': time.time(),
        'verdict': verdict,
        'confidence': confidence,
        'features': feats,
        'flags': flags,
        'reasoning': reasoning,
        'text_preview': text
    })
    refresh()
    ui.notify(f'Done: {verdict}', type='positive' if verdict == 'GENUINE' else 'warning')

# ----------------------------------------------------------------------
# 6. UI LAYOUT (your simple layout but with added controls)
# ----------------------------------------------------------------------
ui.page_title("MedForgeDetector")
ui.query('body').style('background-color: #f5f7fb; font-family: "Inter", sans-serif;')
ui.add_head_html('<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">')

# Header with dark mode toggle
with ui.header(elevated=True).style('background: linear-gradient(90deg, #1e3a8a, #0f172a); padding: 0.8rem 1.5rem;'):
    with ui.row().classes('w-full items-center justify-between'):
        with ui.row().classes('items-center gap-3'):
            ui.icon('local_hospital').classes('text-3xl text-white')
            ui.label("🩺 MedForgeDetector").classes('text-xl font-bold text-white')
        with ui.row().classes('items-center gap-2'):
            ui.button(icon='dark_mode', on_click=lambda: ui.dark_mode().toggle()).props('flat round color=white')
            ui.button('Export JSON', icon='download', on_click=export_json).props('flat color=white')
            ui.button('Export CSV', icon='table_view', on_click=export_csv).props('flat color=white')

# Main content
with ui.column().classes('w-full max-w-5xl mx-auto p-6 gap-4'):
    # KPIs
    kpi_container = ui.column().classes('w-full')
    
    # Upload area
    ui.upload(on_upload=handle_upload, multiple=True, auto_upload=True,
              label="📄 Drag & drop or select .txt medical documents") \
        .props('accept=.txt').classes('w-full')
    
    # Filter bar
    with ui.row().classes('w-full items-center gap-4 flex-wrap my-2'):
        ui.input(placeholder='Search filename...', on_change=lambda e: (state.update(query=e.value), refresh())) \
            .props('outlined dense clearable').classes('flex-grow')
        ui.select({'all':'All','genuine':'Genuine','suspicious':'Suspicious'}, value='all', label='Verdict',
                  on_change=lambda e: (state.update(filter=e.value), refresh())).props('outlined dense').classes('w-32')
        ui.select({'newest':'Newest','confidence':'Confidence','filename':'Filename'}, value='newest', label='Sort',
                  on_change=lambda e: (state.update(sort=e.value), refresh())).props('outlined dense').classes('w-32')
    
    # Action buttons row
    with ui.row().classes('w-full gap-3 flex-wrap'):
        ui.button('👻 Check Ghost Patients', on_click=cross_reference_manual, color='orange', icon='groups')
        ui.button('🗑️ Clear All', on_click=clear_all, color='red', icon='delete')
    
    # Persistent ghost panel (initially empty)
    ghost_panel = ui.column().classes('w-full')
    
    # Results container
    ui.label('📋 Analysis Results').classes('text-xl font-bold mt-2')
    results_container = ui.column().classes('w-full gap-2')

# Initial render
refresh()
ui.run()