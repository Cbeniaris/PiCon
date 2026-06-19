import asyncio
import json
import subprocess
import evdev
from evdev import InputDevice, categorize, ecodes
import websockets

CONTROLLER_PATH = "/dev/input/event0"
CLIENTS = set()


SHUTDOWN_HOLD_SECONDS = 2
SHUTDOWN_COMBO = {"start", "select"}
 
held_buttons = set()
shutdown_task = None
 
 
async def trigger_shutdown():
    await asyncio.sleep(SHUTDOWN_HOLD_SECONDS)
    print("Start+Select held — shutting down.")
    subprocess.run(["sudo", "shutdown", "-h", "now"])
 
 
def on_button_press(button):
    global shutdown_task
    held_buttons.add(button)
    if SHUTDOWN_COMBO.issubset(held_buttons) and shutdown_task is None:
        print(f"Start+Select held — shutdown in {SHUTDOWN_HOLD_SECONDS}s if not released.")
        shutdown_task = asyncio.ensure_future(trigger_shutdown())
 
 
def on_button_release(button):
    global shutdown_task
    held_buttons.discard(button)
    if not SHUTDOWN_COMBO.issubset(held_buttons) and shutdown_task is not None:
        shutdown_task.cancel()
        shutdown_task = None
        print("Shutdown cancelled.")


BUTTON_MAP = {
    306:  "a",
    305:  "b",
    307:  "a",
    304:  "b",
    308:  "l",
    309:  "r",
    310:  "l2",
    311:  "r2",
    312:  "select",
    313:  "start",
    314: "l3",
    315: "r3",
    12: "up",
    13: "down",
    14: "left",
    15: "right",
    16: "home",
}

async def broadcast(message):
    if CLIENTS:
        await asyncio.gather(*[client.send(message) for client in CLIENTS])

async def read_controller():
    try:
        dev = evdev.InputDevice(CONTROLLER_PATH)
        print(f"Controller found: {dev.name}")
    except Exception as e:
        print(f"Controller not found: {e}")
        return

    async for event in dev.async_read_loop():
        if event.type == ecodes.EV_KEY:
            state = "press" if event.value == 1 else "release"
            button = BUTTON_MAP.get(event.code, f"btn_{event.code}")
            msg = json.dumps({"type": state, "button": button})
            print(msg)
            await broadcast(msg)
        elif event.type == ecodes.EV_ABS:
            if event.code == 16:  # left/right
                if event.value == -1:
                    await broadcast(json.dumps({"type": "press", "button": "left"}))
                elif event.value == 1:
                    await broadcast(json.dumps({"type": "press", "button": "right"}))
                else:
                    await broadcast(json.dumps({"type": "release", "button": "left"}))
                    await broadcast(json.dumps({"type": "release", "button": "right"}))
            elif event.code == 17:  # up/down
                if event.value == -1:
                    await broadcast(json.dumps({"type": "press", "button": "up"}))
                elif event.value == 1:
                    await broadcast(json.dumps({"type": "press", "button": "down"}))
                else:
                    await broadcast(json.dumps({"type": "release", "button": "up"}))
                    await broadcast(json.dumps({"type": "release", "button": "down"}))

async def ws_handler(websocket):
    CLIENTS.add(websocket)
    print(f"Client connected: {websocket.remote_address}")
    try:
        await websocket.wait_closed()
    finally:
        CLIENTS.discard(websocket)
        print(f"Client disconnected")

async def main():
    print("Starting WebSocket server on 0.0.0.0:8765")
    async with websockets.serve(ws_handler, "0.0.0.0", 8765):
        await read_controller()

asyncio.run(main())
