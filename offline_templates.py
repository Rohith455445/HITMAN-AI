"""Small deterministic, license-neutral starter projects bundled with HITMAN AI.

These projects do not use the Gemini API to generate files. They remain starter
projects and may require external dependencies or a user-provided API key.
"""
from __future__ import annotations

from studio_engine import build_archive

STARTERS = {
    'ai_bot': {
        'name':'Gemini AI Bot Starter',
        'summary':'Minimal FastAPI bot with environment-based Gemini key and a mocked unit test.',
        'files':[
            {'path':'requirements.txt','content':'fastapi>=0.115,<1\nuvicorn>=0.30,<1\nhttpx>=0.27,<1\npytest>=8\n'},
            {'path':'bot.py','content':'''"""Minimal Gemini bot. Keep credentials in environment variables."""
import os
import httpx

GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')


def reply(message: str) -> str:
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError('Set GEMINI_API_KEY in your environment (never in code).')
    endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent'
    payload = {'contents': [{'role': 'user', 'parts': [{'text': message}]}]}
    with httpx.Client(timeout=40) as client:
        response = client.post(endpoint, headers={'x-goog-api-key': api_key}, json=payload)
        response.raise_for_status()
        data = response.json()
    return ''.join(p.get('text','') for p in data['candidates'][0]['content']['parts']).strip()
'''},
            {'path':'app.py','content':'''"""Simple AI bot HTTP endpoint; protect this before public deployment."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from bot import reply

app = FastAPI(title='Gemini Bot Starter')


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/chat')
def chat(body: ChatRequest):
    try:
        return {'reply': reply(body.message)}
    except Exception:
        raise HTTPException(status_code=502, detail='Model request failed; check configuration or quota')
'''},
            {'path':'tests/test_app.py','content':'''from fastapi.testclient import TestClient
import app


def test_chat_without_live_api(monkeypatch):
    monkeypatch.setattr(app, 'reply', lambda message: 'Received: ' + message)
    client = TestClient(app.app)
    assert client.get('/health').status_code == 200
    assert client.post('/chat', json={'message':'hello'}).json()['reply'] == 'Received: hello'
    assert client.post('/chat', json={'message':''}).status_code == 422
'''},
            {'path':'README.md','content':'''# Gemini AI Bot Starter

A minimal **development** bot. It is not production-secure and requires a Gemini API key for live responses.

1. `python -m venv .venv`
2. Activate your environment (Windows: `.venv\\Scripts\\activate`; macOS/Linux: `source .venv/bin/activate`).
3. `pip install -r requirements.txt`
4. Set `GEMINI_API_KEY` as a secret environment variable. Example PowerShell: `$env:GEMINI_API_KEY = 'your_private_key'`.
5. `uvicorn app:app --reload`
6. Open `http://127.0.0.1:8000/docs`; test `POST /chat`.
7. `pytest -q` runs offline mocked tests.

For a public deployment add auth, abuse controls, quota protection, logging redaction, HTTPS and persistent storage as needed. Model IDs and free-tier access may change.
'''}
        ]
    },
    'ml_model':{
        'name':'Reproducible Classification Model Starter',
        'summary':'scikit-learn Iris training, evaluation and inference pipeline, no fabricated results.',
        'files':[
            {'path':'requirements.txt','content':'scikit-learn>=1.4,<2\njoblib>=1.3,<2\npytest>=8\n'},
            {'path':'train.py','content':'''"""Reproducible baseline on scikit-learn's built-in Iris example dataset."""
from pathlib import Path
import joblib
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report


def train(model_path='model.joblib'):
    data = load_iris()
    X_train, X_test, y_train, y_test = train_test_split(
        data.data, data.target, test_size=0.25, random_state=42,
        stratify=data.target)
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    model.fit(X_train, y_train)
    predicted = model.predict(X_test)
    score = float(accuracy_score(y_test, predicted))
    joblib.dump(model, model_path)
    return score, classification_report(y_test, predicted, target_names=list(data.target_names))


if __name__ == '__main__':
    accuracy, report = train()
    print('Measured holdout accuracy:', accuracy)
    print(report)
'''},
            {'path':'predict.py','content':'''"""Predict Iris species from four flower measurements in centimeters."""
import argparse
import joblib


def infer(features, model_path='model.joblib'):
    if len(features) != 4:
        raise ValueError('Expected 4 numeric Iris features')
    model = joblib.load(model_path)
    return int(model.predict([features])[0])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('measurements', type=float, nargs=4)
    args = parser.parse_args()
    print('Predicted class index:', infer(args.measurements))
'''},
            {'path':'tests/test_pipeline.py','content':'''from train import train
from predict import infer


def test_training_pipeline(tmp_path):
    path = tmp_path / 'model.joblib'
    accuracy, report = train(path)
    assert path.is_file()
    assert 0 <= accuracy <= 1
    assert 'precision' in report
    assert infer([5.1,3.5,1.4,0.2], path) in {0,1,2}
'''},
            {'path':'README.md','content':'''# ML Classification Starter

**Training has not yet been run by HITMAN AI.** This starter demonstrates a reproducible Iris classification baseline using a real, built-in example dataset. Do not generalize results to your own dataset.

1. `python -m venv .venv`
2. Activate it; install: `pip install -r requirements.txt`
3. `python train.py` prints computed evaluation metrics and writes `model.joblib`.
4. `python predict.py 5.1 3.5 1.4 0.2`
5. `pytest -q` runs local tests.

Replace the Iris loader with your actual dataset, enforce train/validation/test separation, check leakage and bias, and tune evaluation metrics for the real task.
'''}
        ]
    },
    'data_science':{
        'name':'CSV Data Science Profiler',
        'summary':'Local CSV nulls, numeric summaries and column types, no data uploaded to HITMAN AI.',
        'files':[
            {'path':'requirements.txt','content':'pandas>=2.0,<3\nmatplotlib>=3.7,<4\npytest>=8\n'},
            {'path':'analyze.py','content':'''"""A local CSV profiler. No upload; figures and reports remain on your computer."""
import argparse
from pathlib import Path
import pandas as pd


def profile(path):
    data = pd.read_csv(path)
    if data.empty:
        raise ValueError('CSV contains no data rows')
    return {'rows': len(data), 'columns': len(data.columns),
            'missing': data.isna().sum().to_dict(),
            'dtypes': {str(col): str(dtype) for col,dtype in data.dtypes.items()},
            'numeric_summary': data.describe(include='number').to_dict() if len(data.select_dtypes(include='number').columns) else {}}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description='Profile a local CSV dataset')
    parser.add_argument('csv_path', type=Path)
    parser.add_argument('--output', type=Path, default=Path('report.json'))
    args=parser.parse_args()
    import json
    result=profile(args.csv_path)
    args.output.write_text(json.dumps(result, indent=2, default=str),encoding='utf-8')
    print('Wrote:', args.output)
'''},
            {'path':'tests/test_profile.py','content':'''from analyze import profile


def test_profile(tmp_path):
    path=tmp_path/'sample.csv'
    path.write_text('age,score\\n20,81\\n,75\\n', encoding='utf8')
    data=profile(path)
    assert data['rows']==2
    assert data['missing']['age']==1
    assert 'score' in data['numeric_summary']
'''},
            {'path':'README.md','content':'''# CSV Data Science Profiler

Runs entirely on your computer, not inside the hosted HITMAN AI chat service. Does not upload data.

1. `python -m venv .venv`
2. Activate it; `pip install -r requirements.txt`
3. `python analyze.py path/to/your_dataset.csv --output report.json`
4. `pytest -q`

Reports actual row count, per-column missing values and numeric statistics. No results are fabricated. Always review column types, sampling bias, data privacy and data sources before drawing conclusions.
'''}
        ]
    }
}


def offline_template(kind: str):
    if kind not in STARTERS:
        raise KeyError(kind)
    return build_archive(STARTERS[kind],kind)
