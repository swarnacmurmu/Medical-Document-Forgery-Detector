import os
import asyncio
from nicegui import ui, app
from gemini_analyzer import analyze_document

# Global storage for analysis results
analysis_results = []

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def update_results_panel():
    """Refresh the displayed results."""
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

            color = "red" if verdict == "suspicious" else "green"
            icon = "⚠️" if verdict == "suspicious" else "✅"

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
                with ui.expandable("Show extracted data"):
                    ui.json_editor({"content": {"json": res.get("extracted_data", {})}, "mode": "view"})

async def handle_upload(files):
    """Process uploaded files one by one."""
    for file in files:
        # Save uploaded file
        file_path = os.path.join(UPLOAD_DIR, file.name)
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Add placeholder
        analysis_results.append({
            "filename": file.name,
            "forensic_verdict": "analyzing",
            "confidence_score": 0,
            "suspicious_flags": [],
            "explanation": "Analyzing with Gemini...",
            "extracted_data": {}
        })
        update_results_panel()

        # Run analysis
        result = analyze_document(file_path)
        result["filename"] = file.name

        # Replace placeholder
        for i, r in enumerate(analysis_results):
            if r["filename"] == file.name:
                analysis_results[i] = result
                break
        update_results_panel()

        # Clean up uploaded file (optional)
        # os.remove(file_path)

def cross_reference():
    """Detect ghost patients by comparing patient IDs across documents."""
    if len(analysis_results) < 2:
        ui.notify("Need at least 2 documents for cross-reference.", type="warning")
        return
    patient_ids = {}
    inconsistencies = []
    for res in analysis_results:
        pid = res.get("extracted_data", {}).get("patient_id")
        pname = res.get("extracted_data", {}).get("patient_name")
        if pid and pname:
            if pid in patient_ids and patient_ids[pid] != pname:
                inconsistencies.append(f"Patient ID {pid} has conflicting names: {patient_ids[pid]} vs {pname}")
            else:
                patient_ids[pid] = pname
    if inconsistencies:
        for inc in inconsistencies:
            ui.notify(inc, type="warning")
        if analysis_results:
            analysis_results[0]["suspicious_flags"].append("Cross-reference inconsistency detected")
        update_results_panel()
    else:
        ui.notify("All documents consistent.", type="positive")

def clear_all():
    """Clear all results and uploaded files."""
    global analysis_results
    analysis_results = []
    for f in os.listdir(UPLOAD_DIR):
        os.remove(os.path.join(UPLOAD_DIR, f))
    update_results_panel()
    ui.notify("All data cleared.", type="info")

# --- Build UI ---
ui.page_title("MedForgeDetector")
ui.query("body").style("background-color: #f0f2f5")

with ui.header(elevated=True).style("background-color: #1e3a8a"):
    ui.label("🩺 MedForgeDetector").classes("text-2xl font-bold text-white")
    ui.label("AI-Powered Medical Document Forensics").classes("text-white")

with ui.column().classes("w-full items-center p-6"):
    ui.upload(on_upload=handle_upload, multiple=True, auto_upload=True,
              label="📄 Upload medical documents (images or text files)") \
        .props("accept=.png,.jpg,.jpeg,.txt").classes("w-full max-w-3xl")

    with ui.row().classes("justify-center gap-4 my-4"):
        ui.button("🔄 Cross-Reference Check", on_click=cross_reference, color="orange")
        ui.button("🗑️ Clear All", on_click=clear_all, color="red")

    ui.label("📋 Analysis Results").classes("text-xl font-bold mt-4")
    results_container = ui.column().classes("w-full max-w-4xl gap-2")
    update_results_panel()

ui.run()