import argparse
import asyncio, json, time
from pathlib import Path
import httpx, websockets, numpy as np
from skellycam.core.types.frontend_payload_bytearray import FRONTEND_PAYLOAD_HEADER_FOOTER_DTYPE as HEADER

parser=argparse.ArgumentParser(description='Measure capture frame progression through the FreeMoCap API; no images are saved.')
parser.add_argument('--port',type=int,default=53117)
parser.add_argument('--output',default='camera-fps-results.json')
args=parser.parse_args()
BASE=f'http://127.0.0.1:{args.port}'
async def main():
 async with httpx.AsyncClient(timeout=90) as client:
  for _ in range(90):
   try:
    r=await client.get(BASE+'/health')
    if r.is_success:break
   except httpx.ConnectError:pass
   await asyncio.sleep(1)
  r=await client.post(BASE+'/skellycam/camera/detect');r.raise_for_status()
  devices=[c for c in r.json()['cameras'] if 'C922' in c['name']]
  assert len(devices)==3,devices
  configs={c['camera_id']:{'camera_id':c['camera_id'],'camera_index':c['index'],'camera_name':c['name'],'resolution':{'width':1280,'height':720},'framerate':60,'exposure_mode':'AUTO','rotation':-1} for c in devices}
  results=[]
  try:
   for n in [1,3]:
    selected=dict(list(configs.items())[:n])
    r=await client.post(BASE+'/skellycam/camera/group/apply',json={'camera_configs':selected});r.raise_for_status()
    result={'camera_count':n,'apply_response':r.json()}
    async with websockets.connect(f'ws://127.0.0.1:{args.port}/websocket/connect',max_size=32*1024*1024) as ws:
     frames=[];rates=[];start=time.monotonic()
     while time.monotonic()-start<25:
      message=await asyncio.wait_for(ws.recv(),15)
      if isinstance(message,bytes) and message[0]==0:
       h=np.frombuffer(message,dtype=HEADER,count=1)[0];f=int(h['frame_number']);count=int(h['number_of_cameras'])
       await ws.send(json.dumps({'frameNumber':f}))
       if time.monotonic()-start>5:frames.append((time.monotonic(),f,count))
      elif isinstance(message,str):
       data=json.loads(message)
       if data.get('message_type')=='framerate_update':rates.append(data)
     result.update(payloads=len(frames),counts=sorted(set(f[2] for f in frames)),capture_frame_progress_fps=(frames[-1][1]-frames[0][1])/(frames[-1][0]-frames[0][0]) if len(frames)>1 else 0,preview_payload_fps=(len(frames)-1)/(frames[-1][0]-frames[0][0]) if len(frames)>1 else 0,last_framerate_update=rates[-1] if rates else None)
    assert result['counts'] == [n], result
    assert result['capture_frame_progress_fps'] > 0, result
    results.append(result)
    await client.delete(BASE+'/skellycam/camera/group/close/all')
    await asyncio.sleep(2)
  finally:
   await client.delete(BASE+'/skellycam/camera/group/close/all')
   Path(args.output).write_text(json.dumps(results,indent=2))
  print(json.dumps(results,indent=2))
if __name__=='__main__':asyncio.run(main())
