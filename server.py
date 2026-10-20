import json,os,time,uuid,urllib.request,urllib.error
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
ROOT=Path(__file__).parent
PROVIDER='gemini' if os.getenv('GEMINI_API_KEY') else 'openai'
MODEL=os.getenv('GEMINI_MODEL','gemini-2.5-flash') if PROVIDER=='gemini' else os.getenv('OPENAI_MODEL','gpt-4.1-mini')
KEY=os.getenv('GEMINI_API_KEY','') if PROVIDER=='gemini' else os.getenv('OPENAI_API_KEY','')
API_URL='https://generativelanguage.googleapis.com/v1beta/openai/chat/completions' if PROVIDER=='gemini' else 'https://api.openai.com/v1/chat/completions'
RUN_COUNTS={}
MAX_RUNS_PER_IP_PER_DAY=3
CASES=[{'id':'finance','department':'Finance','request':'Automate a weekly financial variance report using approved internal read-only financial data.','risk':1,'data':'internal','write':False,'hours':6}, {'id':'hr','department':'HR','request':'Build an assistant to answer employees questions about approved HR policies without accessing employee records.','risk':1,'data':'internal','write':False,'hours':4}, {'id':'sales','department':'Sales','request':'Deploy an agent that automatically changes customer discounts in the CRM.','risk':3,'data':'confidential','write':True,'hours':12}, {'id':'ops','department':'Operations','request':'Summarize supplier delays from an approved read-only logistics dashboard.','risk':1,'data':'internal','write':False,'hours':5}, {'id':'procurement','department':'Procurement','request':'Build a contract review assistant that analyzes confidential supplier agreements.','risk':2,'data':'confidential','write':False,'hours':8}]
ROLES=[('Business Manager','You manage a department. Describe business outcome, constraints, and urgency. Do not assume approval.'),('AI Champion','You are a qualified local AI champion. Propose a limited implementation plan, permitted tools and a test plan. You cannot grant yourself authority.'),('Governance Officer','You are an independent governance officer. Challenge the plan, identify security, privacy, and compliance risks and recommend controls. You cannot override policy.'),('Enterprise Architect','You are an enterprise architect. Assess architecture, integration, duplication and production readiness.'),('Executive Sponsor','You are an executive sponsor. Recommend whether to fund, pilot, defer or reject based on benefit, risk and capacity.')]
def llm(role, instruction, context):
    payload={'model':MODEL,'messages':[{'role':'system','content':instruction+' Return concise practical analysis (max 110 words). Do not claim that a simulation is real.'},{'role':'user','content':json.dumps(context)}],'temperature':0.35,'max_tokens':200}
    req=urllib.request.Request(API_URL,data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=45) as r: response=json.load(r)
        return response['choices'][0]['message']['content'].strip()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Model provider HTTP {e.code}: '+e.read().decode()[:250])
def policy(case,model):
    if model=='mission' and case['risk']==1 and not case['write'] and case['data']=='internal':return {'decision':'DELEGATED PILOT','authority':'Qualified champion, bounded Tier 1 grant','enforced':'Read-only, approved internal data, logging, expiry, human review'}
    if case['risk']==3 or case['write']:return {'decision':'ESCALATE / NO AUTONOMOUS EXECUTION','authority':'Central governance and system owner required','enforced':'No production write access; security and business approvals required'}
    return {'decision':'CENTRAL REVIEW','authority':'Central AI and governance queue','enforced':'Data classification, review, test and audit trail'}
def simulate(case,model):
    record={'id':str(uuid.uuid4()),'case':case,'model':model,'policy':policy(case,model),'steps':[],'model_used':MODEL}
    for role,instruction in ROLES:
        context={'case':case,'operating_model':model,'binding_policy':record['policy'],'prior_agents':record['steps']}
        response=llm(role,instruction,context)
        record['steps'].append({'role':role,'response':response})
    record['note']='AI role assessments are generated. Authorization is deterministic and cannot be changed by the agents. Synthetic scenario only.'
    return record
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def sendjson(self,code,obj):
        raw=json.dumps(obj).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/api/status':return self.sendjson(200,{'connected':bool(KEY),'model':MODEL,'provider':PROVIDER,'agents':len(ROLES),'cases':CASES})
        return super().do_GET()
    def do_POST(self):
        if self.path!='/api/run':return self.sendjson(404,{'error':'Unknown endpoint'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n>10000: return self.sendjson(413,{'error':'Request too large'})
            body=json.loads(self.rfile.read(n));case=next((x for x in CASES if x['id']==body.get('case')),None);model=body.get('model')
            if not case or model not in ('mission','central'):return self.sendjson(400,{'error':'Choose a valid case and model'})
            if not KEY:return self.sendjson(503,{'error':'An AI provider API key is not configured. Real agents are unavailable.'})
            ip=self.client_address[0]
            today=time.strftime('%Y-%m-%d',time.gmtime())
            counter_key=(ip,today)
            if RUN_COUNTS.get(counter_key,0)>=MAX_RUNS_PER_IP_PER_DAY:
                return self.sendjson(429,{'error':'Daily demo limit reached for this visitor. Try again tomorrow.'})
            RUN_COUNTS[counter_key]=RUN_COUNTS.get(counter_key,0)+1
            return self.sendjson(200,simulate(case,model))
        except Exception as e:return self.sendjson(502,{'error':str(e)[:350]})
if __name__=='__main__':
    port=int(os.getenv('PORT','8000'));print(f'Agent server http://localhost:{port} | model={MODEL} | API key configured={bool(KEY)}',flush=True);ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
