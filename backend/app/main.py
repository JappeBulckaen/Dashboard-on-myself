from fastapi import FastAPI

app = FastAPI(title="Dashboard on Myself API")


@app.get("/health")
def health_check():
    return {"status": "ok"}
