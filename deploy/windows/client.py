"""Submit a task and observation to the inference API; never executes actions."""
import argparse,json,time,urllib.request,urllib.error,sys
from pathlib import Path
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',default='http://127.0.0.1:8796')
    p.add_argument('--task',help='Task instruction, e.g. 抓取瓶子')
    src=p.add_mutually_exclusive_group(required=True)
    src.add_argument('--request',type=Path,help='Existing request JSON, including recorded_request.json')
    src.add_argument('--observation-url',help='Robot observation endpoint, normally http://127.0.0.1:8795/v1/observation')
    p.add_argument('--output',type=Path,default=Path('inference_result.json'))
    a=p.parse_args()
    if a.request:body=json.loads(a.request.read_text(encoding='utf-8-sig'))
    else:
        with urllib.request.urlopen(a.observation_url,timeout=5) as r:obs=json.load(r)
        obs['source']='robot_observation_api'
        body={'observation':obs}
    if a.task:body['task']=a.task
    if not body.get('task'):p.error('--task is required when the input has no task')
    body['request_id']='client-'+str(time.time_ns())
    req=urllib.request.Request(a.url.rstrip('/')+'/v1/infer',data=json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'},method='POST')
    started=time.perf_counter()
    try:
        with urllib.request.urlopen(req,timeout=120) as r:result=json.load(r)
    except urllib.error.HTTPError as e:raise SystemExit(f'HTTP {e.code}: {e.read().decode()}')
    result['client_roundtrip_ms']=(time.perf_counter()-started)*1000
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('action_shape','generated_subtask','timing_ms','client_roundtrip_ms','executed')},ensure_ascii=False,indent=2))
    print('Saved:',a.output.resolve())

if __name__=='__main__':main()
