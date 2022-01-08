import json
import os

import dotenv
import fastapi
import rich
import uvicorn
from rich import traceback as rich_traceback
from starlette.middleware.cors import ALL_METHODS, CORSMiddleware
from starlette.responses import HTMLResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

import example_models
import websocket_example

# https://rich.readthedocs.io/en/latest/traceback.html
# Prettify traceback
rich_traceback.install()

dotenv.load_dotenv()

app = fastapi.FastAPI(
    version="0.0.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=ALL_METHODS,
    allow_headers=["*"],
)


@app.post(
    path="/ping/",
    response_class=fastapi.Response,
)
async def ping(any_request: fastapi.Request) -> fastapi.Response:
    try:
        body = json.loads(await any_request.body())
    except json.decoder.JSONDecodeError:
        return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)
    rich.print(body)
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@app.post(
    path="/request/",
    response_model=example_models.ExampleRequest,
)
async def post_request(
    example_request: example_models.ExampleRequest,
) -> example_models.ExampleRequest:
    """Example of post request"""
    return example_request


@app.get(
    path="/list-request/",
    response_model=list[example_models.GetExampleResponse],
)
async def request(
    count: int = 5,
    choices_text: example_models.TextEnum = None,
) -> list[example_models.GetExampleResponse]:
    """Example of post request"""
    return [
        example_models.GetExampleResponse(
            number=i,
            choices_text=choices_text,
        )
        for i in range(count)
    ]


@app.get("/web-socker-example/")
async def get():
    with open("websocket-example.html") as file:
        return HTMLResponse(
            file.read().replace(
                "{backend_url}", os.environ["BACKEND_URL_WS"],
            )
        )


@app.websocket("/ws/{chat}/")
async def websocket_endpoint(
    websocket: WebSocket,
    chat: str,
    client_name: str,
):
    chat_manager = websocket_example.ChatConnectionManager.get_chat(
        chat_name=chat,
    )
    client_id = await chat_manager.connect(
        client_name=client_name,
        websocket=websocket,
    )
    try:
        while True:
            data = await websocket.receive_json()
            rich.print(data)
            await chat_manager.process_event(
                client_id=client_id,
                event_data=data
            )
    except WebSocketDisconnect:
        await chat_manager.disconnect(client_id=client_id)


if __name__ == '__main__':
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
