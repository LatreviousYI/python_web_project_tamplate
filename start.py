import uvicorn


if __name__ == "__main__":
    uvicorn.run("factory.main:app", host="0.0.0.0", port=8779, workers=1)
