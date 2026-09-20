# VoC-Miner

**Voice of Customer Mining System**

VoC-Miner is a machine-learning based system that processes unstructured customer feedback and identifies recurring product problems, pain points, and important customer concerns.

It converts raw feedback into structured insights while keeping the original customer statements available for traceability.

## Features

* Process customer reviews, support tickets, and feedback
* Generate semantic embeddings from customer statements
* Identify recurring pain points and themes
* Group similar feedback
* Separate stronger recurring signals from individual mentions
* Prioritize issues based on evidence across multiple feedback entries
* Trace insights back to the original customer statements
* REST API for integrating the system with other applications

## Technology Stack

### Backend

* Python
* FastAPI
* Uvicorn

### Machine Learning

* Sentence Transformers
* `all-MiniLM-L6-v2`
* Scikit-learn
* PyTorch

### Data Processing

* Pandas
* NumPy

### Frontend

* React
* Vite
* Tailwind CSS

## Project Structure

```text
VoC-Miner/
│
├── api/
│   └── index.py
│
├── src/
│   ├── main.py
│   ├── preprocessing.py
│   └── ...
│
├── data/
│   └── feedback.csv
│
├── requirements.txt
├── Dockerfile
├── .dockerignore
└── README.md
```

## How It Works

```text
Customer Feedback
       ↓
Data Preprocessing
       ↓
Text Embeddings
       ↓
Similarity Analysis
       ↓
Recurring Pain Points
       ↓
Evidence & Prioritization
       ↓
Customer Insights
```

The system uses the `all-MiniLM-L6-v2` sentence-transformer model to convert customer feedback into numerical embeddings.

Similar feedback can then be identified using semantic similarity rather than relying only on exact keyword matches.

## Installation

Clone the repository:

```bash
git clone :`https://github.com/poornasai372/VoC-Miner`
cd VoC-Miner
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Backend

Run the FastAPI application:

```bash
uvicorn api.index:app --reload
```

The API will normally be available at:

```text
http://127.0.0.1:8000
```

FastAPI documentation:

```text
http://127.0.0.1:8000/docs
```

## Running with Docker

Build the Docker image:

```bash
docker build -t voc-miner .
```

Run the container:

```bash
docker run -p 8000:8000 voc-miner
```

The API can then be accessed at:

```text
http://localhost:8000
```

## Deployment

The project includes a `Dockerfile`, allowing it to be deployed on platforms that support Docker containers.

The application uses the `PORT` environment variable when deployed:

```text
uvicorn api.index:app --host 0.0.0.0 --port ${PORT:-8000}
```

This allows the hosting platform to provide its own port.

## Example Input

```json
{
  "feedback": "The application takes too long to load whenever I open the dashboard."
}
```

## Example Insight

```text
Pain Point:
Slow dashboard loading

Evidence:
Multiple customers reported long loading times when opening the dashboard.

Priority:
High

Source:
Original customer feedback
```

## Requirements

The main Python dependencies are listed in:

```text
requirements.txt
```

The project requires Python and the dependencies specified in the requirements file.

## Project Goal

The goal of VoC-Miner is to help teams move from large amounts of unstructured customer feedback to evidence-backed product insights.

Instead of manually reading every review or support ticket, the system helps identify recurring problems and connects those problems back to the feedback that produced them.

## License

This project is for educational and development purposes.

