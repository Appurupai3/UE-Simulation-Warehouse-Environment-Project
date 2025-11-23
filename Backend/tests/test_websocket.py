"""
Test script for the WebSocket bridge
"""

import asyncio
import json
import websockets
from datetime import datetime

async def test_websocket_connection():
    """Test WebSocket connection to the server"""
    uri = "ws://localhost:8000/ws/test/client1"

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket server")

            # Send an order and wait for confirmation
            order_message = {
                "type": "custom_message",
                "content": "10-20-30",
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send(json.dumps(order_message))
            print(f"Sent order message: {order_message}")

            confirmation = await asyncio.wait_for(websocket.recv(), timeout=5)
            print(f"Received confirmation: {confirmation}")

            # Request the latest orders list
            await websocket.send(json.dumps({
                "type": "get_orders",
                "timestamp": datetime.utcnow().isoformat()
            }))
            orders_response = await asyncio.wait_for(websocket.recv(), timeout=5)
            print(f"Orders response: {orders_response}")

    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    print("Testing WebSocket connection...")
    asyncio.run(test_websocket_connection())
