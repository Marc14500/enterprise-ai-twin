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
    payload={'model':MODEL,'messages':[{'role':'system','content':instruction+' Return concise practical analysis (max 180 words). Do not claim that a simulation is real.'},{'role':'user','content':json.dumps(context)}],'temperature':0.35,'max_tokens':350}
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


import threading,hashlib,random
from collections import defaultdict
from datetime import datetime,timezone
from urllib.parse import urlsplit
LOCK=threading.RLock()
SESSIONS={}
RUN_COUNTS=defaultdict(int)
MAX_SESSIONS_PER_IP_DAY=int(os.getenv('MAX_SESSIONS_PER_IP_DAY','3'))
MAX_STEPS=12
APP_VERSION='0.6'
ROSTER={
 'Business Manager':'Owns the business outcome and measurable requirements',
 'AI Champion':'Designs limited AI pilots under delegated authority',
 'Governance Officer':'Identifies control gaps and escalations, but cannot change binding rules',
 'Enterprise Architect':'Designs technical integration and test requirements',
 'Executive Sponsor':'Controls simulated funding and investment priorities',
 'Engineering Agent':'Executes only simulated tests when policy permits',
 'Security Officer':'Challenges data security and access scope',
 'Portfolio Manager':'Evaluates repeatable demand and potential enterprise promotion'
}
PLAYBOOK=[
 ('Business Manager','Initiate the request, quantify opportunity and address the AI Champion.'),
 ('AI Champion','Reply to the manager with a scoped proposal and ask the Governance Officer for controls.'),
 ('Governance Officer','Respond to the Champion and ask the Architect to confirm technical safeguards.'),
 ('Enterprise Architect','Respond to governance, propose concrete sandbox architecture and tests.'),
 ('Security Officer','Challenge the Architect on access and threat boundaries.'),
 ('AI Champion','Answer the concerns raised by Security and ask for binding policy authorization.'),
 ('Executive Sponsor','Respond to the Champion, discuss resources and approve or decline simulated budget subject to policy.'),
 ('Engineering Agent','Report a SIMULATED technical test if permitted, otherwise explain the policy block.'),
 ('Business Manager','Respond to the Engineering Agent; evaluate the result and request refinements.'),
 ('AI Champion','Respond to Business Manager and explain whether the prototype is ready for further validation.'),
 ('Portfolio Manager','Consider reuse across departments; recommend promotion or continued pilot with reasons.'),
 ('Executive Sponsor','Conclude with a clear decision, remaining risks and next actions.')
]
def utc_day():return datetime.now(timezone.utc).strftime('%Y-%m-%d')
def sanitized(s,n=500):return str(s or '')[:n]
def public_session(s):return {k:v for k,v in s.items() if not k.startswith('_')}
def policy_for(s):
    c=s['case'];m=s['model'];i=s['interventions']
    if i['freeze']:
        return {'decision':'STOP / AUTHORITY REVOKED','authority':'Executive emergency stop','enforced':'No further simulated execution or spending until restored','permitted':False}
    if c['risk']==3 or c['write']:
        return {'decision':'ESCALATE / NO AUTONOMOUS EXECUTION','authority':'Central governance and system owner','enforced':'Production writes prohibited; security and business approval required','permitted':False}
    if i['data_restricted']:
        return {'decision':'HOLD / DATA ACCESS RESTRICTED','authority':'Data owner and governance approval','enforced':'Data access blocked pending reclassification','permitted':False}
    if m=='mission' and c['risk']==1 and c['data']=='internal':
        return {'decision':'DELEGATED PILOT','authority':'Qualified champion; scoped Tier 1 grant','enforced':'Approved read-only data, human review, logging and expiry','permitted':True}
    return {'decision':'CENTRAL REVIEW','authority':'Central governance queue','enforced':'No autonomous pilot until central authorization','permitted':False}
def new_session(case,model,ip):
    sid=str(uuid.uuid4());seed=int(hashlib.sha256((case['id']+'|'+model).encode()).hexdigest()[:8],16)
    s={'id':sid,'company':'GlobalCo Industries','case':case,'model':model,'day':1,'turn':0,'messages':[],
       'events':[],'decisions':[],'interventions':{'freeze':False,'data_restricted':False,'budget_cap':1500},
       'state':{'status':'new request','pilot':False,'budget_committed':0,'simulated_tests':0,'simulated_hours_saved':0,'work_items':0},
       'policy':{},'seed':seed,'finished':False,'_ip':ip,'_busy':False}
    s['policy']=policy_for(s)
    with LOCK:SESSIONS[sid]=s
    return s
def record(s,kind,detail):s['events'].append({'day':s['day'],'kind':kind,'detail':detail})
def intervene(s,action,value=None):
    if action=='freeze':s['interventions']['freeze']=True
    elif action=='unfreeze':s['interventions']['freeze']=False
    elif action=='restrict_data':s['interventions']['data_restricted']=True
    elif action=='restore_data':s['interventions']['data_restricted']=False
    elif action=='budget':
        try:v=int(value)
        except (ValueError,TypeError):raise ValueError('Budget must be a whole number')
        if not 0<=v<=10000:raise ValueError('Budget must be between 0 and 10000')
        s['interventions']['budget_cap']=v
    else:raise ValueError('Unknown intervention')
    s['policy']=policy_for(s)
    if not s['policy']['permitted']:
        s['state']['pilot']=False
        s['state']['status']='blocked by policy'
    record(s,'CEO intervention',f'{action}'+(f' = {value}' if action=='budget' else ''))
def parse_agent_response(raw):
    """Recover structured Gemini replies, including double-encoded JSON."""
    import re
    candidate=raw.strip()
    for _ in range(3):
        if candidate.startswith('```'):
            candidate=re.sub(r'^```(?:json)?\\s*|\\s*```$', '', candidate).strip()
        try:
            obj=json.loads(candidate)
            if isinstance(obj,str):
                candidate=obj.strip()
                continue
            if isinstance(obj,dict):
                return obj
        except (ValueError,TypeError):
            pass
        match=re.search(r'\\{.*\\}',candidate,re.S)
        if match and match.group(0)!=candidate:
            candidate=match.group(0)
            continue
        break
    return {'to':'Enterprise Team','message':raw[:500],
            'rationale':'The agent response could not be parsed reliably.',
            'risk':'Response formatting requires review.','proposed_action':'Review'}

def readable_field(value,limit):
    if isinstance(value,(dict,list)):
        value=json.dumps(value,ensure_ascii=False)
    text=str(value or '').strip()
    # Some model replies place JSON in the message field itself.
    if text.startswith('{'):
        try:
            nested=json.loads(text)
            if isinstance(nested,dict) and 'message' in nested:
                text=str(nested['message'])
        except ValueError:
            pass
    return text[:limit]

def explain_event(s,t):
    explanations=[
      'The business identifies an opportunity. This creates demand for an AI solution.',
      'A qualified employee proposes a limited pilot instead of a full enterprise deployment.',
      'Governance challenges the proposal before any implementation is permitted.',
      'Architecture examines integration, data boundaries and duplication.',
      'Security checks the permissions and exposure the pilot would require.',
      'A binding policy decision determines whether delegated work may proceed.',
      'Funding can only be allocated within the permitted authority and CEO budget.',
      'The simulated test either proceeds under approved controls or is blocked.',
      'The business evaluates the synthetic result rather than accepting a technical success alone.',
      'The champion identifies what must be validated before real deployment.',
      'Portfolio review considers whether the same solution might be useful elsewhere.',
      'Leadership closes the request with a decision and unresolved risks.'
    ]
    outcome='Blocked by binding policy.' if t in (5,7) and not s['policy']['permitted'] else ''
    return explanations[t]+' '+outcome

def perform_step(s):
    t=s['turn']
    if t>=len(PLAYBOOK):s['finished']=True;return
    role,task=PLAYBOOK[t]
    # The policy engine, not model output, controls all simulated state transitions.
    s['policy']=policy_for(s)
    p=s['policy']
    if t==5:
        s['decisions'].append({'day':s['day'],**p})
        s['state']['pilot']=p['permitted']
        s['state']['status']='delegated pilot authorized' if p['permitted'] else 'waiting for governance approval'
        record(s,'Policy gate',p['decision'])
    if t==6:
        amount=min(600,s['interventions']['budget_cap']) if p['permitted'] else 0
        s['state']['budget_committed']=amount
        record(s,'Budget',f'Synthetic pilot allocation ${amount}')
    if t==7:
        if p['permitted'] and s['state']['budget_committed']>0:
            # deterministic illustrative outputs, not measurements
            s['state']['simulated_tests']=3
            s['state']['simulated_hours_saved']=round(s['case']['hours']*0.6,1)
            s['state']['status']='synthetic tests complete'
            record(s,'Simulated test','3 illustrative test checks; not empirical validation')
        else:
            s['state']['status']='execution blocked'
            record(s,'Execution blocked',p['decision'])
    if t==10 and p['permitted']:
        s['state']['work_items']=1
        record(s,'Portfolio review','Potential reuse identified for evaluation, not promoted automatically')
    if t==11:s['state']['status']='completed with pilot' if s['state']['simulated_tests'] else 'completed without execution'
    context={'synthetic_company':s['company'],'business_request':s['case'],'operating_model':s['model'],
             'your_role':role,'role_mandate':ROSTER[role],'task':task,'binding_policy':p,
             'interventions':s['interventions'],'enterprise_state':s['state'],
             'previous_agent_messages':s['messages'][-4:],'simulated_day':s['day'],
             'instruction':'Respond to a specific preceding agent. Do not pretend synthetic tests are real measurements.'}
    prompt=('You are an AI role agent in a synthetic enterprise digital twin. Generate a meaningful, concrete workplace message that responds to a named previous role when possible. '
            'Be substantive and realistic. You can recommend actions but cannot override the binding policy or claim external actions were performed. '
            'For tests, clearly label outcomes illustrative. Respond with ONLY a valid JSON object, no markdown fences, with these exact keys: '
            '"to" (recipient role), "message" (3-5 concise sentences, max 500 characters), '
            '"rationale" (1-2 sentence public decision justification citing specific assumptions/evidence, NOT hidden reasoning), '
            '"risk" (specific risk or uncertainty), "proposed_action" (short). '
            'Do not expose private chain-of-thought. If blocked by policy, explicitly say so.')
    raw=llm(role,prompt,context)
    item=parse_agent_response(raw)
    msg={'day':s['day'],'from':role,'to':readable_field(item.get('to','Enterprise Team'),70),
         'message':readable_field(item.get('message'),650),
         'rationale':readable_field(item.get('rationale'),400),
         'risk':readable_field(item.get('risk'),300),
         'proposed_action':readable_field(item.get('proposed_action'),100),
         'narration':explain_event(s,t)}
    s['messages'].append(msg);s['turn']+=1
    if t in (2,5,7,10):s['day']+=1
    if s['turn']>=len(PLAYBOOK):s['finished']=True
    return s
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def sendjson(self,code,obj):
        data=json.dumps(obj).encode();self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if urlsplit(self.path).path=='/api/status':
            return self.sendjson(200,{'connected':bool(KEY),'model':MODEL,'provider':PROVIDER,
              'cases':CASES,'max_sessions_per_day':MAX_SESSIONS_PER_IP_DAY,'version':APP_VERSION})
        return super().do_GET()
    def do_POST(self):
        path=urlsplit(self.path).path
        if path not in ('/api/session','/api/step','/api/intervene'):return self.sendjson(404,{'error':'Unknown endpoint'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=5000:return self.sendjson(400,{'error':'Invalid request size'})
            body=json.loads(self.rfile.read(n))
            if not KEY:return self.sendjson(503,{'error':'Gemini API key missing on Render'})
            ip=self.client_address[0]
            # Optional access passcode protects API quota for public services.
            access=os.getenv('SIM_ACCESS_CODE','')
            if access and body.get('access_code')!=access:return self.sendjson(403,{'error':'Incorrect simulation access code'})
            if path=='/api/session':
                case=next((c for c in CASES if c['id']==body.get('case')),None)
                model=body.get('model')
                if not case or model not in ('mission','central'):return self.sendjson(400,{'error':'Invalid scenario or model'})
                with LOCK:
                    key=(ip,utc_day())
                    if RUN_COUNTS[key]>=MAX_SESSIONS_PER_IP_DAY:return self.sendjson(429,{'error':'Daily simulation limit reached for this connection'})
                    RUN_COUNTS[key]+=1
                    if len(SESSIONS)>=120:SESSIONS.pop(next(iter(SESSIONS)))
                    s=new_session(case,model,ip)
                return self.sendjson(200,public_session(s))
            sid=body.get('id')
            with LOCK:
                s=SESSIONS.get(sid)
                if not s:return self.sendjson(404,{'error':'Simulation expired; start again'})
                if s['_ip']!=ip:return self.sendjson(403,{'error':'Simulation session belongs to a different connection'})
                if s['_busy']:return self.sendjson(409,{'error':'Agent already running'})
                s['_busy']=True
            try:
                if path=='/api/intervene':intervene(s,body.get('action'),body.get('value'))
                else:perform_step(s)
                return self.sendjson(200,public_session(s))
            finally:
                with LOCK:s['_busy']=False
        except ValueError as e:return self.sendjson(400,{'error':str(e)[:200]})
        except Exception as e:
            print('API error',type(e).__name__,str(e)[:250],flush=True)
            return self.sendjson(502,{'error':str(e)[:250]})
if __name__=='__main__':
    port=int(os.getenv('PORT','8000'))
    print('Enterprise Twin v0.6 on',port,flush=True)
    ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
