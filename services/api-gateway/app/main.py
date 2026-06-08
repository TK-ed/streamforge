from fastapi import FastAPI

app = FastAPI(title="StreamForge")


@app.get("/")
def health():
    return {"status": "healthy"}
