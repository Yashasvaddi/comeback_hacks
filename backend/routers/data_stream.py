
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from services.data_stream_service import (
    AVAILABLE_DATASETS,
    data_stream_service,
)

router = APIRouter(tags=["Data Stream"])


class DatasetSwitchRequest(BaseModel):
    dataset: str = Field(
        ...,
        description="Dataset to activate: dataset_1, dataset_2, or dataset_3",
    )


@router.get("/api/data-stream/datasets")
async def list_datasets():
    return {
        "datasets": list(AVAILABLE_DATASETS.keys()),
    }


@router.get("/api/data-stream/status")
async def stream_status():
    try:
        return await data_stream_service.get_status()
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/data-stream/switch")
async def switch_dataset(request: DatasetSwitchRequest):
    try:
        return await data_stream_service.switch_dataset(request.dataset)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.websocket("/ws/data-stream")
async def websocket_data_stream(websocket: WebSocket):
    try:
        await data_stream_service.connect(websocket)

        # Keep the connection open while the server streams records.
        # REST is responsible for switching datasets.
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        pass
    finally:
        await data_stream_service.disconnect(websocket)
