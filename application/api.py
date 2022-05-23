from fastapi import FastAPI, APIRouter

from application.worker import my_task


def setup_application() -> FastAPI:

    app = FastAPI(
        title='Test Application',
        version='0.1.0',
        description='Replicating an issue.'
    )

    api_router = APIRouter(prefix='/api')

    @api_router.post(path='/run-task')
    async def run_task():
        my_task.delay()

    @api_router.get(path='/status')
    async def run_task():
        return {'msg': 'Greetings!'}

    app.include_router(api_router)

    return app