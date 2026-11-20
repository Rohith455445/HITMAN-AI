"""Optional HITMAN AI Gemini Live proxy, disabled in public demos by default.

Server-side key only; no arbitrary tools and no computer control. Each session is
limited to one short session. Install optional requirements-voice.txt to enable.
Audio protocol: PCM16 mono 16 kHz in, 24 kHz out, base64 WebSocket JSON frames.
"""
from __future__ import annotations
import asyncio
import base64
import binascii
import os
from urllib.parse import urlparse

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

_slots = asyncio.Semaphore(1)


def allowed_origin(origin: str | None, base_url: str) -> bool:
    if not origin:
        return False
    try:
        a, b = urlparse(origin), urlparse(base_url)
        return (a.scheme, a.netloc) == (b.scheme, b.netloc) and a.scheme in {'https', 'http'}
    except (ValueError, TypeError):
        return False


async def serve_live_voice(ws: WebSocket, *, enabled: bool, public_demo: bool):
    if not (enabled and public_demo and os.getenv('GEMINI_API_KEY')):
        await ws.close(code=1008)
        return
    expected = os.getenv('PUBLIC_BASE_URL') or str(ws.url).replace('ws://','http://').replace('wss://','https://').split('/api/',1)[0]
    if not allowed_origin(ws.headers.get('origin'), expected):
        await ws.close(code=1008)
        return
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        await ws.accept()
        await ws.send_json({'type':'error','message':'Live voice requires optional google-genai dependency.'})
        await ws.close(code=1011)
        return
    try:
        await asyncio.wait_for(_slots.acquire(), timeout=0.2)
    except asyncio.TimeoutError:
        await ws.close(code=1013)
        return
    accepted = False
    try:
        await ws.accept()
        accepted = True
        client = genai.Client(api_key=os.environ['GEMINI_API_KEY'],
                              http_options={'api_version':'v1beta'})
        model = os.getenv('GEMINI_LIVE_MODEL', 'gemini-2.5-flash-native-audio-preview-12-2025')
        config = {'response_modalities':['AUDIO'], 'input_audio_transcription':{}, 'output_audio_transcription':{}}
        async with client.aio.live.connect(model=model, config=config) as session:
            await ws.send_json({'type':'ready','message':'Live audio connected. Speak normally.'})
            async def upstream():
                received = 0
                while True:
                    packet = await ws.receive_json()
                    if not isinstance(packet, dict):
                        break
                    if packet.get('type') == 'end':
                        break
                    if packet.get('type') != 'audio':
                        continue
                    chunk = packet.get('data')
                    if not isinstance(chunk,str) or len(chunk)>47_000:
                        break
                    try:
                        raw=base64.b64decode(chunk,validate=True)
                    except (binascii.Error, ValueError):
                        break
                    received += len(raw)
                    if received > 3_000_000 or len(raw)%2:
                        break
                    await session.send_realtime_input(audio=types.Blob(data=raw,mime_type='audio/pcm;rate=16000'))
            async def downstream():
                while True:
                    async for response in session.receive():
                        content = response.server_content
                        if content is None:
                            continue
                        if content.input_transcription and content.input_transcription.text:
                            await ws.send_json({'type':'transcript','speaker':'you',
                                'text':content.input_transcription.text[:2000]})
                        if content.output_transcription and content.output_transcription.text:
                            await ws.send_json({'type':'transcript','speaker':'AI',
                                'text':content.output_transcription.text[:2000]})
                        if content.model_turn:
                            for part in content.model_turn.parts:
                                if part.inline_data and part.inline_data.data:
                                    raw=part.inline_data.data
                                    await ws.send_json({'type':'audio','data':base64.b64encode(raw).decode('ascii')})
            tasks=[asyncio.create_task(upstream()),asyncio.create_task(downstream())]
            try:
                done,pending=await asyncio.wait(tasks,timeout=100,return_when=asyncio.FIRST_COMPLETED)
            finally:
                for task in tasks:task.cancel()
                await asyncio.gather(*tasks,return_exceptions=True)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as exc:
        print('Gemini Live failed:',type(exc).__name__)
        if accepted:
            try:await ws.send_json({'type':'error','message':'Live session failed; check voice model access or quota.'})
            except Exception:pass
    finally:
        _slots.release()
        try:await ws.close()
        except Exception:pass
