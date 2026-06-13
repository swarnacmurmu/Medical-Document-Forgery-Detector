import os
import re
from nicegui import ui, events
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
            extracted = res.get("extracted_text", "")[:300]
            
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
                with ui.expansion("View extracted text (first 300 chars)"):
                    ui.label(extracted)

async def handle_upload(event: events.UploadEventArguments):
    """Handle one file upload – NiceGUI calls this once per selected file."""
    try:
        file_name = event.file.name
        ui.notify(f'Processing "{file_name}"...', type='info')
        
        # Read the entire file content as text
        file_content = await event.file.read()
        # Decode bytes to string (assuming UTF-8 text files)
        try:
            text_content = file_content.decode('utf-8')
        except UnicodeDecodeError:
            ui.notify(f'"{file_name}" is not a valid text file.', type='negative')
            return
        
        # Analyze using Gemini (pass text content directly)
        result = analyze_document(text_content, file_name)
        result["filename"] = file_name
        result["extracted_text"] = text_content
        
        analysis_results.append(result)
        update_results_panel()
        ui.notify(f'Analysis complete for "{file_name}"', type='positive')
        
    except Exception as e:
        ui.notify(f'Error processing file: {e}', type='negative')
        print(f"Error in handle_upload: {e}")

def cross_reference():
    """Compare Patient ID and Name across multiple documents."""
    if len(analysis_results) < 2:
        ui.notify("Need at least 2 documents for cross-reference.", type="warning")
        return
    
    patient_map = {}
    inconsistencies = []
    for res in analysis_results:
        content = res.get("extracted_text", "")
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
    update_results_panel()
    ui.notify("All data cleared.", type="info")

# ---------- UI Layout ----------
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