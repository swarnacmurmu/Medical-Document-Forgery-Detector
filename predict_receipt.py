import os
import re
from nicegui import ui
from gemini_analyzer import analyze_document

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

analysis_results = []  # each: {filename, verdict, confidence, flags, explanation, extracted_text}

def update_results_panel():
    results_container.clear()
    with results_container:
        if not analysis_results:
            ui.label("No documents analyzed yet.").classes("text-gray-500")
            return
        for res in analysis_results:
            verdict = res.get("forensic_verdict", "unknown")
            confidence = res.get("confidence_score", 0)
            flags = res.get("suspicious_flags", [])
            explanation = res.get("explanation", "")
            filename = res.get("filename", "unknown")
            
            color = "red" if verdict == "suspicious" else ("green" if verdict == "clean" else "gray")
            icon = "⚠️" if verdict == "suspicious" else ("✅" if verdict == "clean" else "❓")
            
            with ui.card().classes("w-full mb-4"):
                with ui.row().classes("items-center justify-between"):
                    ui.label(f"{icon} {filename}").classes("font-bold text-lg")
                    ui.label(f"Confidence: {confidence:.2f}").classes(f"text-{color}-600")
                ui.separator()
                ui.html(f"<span class='text-{color}-600 font-semibold'>Verdict: {verdict.upper()}</span>")
                if flags:
                    ui.label("Suspicious flags:").classes("font-semibold mt-2")
                    for flag in flags:
                        ui.label(f"• {flag}").classes("text-red-600")
                ui.label(f"Explanation: {explanation}").classes("mt-2")
                with ui.expandable("View extracted text (first 300 chars)"):
                    ui.label(res.get("extracted_text", "")[:300])

async def handle_upload(event):
    """Handle a single file upload (called once per file)."""
    file_path = os.path.join(UPLOAD_DIR, event.name)
    with open(file_path, "wb") as f:
        f.write(event.content)
    
    result = analyze_document(file_path)
    result["filename"] = event.name
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            result["extracted_text"] = f.read()
    except Exception:
        result["extracted_text"] = "Could not read text content."
    
    analysis_results.append(result)
    update_results_panel()

def cross_reference():
    if len(analysis_results) < 2:
        ui.notify("Need at least 2 documents for cross-reference.", type="warning")
        return
    
    patient_map = {}
    inconsistencies = []
    for res in analysis_results:
        file_path = os.path.join(UPLOAD_DIR, res["filename"])
        if not os.path.exists(file_path):
            continue
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        pid_match = re.search(r"Patient ID:\s*(\S+)", content)
        name_match = re.search(r"Patient Name:\s*(.+)", content)
        if pid_match and name_match:
            pid = pid_match.group(1)
            name = name_match.group(1).strip()
            if pid in patient_map and patient_map[pid] != name:
                inconsistencies.append(f"Patient ID {pid} has conflicting names: {patient_map[pid]} vs {name}")
            else:
                patient_map[pid] = name
    
    if inconsistencies:
        for inc in inconsistencies:
            ui.notify(inc, type="warning")
        if analysis_results:
            if "suspicious_flags" not in analysis_results[0]:
                analysis_results[0]["suspicious_flags"] = []
            analysis_results[0]["suspicious_flags"].append("cross-reference inconsistency")
        update_results_panel()
    else:
        ui.notify("All patient IDs match consistently.", type="positive")

def clear_all():
    global analysis_results
    analysis_results = []
    for f in os.listdir(UPLOAD_DIR):
        os.remove(os.path.join(UPLOAD_DIR, f))
    update_results_panel()
    ui.notify("All data cleared.", type="info")

# UI Layout
ui.page_title("MedForgeDetector")
ui.query("body").style("background-color: #f0f2f5")

with ui.header(elevated=True).style("background-color: #1e3a8a"):
    ui.label("🩺 MedForgeDetector").classes("text-2xl font-bold text-white")
    ui.label("AI-Powered Medical Document Forgery Detection").classes("text-white")

with ui.column().classes("w-full items-center p-6"):
    ui.upload(on_upload=handle_upload, multiple=True, auto_upload=True,
              label="📄 Upload medical documents (.txt files)") \
        .props("accept=.txt").classes("w-full max-w-3xl")
    
    with ui.row().classes("justify-center gap-4 my-4"):
        ui.button("🔄 Cross-Reference Check", on_click=cross_reference, color="orange")
        ui.button("🗑️ Clear All", on_click=clear_all, color="red")
    
    ui.label("📋 Analysis Results").classes("text-xl font-bold mt-4")
    results_container = ui.column().classes("w-full max-w-4xl gap-2")
    update_results_panel()

ui.run()