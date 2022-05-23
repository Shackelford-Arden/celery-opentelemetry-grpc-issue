import uvicorn

from application.api import setup_application

app = setup_application()

uvicorn.run(app, host='0.0.0.0', port=8080)
