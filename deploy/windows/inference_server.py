"""Portable checkpoint inference only. No robot command transport is included."""
import base64
import io
import json
import os
from pathlib import Path
import threading
import time
from contextlib import asynccontextmanager

BASE=Path(os.environ.get('PI05_HOME',str(Path(__file__).resolve().parent)))
CHECKPOINT_STEP=int(json.loads((BASE/'model/export_manifest.json').read_text())['checkpoint_step'])
(BASE/'reports').mkdir(exist_ok=True)
os.environ.setdefault('OPENPI_DATA_HOME',str(BASE/'cache/openpi'))
os.environ.setdefault('XLA_PYTHON_CLIENT_PREALLOCATE','false')
os.environ.setdefault('JAX_COMPILATION_CACHE_DIR',str(BASE/'cache/jax'))
os.environ.setdefault('JAX_PLATFORMS','cuda')
import jax
import jax.numpy as jnp
import numpy as np
from PIL import Image
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import JSONResponse
from openpi import transforms
from openpi.models import model as model_lib,pi05_config,tokenizer
from openpi.shared import normalize,nnx_utils

NAMES=['left_joint_12','left_joint_14','left_joint_24','left_joint_16','left_joint_18',
       'right_joint_11','right_joint_13','right_joint_23','right_joint_15','right_joint_17',
       'left_gripper','right_gripper']
engine=None

class Engine:
    def __init__(self):
        started=time.perf_counter()
        self.lock=threading.Lock()
        self.ready=False
        self.norm=normalize.load(BASE/'model/assets/tabletop_joint')
        self.tokenizer=tokenizer.PaligemmaTokenizer(max_len=128)
        cfg=json.loads((BASE/'model/training_config.json').read_text())['model']
        cfg.pop('pi05',None);cfg.pop('discrete_state_input',None)
        self.model=pi05_config.Pi05Config(**cfg).load(
            model_lib.restore_params(BASE/'model/params',dtype=jnp.bfloat16))
        self.sample=nnx_utils.module_jit(self.model.sample_actions)
        self.rng=jax.random.key(0)
        self.load_s=time.perf_counter()-started
        self.calls=0
        print(json.dumps({'event':'model_loaded','seconds':self.load_s,'devices':str(jax.devices())}),flush=True)

    def prepare(self,body):
        task=body.get('task')
        if not isinstance(task,str) or not task.strip() or len(task)>300:
            raise ValueError('task must be a nonempty string of at most 300 characters')
        obs=body.get('observation')
        if not isinstance(obs,dict):raise ValueError('observation is required')
        state=np.asarray(obs.get('state'),dtype=np.float32)
        if state.shape!=(12,) or not np.isfinite(state).all():raise ValueError('state must contain 12 finite numbers')
        if not 0<=state[10]<=1 or abs(float(state[11])-1)>1e-5:
            raise ValueError('left_gripper must be in [0,1]; synthetic right_gripper must equal 1')
        if obs.get('state_names',NAMES)!=NAMES:raise ValueError('state_names do not match training order')
        images={}
        for name,key in [('head','base_0_rgb'),('right_wrist','right_wrist_0_rgb')]:
            entry=obs.get('images',{}).get(name,{})
            value=entry.get('jpeg_base64')
            if not isinstance(value,str) or len(value)>8*1024*1024:raise ValueError('missing or oversized image '+name)
            raw=base64.b64decode(value,validate=True)
            with Image.open(io.BytesIO(raw)) as img:
                if img.format!='JPEG' or img.width*img.height>4096*4096:raise ValueError('invalid JPEG dimensions')
                images[key]=np.asarray(img.convert('RGB'))
        images['left_wrist_0_rgb']=np.zeros((224,224,3),dtype=np.uint8)
        inputs={'state':state,'image':images,'image_mask':{
            'base_0_rgb':np.bool_(True),'right_wrist_0_rgb':np.bool_(True),'left_wrist_0_rgb':np.bool_(False)}}
        inputs=transforms.Normalize(self.norm,use_quantiles=True)(inputs)
        inputs=transforms.ResizeImages(224,224)(inputs)
        tok,mask,ar,loss=self.tokenizer.tokenize_high_low_prompt_infer(task,'',inputs['state'])
        # Reserve space for the generated subtask; avoid silently truncating long task inputs.
        if int(mask.sum())>=128:raise ValueError('task and state exceed the 128-token prompt limit')
        inputs.update(tokenized_prompt=tok,tokenized_prompt_mask=mask,token_ar_mask=ar,token_loss_mask=loss)
        inputs=transforms.PadStatesAndActions(32)(inputs)
        batched=jax.tree.map(lambda x:jnp.asarray(x)[None,...],inputs)
        return batched,obs

    def infer(self,body):
        # Reject busy callers instead of building a queue of stale observations.
        if not self.lock.acquire(blocking=False):raise HTTPException(409,'inference busy; send a fresh observation after completion')
        try:
            t0=time.perf_counter()
            inputs,obs=self.prepare(body)
            self.rng,rng=jax.random.split(self.rng)
            t1=time.perf_counter()
            actions,tokens=self.sample(rng,model_lib.Observation.from_dict(inputs),num_steps=10)
            actions=np.asarray(actions[0]);tokens=np.asarray(tokens[0],dtype=np.int32)
            t2=time.perf_counter()
            outputs=transforms.Unnormalize(self.norm,use_quantiles=True)({'state':np.asarray(inputs['state'][0]),'actions':actions})
            actions=np.asarray(outputs['actions'][:,:12],dtype=np.float32)
            if actions.shape!=(50,12) or not np.isfinite(actions).all():raise RuntimeError('invalid model output')
            subtask=self.tokenizer.detokenize(tokens)
            self.calls+=1
            result={'request_id':body.get('request_id'),'checkpoint_step':CHECKPOINT_STEP,'actions':actions.tolist(),
                'action_shape':[50,12],'state_names':NAMES,'action_dt_s':0.02,
                'action_semantics':'absolute_joint_positions_rad_and_normalized_grippers',
                'generated_subtask':subtask.split(';')[0].rstrip('.'), 'generated_text_raw':subtask,'observation_source':obs.get('source','client_supplied'),
                'timing_ms':{'preprocess':(t1-t0)*1000,'model_synchronized':(t2-t1)*1000,
                             'server_total':(time.perf_counter()-t0)*1000},
                'right_gripper_synthetic':True,'control_ready':False,'executed':False,'rtc_enabled':False,
                'warnings':['Predictions are not motion commands; joint limits, time alignment and hardware stop remain unconnected.',
                            '50 steps at 50 Hz; selecting the next 10 steps requires observation/execution time alignment.']}
            return result
        finally:self.lock.release()

@asynccontextmanager
async def lifespan(app):
    global engine
    engine=Engine()
    sample=json.loads((BASE/'examples/recorded_request.json').read_text())
    result=engine.infer(sample)
    (BASE/'reports/cold_inference.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    engine.ready=True
    print('READY: http://127.0.0.1:8796 | inference only; no robot motion',flush=True)
    print(json.dumps({'event':'ready','cold_timing_ms':result['timing_ms']},ensure_ascii=False),flush=True)
    yield

app=FastAPI(title=f'Ke pi05 checkpoint {CHECKPOINT_STEP} inference',version='1.0',lifespan=lifespan)

@app.get('/health')
def health():
    return {'ready':bool(engine and engine.ready),'checkpoint_step':CHECKPOINT_STEP,'device':str(jax.devices()),
            'control_ready':False,'rtc_enabled':False,'calls':engine.calls if engine else 0}

@app.post('/v1/infer')
def infer(body:dict):
    if not engine or not engine.ready:raise HTTPException(503,'model not ready')
    try:return engine.infer(body)
    except HTTPException:raise
    except (ValueError,KeyError,TypeError,OSError) as e:raise HTTPException(422,str(e)) from e

@app.get('/v1/contract')
def contract():
    return {'method':'POST','path':'/v1/infer','required_fields':{
        'task':'nonempty task instruction, e.g. 抓取瓶子',
        'observation.state':'12 finite numbers in state_names order; joints rad, grippers normalized',
        'observation.images.head.jpeg_base64':'base64 JPEG',
        'observation.images.right_wrist.jpeg_base64':'base64 JPEG'},
        'optional_fields':['request_id','observation.source','observation.state_names'],
        'state_names':NAMES,'checkpoint_step':CHECKPOINT_STEP,'action_shape':[50,12],
        'action_dt_s':0.02,'flow_steps':10,'right_gripper_synthetic':True,
        'robot_execution_endpoint':None,'rtc_enabled':False,'control_ready':False,
        'errors':{'409':'busy; do not queue stale observations','422':'invalid input','503':'not ready'}}

@app.middleware('http')
async def limit_request(request:Request,call_next):
    # Loopback service, reachable from Windows through WSL localhost forwarding.
    data=bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data)>18*1024*1024:return JSONResponse({'detail':'request exceeds 18 MiB'},status_code=413)
    request._body=bytes(data)
    return await call_next(request)

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8796,workers=1)
