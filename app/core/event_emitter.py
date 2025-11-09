"""
Sistema de emisión de eventos para comunicación en tiempo real.
"""
import asyncio
from typing import Dict, Set, Callable, Any
from collections import defaultdict
import json
from app.models.events import BaseStreamEvent


class EventEmitter:
    """Emisor de eventos para broadcast a múltiples clientes"""
    
    def __init__(self):
        self._listeners: Dict[str, Set[Callable]] = defaultdict(set)
        self._consultation_listeners: Dict[str, Set[Callable]] = defaultdict(set)
    
    def on(self, event_type: str, callback: Callable) -> None:
        """
        Registrar listener para tipo de evento.
        
        Args:
            event_type: Tipo de evento a escuchar
            callback: Función callback a ejecutar
        """
        self._listeners[event_type].add(callback)
    
    def off(self, event_type: str, callback: Callable) -> None:
        """
        Remover listener de tipo de evento.
        
        Args:
            event_type: Tipo de evento
            callback: Función callback a remover
        """
        if event_type in self._listeners:
            self._listeners[event_type].discard(callback)
    
    def on_consultation(self, consulta_id: str, callback: Callable) -> None:
        """
        Registrar listener para consulta específica.
        
        Args:
            consulta_id: ID de la consulta
            callback: Función callback a ejecutar
        """
        self._consultation_listeners[consulta_id].add(callback)
    
    def off_consultation(self, consulta_id: str, callback: Callable) -> None:
        """
        Remover listener de consulta específica.
        
        Args:
            consulta_id: ID de la consulta
            callback: Función callback a remover
        """
        if consulta_id in self._consultation_listeners:
            self._consultation_listeners[consulta_id].discard(callback)
    
    async def emit(self, event: BaseStreamEvent) -> None:
        """
        Emitir evento a todos los listeners.
        
        Args:
            event: Evento a emitir
        """
        # Notificar listeners globales del tipo de evento
        if event.event_type in self._listeners:
            tasks = []
            for callback in self._listeners[event.event_type]:
                tasks.append(self._call_async(callback, event))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        # Notificar listeners específicos de la consulta
        if event.consulta_id in self._consultation_listeners:
            tasks = []
            for callback in self._consultation_listeners[event.consulta_id]:
                tasks.append(self._call_async(callback, event))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _call_async(self, callback: Callable, event: BaseStreamEvent) -> None:
        """
        Llamar callback de forma asíncrona.
        
        Args:
            callback: Función a llamar
            event: Evento a pasar
        """
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)
        except Exception as e:
            print(f"Error in event callback: {str(e)}")
    
    def clear_consultation(self, consulta_id: str) -> None:
        """
        Limpiar todos los listeners de una consulta.
        
        Args:
            consulta_id: ID de la consulta
        """
        if consulta_id in self._consultation_listeners:
            del self._consultation_listeners[consulta_id]


# Instancia global del event emitter
event_emitter = EventEmitter()
