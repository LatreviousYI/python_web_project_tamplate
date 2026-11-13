import uvicorn

from configs import settings


if __name__ == "__main__":
    uvicorn.run("factory.main:app", host=settings.server_host, port=settings.server_port, workers=1)
