import asyncio
import websockets

clients = set()

async def handler(ws):
    clients.add(ws)
    try:
        async for msg in ws:
            
            parts = msg.split()
            if len(parts) == 2 and parts[0] == "SEND_GARBAGE":
                n = int(parts[1])
                broadcast = f"RECV_GARBAGE {n}"
                
                await asyncio.gather(*[
                    c.send(broadcast) for c in clients
                    if c != ws and c.open
                ], return_exceptions=True)
    finally:
        clients.discard(ws)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("ws server on :8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())