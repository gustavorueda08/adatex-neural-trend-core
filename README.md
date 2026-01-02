# ANTC V5.0 (Adatex Neural Trend Core)

Microservice for autonomous business intelligence, predicting fashion trends using multi-modal AI.

## 🏗 System Architecture

The system is composed of 5 autonomous modules:

### 1. The Hunters (Ingestion)

- **Pinterest**: Scrapes images using Selenium.
- **TikTok/Reels**: Downloads and extracts frames using `yt-dlp` and OpenCV.
- **YouTube**: Transcribes videos using `youtube-transcript-api`.
- **Web**: Reads articles using `newspaper3k`.

### 2. The Brains (Neural Processing)

- **Vision Engine**: Uses `Google SigLIP` for Zero-Shot Classification.
- **Color Engine**: Uses `K-Means Clustering` for palette extraction.
- **NLP Engine**: Uses `BART` (Summarization) and `DistilBERT` (Sentiment).

### 3. The Oracle (Market Intelligence)

- **Trends Oracle**: Uses `Google Trends` to validate interest velocity (Rising/Stable/Declining).

### 4. The Creative (Synthesis & GenAI)

- **Copy Engine**: Uses `GPT-4o` to generate Trend Reports.
- **Image Engine**: Uses `Stable Diffusion XL` to generate Concept Art.

### 5. Integration

- **Persistance**: SQLite (Dev) / PostgreSQL (Prod).
- **Models**: SQLAlchemy ORM.

## 🚀 Setup & Execution

1. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration**
   Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

   _Set `OPENAI_API_KEY` in `.env` for full functionality._

3. **Run Pipeline**
   ```bash
   python run_pipeline.py
   ```
   _By default, the pipeline runs in `DEV` mode, saving data to `resources/` and `antc_dev.db`._

## 📂 Output

- **Database**: `antc_dev.db` (Contains `trend_reports` table).
- **Assets**: `resources/antc_data/` (Images from hunters).
- **Report**: `resources/trend_report_2026.md`.
- **Concept Art**: `resources/concept_art_2026.png`.

## 🛠️ API & Automation

**1. Start API Server** (On-demand Trigger)

```bash
uvicorn api:app --reload --port 8000
```

- **Trigger Pipeline**: `POST http://localhost:8000/pipeline/trigger`
- **Check Status**: `GET http://localhost:8000/pipeline/status`

**2. Cron Job** (Scheduled Execution)
Add to crontab to run daily at 8AM:

```bash
0 8 * * * cd /path/to/ANTC && venv/bin/python run_pipeline.py >> pipeline.log 2>&1
```
