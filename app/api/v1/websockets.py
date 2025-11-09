"""
WebSocket endpoints para streaming en tiempo real.
"""
import asyncio
import json
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from app.core.event_emitter import event_emitter
from app.models.events import BaseStreamEvent
from app.models.database import MedicalConsultation

router = APIRouter()


class WebSocketManager:
    """Manager para conexiones WebSocket activas"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, consulta_id: str, websocket: WebSocket):
        """Conectar nuevo cliente WebSocket"""
        await websocket.accept()
        
        if consulta_id not in self.active_connections:
            self.active_connections[consulta_id] = set()
        
        self.active_connections[consulta_id].add(websocket)
        
        # Registrar callback para eventos de esta consulta
        async def send_event(event: BaseStreamEvent):
            await self.send_to_consultation(consulta_id, event)
        
        event_emitter.on_consultation(consulta_id, send_event)
        
        print(f"✓ WebSocket connected for consultation {consulta_id}")
    
    def disconnect(self, consulta_id: str, websocket: WebSocket):
        """Desconectar cliente WebSocket"""
        if consulta_id in self.active_connections:
            self.active_connections[consulta_id].discard(websocket)
            
            if not self.active_connections[consulta_id]:
                del self.active_connections[consulta_id]
                event_emitter.clear_consultation(consulta_id)
        
        print(f"✗ WebSocket disconnected for consultation {consulta_id}")
    
    async def send_to_consultation(self, consulta_id: str, event: BaseStreamEvent):
        """Enviar evento a todos los clientes de una consulta"""
        if consulta_id not in self.active_connections:
            return
        
        # Serializar evento
        message = json.dumps(event.model_dump(), default=str)
        
        # Enviar a todos los clientes conectados
        dead_connections = set()
        for connection in self.active_connections[consulta_id]:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error sending to WebSocket: {str(e)}")
                dead_connections.add(connection)
        
        # Limpiar conexiones muertas
        for conn in dead_connections:
            self.disconnect(consulta_id, conn)
    
    async def broadcast(self, event: BaseStreamEvent):
        """Broadcast evento a todos los clientes"""
        for consulta_id in self.active_connections:
            await self.send_to_consultation(consulta_id, event)


# Instancia global del manager
ws_manager = WebSocketManager()


@router.websocket("/ws/consultation/{consulta_id}")
async def websocket_endpoint(websocket: WebSocket, consulta_id: str):
    """
    WebSocket endpoint para streaming de eventos de consulta.
    
    Args:
        websocket: Conexión WebSocket
        consulta_id: ID de la consulta
    """
    # Verificar que la consulta existe
    consulta = await MedicalConsultation.get(consulta_id)
    if not consulta:
        await websocket.close(code=1008, reason="Consultation not found")
        return
    
    await ws_manager.connect(consulta_id, websocket)
    
    try:
        # Enviar estado inicial
        initial_event = BaseStreamEvent(
            event_type="connected",
            consulta_id=consulta_id,
            data={
                "status": consulta.status,
                "message": "Connected to consultation stream"
            }
        )
        await websocket.send_text(json.dumps(initial_event.model_dump(), default=str))
        
        # Mantener conexión abierta y escuchar mensajes del cliente
        while True:
            try:
                data = await websocket.receive_text()
                # Aquí se pueden procesar mensajes del cliente si es necesario
                # Por ejemplo, respuestas a preguntas de interrogación
                message = json.loads(data)
                
                if message.get("type") == "user_response":
                    # Procesar respuesta del usuario (se implementará después)
                    pass
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "error": "Invalid JSON format"
                }))
    
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    
    finally:
        ws_manager.disconnect(consulta_id, websocket)


@router.get("/consultation/{consulta_id}/stream")
async def sse_stream(consulta_id: str):
    """
    Server-Sent Events endpoint como alternativa a WebSocket.
    
    Args:
        consulta_id: ID de la consulta
    
    Returns:
        StreamingResponse con eventos SSE
    """
    # Verificar que la consulta existe
    consulta = await MedicalConsultation.get(consulta_id)
    if not consulta:
        raise HTTPException(status_code=404, detail="Consultation not found")
    
    async def event_generator():
        """Generador de eventos SSE"""
        queue = asyncio.Queue()
        
        # Callback para agregar eventos a la cola
        async def queue_event(event: BaseStreamEvent):
            await queue.put(event)
        
        # Registrar callback
        event_emitter.on_consultation(consulta_id, queue_event)
        
        try:
            # Enviar evento inicial
            yield f"event: connected\n"
            yield f"data: {json.dumps({'consulta_id': consulta_id, 'status': consulta.status})}\n\n"
            
            # Stream de eventos
            while True:
                try:
                    # Esperar evento con timeout para heartbeat
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Enviar evento
                    yield f"event: {event.event_type}\n"
                    yield f"data: {json.dumps(event.model_dump(), default=str)}\n\n"
                
                except asyncio.TimeoutError:
                    # Enviar heartbeat cada 30 segundos
                    yield f"event: heartbeat\n"
                    yield f"data: {json.dumps({'timestamp': str(asyncio.get_event_loop().time())})}\n\n"
        
        except asyncio.CancelledError:
            pass
        
        finally:
            # Limpiar callback
            event_emitter.off_consultation(consulta_id, queue_event)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
