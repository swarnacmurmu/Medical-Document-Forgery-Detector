import os
from nicegui import ui
from predict_receipt import ReceiptForgeryPredictor

# Initialize predictor
predictor = ReceiptForgeryPredictor()
analysis_results = []

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def update_results_panel():
    results_container.clear()
    with results_container:
        if not analysis_results:
            ui.label("No receipts analyzed yet.").classes("text-gray-500")
            return
        
        for res in analysis_results:
            with ui.card().classes("w-full mb-4"):
                with ui.row().classes("items-center justify-between"):
                    ui.label(f"📄 {res['filename']}").classes("font-bold text-lg")
                    ui.label(f"Confidence: {res['confidence']:.2%}").classes(f"text-{res['color']}-600")
                ui.separator()
                ui.html(f"<span class='text-{res['color']}-600 font-semibold text-xl'>Verdict: {res['verdict']}</span>")
                
                if res.get('error'):
                    ui.label(f"Error: {res['error']}").classes("text-red-600")

async def handle_upload(files):
    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.name)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        # Predict
        result = predictor.predict(file_path)
        result["filename"] = file.name
        analysis_results.append(result)
        update_results_panel()

def clear_all():
    global analysis_results
    analysis_results = []
    for f in os.listdir(UPLOAD_DIR):
        os.remove(os.path.join(UPLOAD_DIR, f))
    update_results_panel()
    ui.notify("All data cleared.", type="info")

# UI Layout
ui.page_title("Receipt Forgery Detector")
ui.query("body").style("background-color: #f0f2f5")

with ui.header(elevated=True).style("background-color: #1e3a8a"):
    ui.label("📄 Receipt Forgery Detector").classes("text-2xl font-bold text-white")
    ui.label("AI-Powered Receipt Document Forensics").classes("text-white")

with ui.column().classes("w-full items-center p-6"):
    ui.upload(on_upload=handle_upload, multiple=True, auto_upload=True,
              label="📤 Upload receipt images (PNG, JPG)") \
        .props("accept=.png,.jpg,.jpeg").classes("w-full max-w-3xl")
    
    with ui.row().classes("justify-center gap-4 my-4"):
        ui.button("🗑️ Clear All", on_click=clear_all, color="red")
    
    ui.label("📋 Analysis Results").classes("text-xl font-bold mt-4")
    results_container = ui.column().classes("w-full max-w-4xl gap-2")
    update_results_panel()

ui.run()