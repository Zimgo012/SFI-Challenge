from fastapi import FastAPI

from controller.health_controller import router as health_router

app = FastAPI(title='SFI Challenge API', version='0.1.0')
app.include_router(health_router)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('main:app', host='127.0.0.1', port=8000, reload=True)
