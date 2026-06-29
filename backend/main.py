# backend/main.py
# FastAPI entrypoint for Ally AI

from fastapi import FastAPI

app = FastAPI()

@app.get('/')
def root():
    return {'status': 'Ally AI backend placeholder'}

