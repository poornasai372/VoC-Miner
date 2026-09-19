from pathlib import Path
from typing import Any
import json
import re
from datetime import datetime, date

import numpy as np
import pandas as pd
import fitz  # PyMuPDF
from docx import Document

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .main import analyze_feedback


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CURRENT_DATA_PATH = DATA_DIR / "current_upload.csv"

DATA_DIR.mkdir(exist_ok=True)


# ============================================================
# APP
# ============================================================

app = FastAPI(title="VoC-Miner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# CURRENT STATE
# ============================================================

pain_points = []

dataset_stats = {
    "total_feedback": 0,
    "active_insights": 0,
    "high_priority": 0,
    "strong_signals": 0,
    "sources": 0,
}

timeline_data = []

current_dataset_loaded = False
current_filename = None


# ============================================================
# JSON SAFE CONVERSION
# ============================================================

def json_safe(value: Any):

    if isinstance(value, dict):
        return {
            str(k): json_safe(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            json_safe(v)
            for v in value
        ]

    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())

    if isinstance(value, np.generic):
        return value.item()

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()

    if isinstance(value, float):
        if np.isnan(value) or np.isinf(value):
            return None

    try:
        result = pd.isna(value)

        if isinstance(result, (bool, np.bool_)):
            if result:
                return None

    except Exception:
        pass

    return value


# ============================================================
# CSV
# ============================================================

def parse_csv(file_path: Path) -> pd.DataFrame:

    return pd.read_csv(file_path)


# ============================================================
# EXCEL
# ============================================================

def parse_excel(file_path: Path) -> pd.DataFrame:

    return pd.read_excel(file_path)


# ============================================================
# JSON
# ============================================================

def parse_json(file_path: Path) -> pd.DataFrame:

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    if isinstance(data, list):
        return pd.DataFrame(data)

    if isinstance(data, dict):

        for key in [
            "feedback",
            "data",
            "reviews",
            "records"
        ]:

            if (
                key in data
                and isinstance(data[key], list)
            ):
                return pd.DataFrame(data[key])

        return pd.DataFrame([data])

    raise ValueError(
        "Unsupported JSON structure."
    )


# ============================================================
# TXT
# ============================================================

def parse_txt(file_path: Path) -> pd.DataFrame:

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as f:

        text = f.read()

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        raise ValueError(
            "TXT file contains no text."
        )

    return pd.DataFrame({
        "id": range(1, len(lines) + 1),
        "text": lines,
        "source": ["text_file"] * len(lines),
        "date": [pd.Timestamp.now()] * len(lines),
    })


# ============================================================
# DOCX
# ============================================================

def parse_docx(file_path: Path) -> pd.DataFrame:

    document = Document(file_path)

    paragraphs = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    if not paragraphs:
        raise ValueError(
            "DOCX file contains no readable paragraphs."
        )

    return pd.DataFrame({
        "id": range(1, len(paragraphs) + 1),
        "text": paragraphs,
        "source": ["docx"] * len(paragraphs),
        "date": [pd.Timestamp.now()] * len(paragraphs),
    })


# ============================================================
# PDF
# ============================================================

def parse_pdf(file_path: Path) -> pd.DataFrame:

    document = fitz.open(file_path)

    rows = []
    counter = 1

    for page_number, page in enumerate(
        document,
        start=1
    ):

        # Get text line-by-line instead of treating
        # the entire PDF page as one feedback item.
        raw_text = page.get_text("text")

        if not raw_text:
            continue

        # Normalize line endings
        raw_text = raw_text.replace("\r\n", "\n")
        raw_text = raw_text.replace("\r", "\n")

        # Split into lines
        lines = raw_text.split("\n")

        for line in lines:

            line = line.strip()

            # Ignore empty lines
            if not line:
                continue

            # Ignore very short fragments
            if len(line) < 8:
                continue

            # Remove common PDF bullet characters
            line = re.sub(
                r"^[•●▪◦‣\-–—]+\s*",
                "",
                line
            ).strip()

            # Remove numbering such as:
            # 1.
            # 2)
            # 10.
            line = re.sub(
                r"^\d+[\.\)]\s*",
                "",
                line
            ).strip()

            if not line:
                continue

            # If one line contains several sentences,
            # separate them into individual feedback items.
            sentences = re.split(
                r"(?<=[.!?])\s+(?=[A-Z])",
                line
            )

            for sentence in sentences:

                sentence = sentence.strip()

                if len(sentence) < 8:
                    continue

                rows.append({
                    "id": counter,
                    "text": sentence,
                    "source": f"pdf_page_{page_number}",
                    "date": pd.Timestamp.now(),
                })

                counter += 1

    document.close()

    if not rows:

        raise ValueError(
            "PDF contains no extractable text. "
            "Scanned/image-only PDFs require OCR."
        )

    return pd.DataFrame(rows)


# ============================================================
# UNIVERSAL FILE PARSER
# ============================================================

def parse_uploaded_file(
    file_path: Path
) -> pd.DataFrame:

    extension = file_path.suffix.lower()

    if extension == ".csv":

        df = parse_csv(file_path)

    elif extension in [".xlsx", ".xls"]:

        df = parse_excel(file_path)

    elif extension == ".json":

        df = parse_json(file_path)

    elif extension == ".txt":

        df = parse_txt(file_path)

    elif extension == ".docx":

        df = parse_docx(file_path)

    elif extension == ".pdf":

        df = parse_pdf(file_path)

    else:

        raise ValueError(
            f"Unsupported file format: {extension}"
        )

    return standardize_dataframe(df)


# ============================================================
# STANDARDIZE DATA
# ============================================================

def standardize_dataframe(
    df: pd.DataFrame
) -> pd.DataFrame:

    if df.empty:

        raise ValueError(
            "The uploaded file contains no data."
        )

    df = df.copy()

    df.columns = [
        str(column).strip().lower()
        for column in df.columns
    ]

    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

    text_candidates = [
        "text",
        "feedback",
        "comment",
        "comments",
        "review",
        "reviews",
        "message",
        "content",
        "description",
        "transcript",
        "note",
        "notes",
    ]

    text_column = None

    for column in text_candidates:

        if column in df.columns:

            text_column = column
            break

    if text_column is None:

        object_columns = df.select_dtypes(
            include=["object", "string"]
        ).columns

        if len(object_columns) > 0:

            average_lengths = {
                column: df[column]
                .astype(str)
                .str.len()
                .mean()
                for column in object_columns
            }

            text_column = max(
                average_lengths,
                key=average_lengths.get
            )

    if text_column is None:

        raise ValueError(
            "Could not find a feedback/text column."
        )

    # --------------------------------------------------------
    # ID
    # --------------------------------------------------------

    id_candidates = [
        "id",
        "feedback_id",
        "review_id",
        "ticket_id",
    ]

    id_column = next(
        (
            column
            for column in id_candidates
            if column in df.columns
        ),
        None,
    )

    if id_column:

        ids = df[id_column]

    else:

        ids = range(
            1,
            len(df) + 1
        )

    # --------------------------------------------------------
    # SOURCE
    # --------------------------------------------------------

    source_candidates = [
        "source",
        "channel",
        "type",
        "feedback_source",
    ]

    source_column = next(
        (
            column
            for column in source_candidates
            if column in df.columns
        ),
        None,
    )

    if source_column:

        sources = df[source_column].fillna(
            "unknown"
        )

    else:

        sources = [
            "uploaded_file"
        ] * len(df)

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    date_candidates = [
        "date",
        "timestamp",
        "created_at",
        "created",
        "datetime",
    ]

    date_column = next(
        (
            column
            for column in date_candidates
            if column in df.columns
        ),
        None,
    )

    if date_column:

        dates = pd.to_datetime(
            df[date_column],
            errors="coerce"
        )

    else:

        dates = pd.Series(
            [pd.Timestamp.now()] * len(df)
        )

    # --------------------------------------------------------
    # CREATE STANDARD DATAFRAME
    # --------------------------------------------------------

    standardized = pd.DataFrame({
        "id": list(ids),
        "text": df[text_column].astype(str),
        "source": sources.astype(str),
        "date": dates,
    })

    standardized["text"] = (
        standardized["text"].str.strip()
    )

    standardized = standardized[
        standardized["text"].notna()
        & (standardized["text"] != "")
        & (standardized["text"] != "nan")
    ]

    standardized = standardized.reset_index(
        drop=True
    )

    standardized["id"] = [
        str(value)
        for value in standardized["id"]
    ]

    standardized["date"] = pd.to_datetime(
        standardized["date"],
        errors="coerce"
    )

    standardized["date"] = (
        standardized["date"].fillna(
            pd.Timestamp.now()
        )
    )

    return standardized


# ============================================================
# VALIDATION
# ============================================================

def validate_feedback_dataframe(
    df: pd.DataFrame
):

    required_columns = {
        "id",
        "text",
        "source",
        "date",
    }

    missing = (
        required_columns
        - set(df.columns)
    )

    if missing:

        raise ValueError(
            f"Missing required columns: "
            f"{sorted(missing)}"
        )

    if len(df) == 0:

        raise ValueError(
            "No usable feedback was found."
        )


# ============================================================
# DATASET STATS
# ============================================================

def get_dataset_stats(
    df: pd.DataFrame
):

    return {
        "total_feedback": int(
            len(df)
        ),

        "active_insights": int(
            len(pain_points)
        ),

        "high_priority": int(
            sum(
                1
                for item in pain_points
                if str(
                    item.get(
                        "priority",
                        ""
                    )
                ).upper()
                == "HIGH"
            )
        ),

        "strong_signals": int(
            sum(
                1
                for item in pain_points
                if str(
                    item.get(
                        "signal_strength",
                        ""
                    )
                ).upper()
                in [
                    "STRONG",
                    "HIGH"
                ]
            )
        ),

        "sources": int(
            df["source"].nunique()
        ),
    }


# ============================================================
# TIMELINE
# ============================================================

def get_feedback_timeline(
    df: pd.DataFrame
):

    timeline_df = df.copy()

    timeline_df["date"] = pd.to_datetime(
        timeline_df["date"],
        errors="coerce"
    )

    timeline_df = timeline_df.dropna(
        subset=["date"]
    )

    if timeline_df.empty:

        return []

    timeline_df["date_only"] = (
        timeline_df["date"]
        .dt.strftime("%Y-%m-%d")
    )

    timeline = (
        timeline_df
        .groupby("date_only")
        .size()
        .reset_index(
            name="count"
        )
    )

    timeline.columns = [
        "date",
        "count"
    ]

    return timeline.to_dict(
        orient="records"
    )


# ============================================================
# ANALYZE DATASET
# ============================================================

def update_analysis():

    global pain_points
    global dataset_stats
    global timeline_data
    global current_dataset_loaded

    if not CURRENT_DATA_PATH.exists():

        raise ValueError(
            "No dataset has been uploaded."
        )

    df = pd.read_csv(
        CURRENT_DATA_PATH
    )

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    validate_feedback_dataframe(
        df
    )

    print(
        f"Number of feedback entries: "
        f"{len(df)}"
    )

    results = analyze_feedback(
        str(CURRENT_DATA_PATH)
    )

    pain_points = json_safe(
        results
    )

    dataset_stats = get_dataset_stats(
        df
    )

    timeline_data = get_feedback_timeline(
        df
    )

    current_dataset_loaded = True


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    return {
        "status": "ok",
        "dataset_loaded": current_dataset_loaded,
        "filename": current_filename,
    }


# ============================================================
# INSIGHTS
# ============================================================

@app.get("/api/insights")
def get_insights():

    return JSONResponse(
        content=json_safe({
            "insights": pain_points,
            "dataset_loaded": current_dataset_loaded,
            "filename": current_filename,
        })
    )


# ============================================================
# STATS
# ============================================================

@app.get("/api/stats")
def get_stats():

    return JSONResponse(
        content=json_safe(
            dataset_stats
        )
    )


# ============================================================
# TIMELINE
# ============================================================

@app.get("/api/timeline")
def get_timeline():

    return JSONResponse(
        content=json_safe({
            "timeline": timeline_data
        })
    )


# ============================================================
# UPLOAD
# ============================================================

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...)
):

    global current_filename

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No file selected."
        )

    allowed_extensions = {
        ".csv",
        ".xlsx",
        ".xls",
        ".json",
        ".txt",
        ".docx",
        ".pdf",
    }

    extension = Path(
        file.filename
    ).suffix.lower()

    if extension not in allowed_extensions:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file format. "
                "Supported formats: "
                "CSV, XLSX, XLS, JSON, "
                "TXT, DOCX, PDF."
            )
        )

    temporary_path = (
        DATA_DIR /
        f"uploaded{extension}"
    )

    try:

        contents = await file.read()

        with open(
            temporary_path,
            "wb"
        ) as f:

            f.write(contents)

        # Parse uploaded file
        df = parse_uploaded_file(
            temporary_path
        )

        validate_feedback_dataframe(
            df
        )

        print(
            f"Parsed {len(df)} feedback entries "
            f"from {file.filename}"
        )

        # Save standardized data
        df.to_csv(
            CURRENT_DATA_PATH,
            index=False
        )

        # Run ML pipeline
        update_analysis()

        current_filename = (
            file.filename
        )

        response = {
            "message": (
                "File uploaded and "
                "analyzed successfully."
            ),

            "filename": current_filename,

            "format": extension,

            "rows": int(len(df)),

            "columns": list(
                df.columns
            ),

            "stats": dataset_stats,

            "timeline": timeline_data,

            "insights": pain_points,
        }

        return JSONResponse(
            content=json_safe(
                response
            )
        )

    except Exception as e:

        print(
            "UPLOAD ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        if temporary_path.exists():

            temporary_path.unlink()


# ============================================================
# RE-ANALYZE
# ============================================================

@app.post("/api/analyze")
def analyze_current_dataset():

    if not CURRENT_DATA_PATH.exists():

        raise HTTPException(
            status_code=400,
            detail=(
                "No dataset has been uploaded yet."
            )
        )

    try:

        update_analysis()

        return JSONResponse(
            content=json_safe({
                "message": (
                    "Dataset analyzed successfully."
                ),

                "stats": dataset_stats,

                "timeline": timeline_data,

                "insights": pain_points,
            })
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )