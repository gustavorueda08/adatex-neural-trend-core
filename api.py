from fastapi import FastAPI, BackgroundTasks, HTTPException
import subprocess
import sys
import logging
import os
from datetime import datetime

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ANTC_API")

app = FastAPI(title="ANTC API", version="5.0", description="Autonomous Neural Trend Core API")

PIPELINE_SCRIPT = "run_pipeline.py"
LOG_FILE = "pipeline.log"

def run_pipeline_task():
    """
    Executes the pipeline script in a subprocess and logs output.
    This runs in the background.
    """
    logger.info("🚀 [API] Starting Pipeline Execution...")
    try:
        # Use full path to venv python if needed, or just 'python' if running inside venv
        # Assuming we are running this API with the same venv
        cmd = [sys.executable, PIPELINE_SCRIPT]
        
        with open(LOG_FILE, "a") as log:
            log.write(f"\n\n--- Execution Request: {datetime.now()} ---\n")
            process = subprocess.Popen(cmd, stdout=log, stderr=log, text=True)
            process.wait() # Wait for process to finish
            
        logger.info(f"✅ [API] Pipeline finished. Return code: {process.returncode}")
    except Exception as e:
        logger.error(f"❌ [API] Error running pipeline: {e}")

@app.get("/")
def home():
    return {"message": "Welcome to ANTC V5.0 API", "status": "online"}

@app.post("/pipeline/trigger")
def trigger_pipeline(background_tasks: BackgroundTasks):
    """
    Triggers the ANTC pipeline asynchronously.
    Returns immediately confirming the task started.
    """
    # Check if pipeline file exists
    if not os.path.exists(PIPELINE_SCRIPT):
        raise HTTPException(status_code=500, detail="Pipeline script not found.")

    background_tasks.add_task(run_pipeline_task)
    return {"message": "Pipeline execution started in background.", "log_file": LOG_FILE}

@app.get("/pipeline/status")
def get_status():
    """
    Returns the last 10 lines of the log file to see status.
    """
    if not os.path.exists(LOG_FILE):
        return {"status": "No logs found yet."}
    
    try:
        # Simple tail implementation
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            last_lines = lines[-10:] if len(lines) > 10 else lines
        return {
            "last_log_lines": [l.strip() for l in last_lines]
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Run with reloader for dev
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
