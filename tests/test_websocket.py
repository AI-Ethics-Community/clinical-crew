"""
Tests for WebSocket streaming functionality.
"""
import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.main import app
from app.models.events import (
    BaseStreamEvent,
    GPInterrogatingEvent,
    SpecialistStartedEvent,
    ToolStartedEvent,
    SourceFoundEvent,
    CompletedEvent,
)
from app.core.event_emitter import event_emitter


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_consultation():
    """Mock consultation data"""
    return {
        "consulta_id": "test-consultation-123",
        "estado": "interrogando",
        "original_consultation": "Patient with chest pain",
        "patient_context": {
            "edad": 45,
            "sexo": "M"
        }
    }


@pytest.mark.asyncio
class TestWebSocketEndpoint:
    """Tests for WebSocket endpoint"""
    
    async def test_websocket_connection(self, client, mock_consultation):
        """Test basic WebSocket connection"""
        with patch('app.models.database.MedicalConsultation.get', 
                   new=AsyncMock(return_value=MagicMock(**mock_consultation))):
            
            with client.websocket_connect(f"/api/v1/ws/consultation/{mock_consultation['consulta_id']}") as websocket:
                # Should receive initial connection event
                data = websocket.receive_text()
                message = json.loads(data)
                
                assert message["event_type"] == "connected"
                assert message["consulta_id"] == mock_consultation["consulta_id"]
                assert message["data"]["estado"] == "interrogando"
    
    async def test_websocket_consultation_not_found(self, client):
        """Test WebSocket connection with non-existent consultation"""
        with patch('app.models.database.MedicalConsultation.get', 
                   new=AsyncMock(return_value=None)):
            
            with pytest.raises(Exception):
                with client.websocket_connect("/api/v1/ws/consultation/non-existent"):
                    pass
    
    async def test_websocket_event_streaming(self, client, mock_consultation):
        """Test receiving events through WebSocket"""
        with patch('app.models.database.MedicalConsultation.get', 
                   new=AsyncMock(return_value=MagicMock(**mock_consultation))):
            
            with client.websocket_connect(f"/api/v1/ws/consultation/{mock_consultation['consulta_id']}") as websocket:
                # Receive initial connection event
                websocket.receive_text()
                
                # Emit test event
                test_event = GPInterrogatingEvent(
                    consulta_id=mock_consultation["consulta_id"],
                    data={"status": "started"}
                )
                
                await event_emitter.emit_consultation(
                    mock_consultation["consulta_id"],
                    test_event
                )
                
                # Should receive the emitted event
                data = websocket.receive_text()
                message = json.loads(data)
                
                assert message["event_type"] == "gp_interrogating"
                assert message["data"]["status"] == "started"
    
    async def test_websocket_multiple_events(self, client, mock_consultation):
        """Test receiving multiple events in sequence"""
        with patch('app.models.database.MedicalConsultation.get', 
                   new=AsyncMock(return_value=MagicMock(**mock_consultation))):
            
            with client.websocket_connect(f"/api/v1/ws/consultation/{mock_consultation['consulta_id']}") as websocket:
                websocket.receive_text()  # Initial connection
                
                # Emit multiple events
                events = [
                    GPInterrogatingEvent(
                        consulta_id=mock_consultation["consulta_id"],
                        data={"status": "started"}
                    ),
                    SpecialistStartedEvent(
                        consulta_id=mock_consultation["consulta_id"],
                        data={"specialty": "cardiology"}
                    ),
                    ToolStartedEvent(
                        consulta_id=mock_consultation["consulta_id"],
                        data={"tool": "pubmed_search"}
                    ),
                ]
                
                for event in events:
                    await event_emitter.emit_consultation(
                        mock_consultation["consulta_id"],
                        event
                    )
                
                # Receive all events
                received_events = []
                for _ in range(len(events)):
                    data = websocket.receive_text()
                    received_events.append(json.loads(data))
                
                assert len(received_events) == len(events)
                assert received_events[0]["event_type"] == "gp_interrogating"
                assert received_events[1]["event_type"] == "specialist_started"
                assert received_events[2]["event_type"] == "tool_started"
    
    async def test_websocket_client_disconnect(self, client, mock_consultation):
        """Test WebSocket cleanup on client disconnect"""
        with patch('app.models.database.MedicalConsultation.get', 
                   new=AsyncMock(return_value=MagicMock(**mock_consultation))):
            
            with client.websocket_connect(f"/api/v1/ws/consultation/{mock_consultation['consulta_id']}") as websocket:
                websocket.receive_text()  # Initial connection
                # Connection closes when exiting context
            
            # After disconnect, manager should have cleaned up
            from app.api.v1.websockets import ws_manager
            assert mock_consultation["consulta_id"] not in ws_manager.active_connections


@pytest.mark.asyncio
class TestSSEEndpoint:
    """Tests for Server-Sent Events endpoint"""
    
    async def test_sse_connection(self, client, mock_consultation):
        """Test SSE connection and initial event"""
        with patch('app.models.database.MedicalConsultation.get', 
                   new=AsyncMock(return_value=MagicMock(**mock_consultation))):
            
            response = client.get(
                f"/api/v1/consultation/{mock_consultation['consulta_id']}/stream",
                stream=True
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            assert response.headers["cache-control"] == "no-cache"
    
    async def test_sse_consultation_not_found(self, client):
        """Test SSE endpoint with non-existent consultation"""
        with patch('app.models.database.MedicalConsultation.get', 
                   new=AsyncMock(return_value=None)):
            
            response = client.get("/api/v1/consultation/non-existent/stream")
            assert response.status_code == 404


@pytest.mark.asyncio
class TestEventEmitter:
    """Tests for event emitter functionality"""
    
    async def test_emit_consultation_event(self, mock_consultation):
        """Test emitting event to specific consultation"""
        callback_called = False
        received_event = None
        
        async def test_callback(event: BaseStreamEvent):
            nonlocal callback_called, received_event
            callback_called = True
            received_event = event
        
        # Register callback
        event_emitter.on_consultation(
            mock_consultation["consulta_id"],
            test_callback
        )
        
        # Emit event
        test_event = CompletedEvent(
            consulta_id=mock_consultation["consulta_id"],
            data={"status": "completed"}
        )
        
        await event_emitter.emit_consultation(
            mock_consultation["consulta_id"],
            test_event
        )
        
        assert callback_called
        assert received_event.event_type == "completed"
        
        # Cleanup
        event_emitter.clear_consultation(mock_consultation["consulta_id"])
    
    async def test_multiple_callbacks(self, mock_consultation):
        """Test multiple callbacks for same consultation"""
        callback_count = 0
        
        async def callback1(event: BaseStreamEvent):
            nonlocal callback_count
            callback_count += 1
        
        async def callback2(event: BaseStreamEvent):
            nonlocal callback_count
            callback_count += 1
        
        # Register multiple callbacks
        event_emitter.on_consultation(mock_consultation["consulta_id"], callback1)
        event_emitter.on_consultation(mock_consultation["consulta_id"], callback2)
        
        # Emit event
        test_event = BaseStreamEvent(
            event_type="test",
            consulta_id=mock_consultation["consulta_id"]
        )
        
        await event_emitter.emit_consultation(
            mock_consultation["consulta_id"],
            test_event
        )
        
        # Both callbacks should be called
        assert callback_count == 2
        
        # Cleanup
        event_emitter.clear_consultation(mock_consultation["consulta_id"])


@pytest.mark.asyncio
class TestWebSocketManager:
    """Tests for WebSocket manager"""
    
    async def test_manager_multiple_connections(self, mock_consultation):
        """Test manager handling multiple connections to same consultation"""
        from app.api.v1.websockets import ws_manager
        
        # Create mock WebSocket connections
        ws1 = MagicMock()
        ws1.send_text = AsyncMock()
        
        ws2 = MagicMock()
        ws2.send_text = AsyncMock()
        
        # Connect both
        await ws_manager.connect(mock_consultation["consulta_id"], ws1)
        await ws_manager.connect(mock_consultation["consulta_id"], ws2)
        
        assert len(ws_manager.active_connections[mock_consultation["consulta_id"]]) == 2
        
        # Send event - both should receive
        test_event = BaseStreamEvent(
            event_type="test",
            consulta_id=mock_consultation["consulta_id"]
        )
        
        await ws_manager.send_to_consultation(
            mock_consultation["consulta_id"],
            test_event
        )
        
        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()
        
        # Disconnect
        ws_manager.disconnect(mock_consultation["consulta_id"], ws1)
        ws_manager.disconnect(mock_consultation["consulta_id"], ws2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
