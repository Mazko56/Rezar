"""Telegram WebApp authenticated API. Do not use query-string Telegram IDs for authorization."""
import os, json, time, hmac, hashlib, csv, io, re
from pathlib import Path
from urllib.parse import parse_qsl
from fastapi import FastAPI, HTTPException, Header, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from pydantic import BaseModel, Field
from . import admin_db as adb
from . import content

app=FastAPI(title='REZAR Admin')
FRONT=Path(__file__).resolve().parent.parent/'miniapp'/'index.html'


def valid_user(data):
    if not data: raise HTTPException(401,'Open from Telegram')
    fields=dict(parse_qsl(data,keep_blank_values=True))
    hashval=fields.pop('hash',None)
    if not hashval:raise HTTPException(401,'Missing signature')
    try: issued=int(fields.get('auth_date','0'))
    except ValueError:raise HTTPException(401,'Invalid timestamp')
    if abs(time.time()-issued)>3600:raise HTTPException(401,'Expired Telegram authorization')
    token=os.getenv('BOT_TOKEN','')
    if not token:raise HTTPException(503,'Bot token not configured')
    check='\n'.join(f'{k}={v}' for k,v in sorted(fields.items()))
    secret=hmac.new(b'WebAppData',token.encode(),hashlib.sha256).digest()
    digest=hmac.new(secret,check.encode(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest,hashval):raise HTTPException(401,'Invalid Telegram signature')
    try: tid=int(json.loads(fields['user'])['id'])
    except (KeyError,ValueError,TypeError):raise HTTPException(401,'Missing Telegram user')
    return tid

def require(init_data,permission='stats'):
    uid=valid_user(init_data)
    if not adb.can(uid,permission):raise HTTPException(403,'No permission')
    return uid

@app.get('/',response_class=HTMLResponse)
def index():return FRONT.read_text(encoding='utf8')

@app.get('/api/me')
def me(x_telegram_init_data:str=Header(default='')):
    uid=valid_user(x_telegram_init_data)
    role=adb.role(uid)
    if not role: raise HTTPException(403)
    return {'id':uid,'role':role}

@app.get('/api/stats')
def stats(x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'stats')
    with adb.connection() as c:
        totals={}
        for k,q in {'users':'SELECT COUNT(*) FROM people','phones':'SELECT COUNT(*) FROM people WHERE phone IS NOT NULL AND phone != ""','completed_quizzes':'SELECT COUNT(*) FROM quiz_sessions WHERE completed=1','crm_errors':'SELECT COUNT(*) FROM mini_crm_issues WHERE status="pending"','broadcasts':'SELECT COUNT(*) FROM mini_broadcasts'}.items():
            try:totals[k]=c.execute(q).fetchone()[0]
            except Exception:totals[k]=0
    return totals

@app.get('/api/users')
def users(q:str='',x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'users')
    with adb.connection() as c:
        rows=c.execute('SELECT telegram_id,car,year,budget,phone,completed,source,view FROM people WHERE CAST(telegram_id AS TEXT) LIKE ? OR COALESCE(phone, "") LIKE ? ORDER BY telegram_id DESC LIMIT 200',('%'+q+'%','%'+q+'%')).fetchall()
    return [dict(r) for r in rows]

@app.get('/api/csv')
def export_csv(start:str='',end:str='',kind:str='all',x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'users')
    # Legacy DB has no creation timestamp, so cannot honestly apply a date filter yet.
    if start or end:raise HTTPException(422,'Date filtering requires user creation timestamps in PostgreSQL')
    q='SELECT telegram_id,car,year,budget,phone,completed,source FROM people'
    if kind=='phones':q+=' WHERE phone IS NOT NULL AND phone != ""'
    elif kind=='completed':q+=' WHERE completed=1'
    elif kind!='all':raise HTTPException(400,'Invalid export type')
    with adb.connection() as c: rows=[dict(x) for x in c.execute(q)]
    s=io.StringIO(); w=csv.DictWriter(s,fieldnames=['telegram_id','car','year','budget','phone','completed','source']);w.writeheader();w.writerows(rows)
    return StreamingResponse(iter([s.getvalue().encode('utf-8-sig')]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="rezar-export.csv"'})

class Content(BaseModel):
    key:str=Field(pattern=r'^[a-z][a-z0-9_]{0,45}$')
    body:str=Field(max_length=4000)
    media_file_id:str=''
    buttons_json:str='[]'

@app.get('/api/content')
def content_list(x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'content')
    data={x['key']:x for x in adb.list_content()}
    default_keys=('home','pick','calc','manager','access1','access2','access3','korea1','korea2','korea3','korea4','bonus','auctions','dealers','quiz_ready')
    for key in default_keys:
        data.setdefault(key,{'key':key,'body':'','media_file_id':'','buttons_json':'[]'})
    return list(data.values())

@app.put('/api/content')
def content_save(item:Content,x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'content')
    try:
        buttons=json.loads(item.buttons_json)
        if not isinstance(buttons,list) or len(buttons)>20:raise ValueError()
        for b in buttons:
            if not isinstance(b,dict) or not isinstance(b.get('text'),str) or len(b['text'])>64 or not isinstance(b.get('callback'),str) or not re.fullmatch(r'[a-zA-Z0-9_:\-]{1,64}',b['callback']):raise ValueError()
    except (ValueError,TypeError):raise HTTPException(422,'Buttons must be a list of {text,callback}')
    with adb.connection() as c:
        c.execute('INSERT INTO mini_content(key,body,media_file_id,buttons_json) VALUES(?,?,?,?) ON CONFLICT(key) DO UPDATE SET body=excluded.body,media_file_id=excluded.media_file_id,buttons_json=excluded.buttons_json,updated_at=CURRENT_TIMESTAMP',(item.key,item.body,item.media_file_id,item.buttons_json))
    return {'ok':True}

class Label(BaseModel):
    code:str=Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    utm_source:str='telegram'
    utm_medium:str='paid'
    utm_campaign:str=''
    utm_content:str=''
    utm_term:str=''

@app.get('/api/labels')
def labels(x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'labels')
    with adb.connection() as c:return [dict(r) for r in c.execute('SELECT * FROM mini_labels ORDER BY created_at DESC')]

@app.post('/api/labels')
def add_label(item:Label,x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'labels')
    with adb.connection() as c:
        try:c.execute('INSERT INTO mini_labels(code,utm_source,utm_medium,utm_campaign,utm_content,utm_term) VALUES(?,?,?,?,?,?)',tuple(getattr(item,x) for x in ['code','utm_source','utm_medium','utm_campaign','utm_content','utm_term']))
        except Exception:raise HTTPException(409,'Code already exists')
    botname=os.getenv('BOT_USERNAME','TestRezar_bot').lstrip('@')
    return {'url':f'https://t.me/{botname}?start={item.code}'}

@app.get('/api/admins')
def admins(x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'admins')
    with adb.connection() as c:return [dict(x) for x in c.execute('SELECT id,role,created_at FROM mini_admins ORDER BY id')]

class Admin(BaseModel):
    id:int=Field(gt=0)
    role:str=Field(pattern=r'^(admin|marketer)$')

@app.post('/api/admins')
def add_admin(item:Admin,x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'admins')
    with adb.connection() as c:c.execute('INSERT INTO mini_admins(id,role) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET role=excluded.role WHERE mini_admins.role != "owner"',(item.id,item.role))
    return {'ok':True}

@app.delete('/api/admins/{tid}')
def remove_admin(tid:int,x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'admins')
    if tid==adb.ROOT_ID:raise HTTPException(403,'Owner cannot be removed')
    with adb.connection() as c:c.execute('DELETE FROM mini_admins WHERE id=? AND role != "owner"',(tid,))
    return {'ok':True}

@app.get('/api/issues')
def issues(x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'users')
    with adb.connection() as c:return [dict(x) for x in c.execute('SELECT * FROM mini_crm_issues ORDER BY id DESC LIMIT 100')]

@app.post('/api/issues/{issue_id}/retry')
def retry_issue(issue_id:int,x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'users')
    # Do not mark as sent; actual CRM worker needs to consume the retry request.
    with adb.connection() as c:
        c.execute('UPDATE mini_crm_issues SET status="retry_requested",updated_at=CURRENT_TIMESTAMP WHERE id=?',(issue_id,))
    return {'ok':True,'note':'Requires connected KeyCRM worker'}

class Publication(BaseModel):
    body:str=Field(max_length=4000)
    media_file_id:str=''

@app.post('/api/publications')
def publish(item:Publication,x_telegram_init_data:str=Header(default='')):
    uid=require(x_telegram_init_data,'publications')
    with adb.connection() as c:
        cur=c.execute('INSERT INTO mini_broadcasts(body,media_file_id,created_by,state) VALUES(?,?,?,"draft")',(item.body,item.media_file_id,uid))
        return {'id':cur.lastrowid,'state':'draft','note':'Review and send using /api/publications/{id}/send'}

@app.get('/api/publications')
def publications(x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'publications')
    with adb.connection() as c:return [dict(x) for x in c.execute('SELECT * FROM mini_broadcasts ORDER BY id DESC LIMIT 100')]

@app.post('/api/publications/{pub_id}/send')
def queue_publication(pub_id:int,x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'publications')
    with adb.connection() as c:
        pub=c.execute('SELECT state FROM mini_broadcasts WHERE id=?',(pub_id,)).fetchone()
        if not pub or pub['state']!='draft':raise HTTPException(409,'Publication not a draft')
        c.execute('INSERT OR IGNORE INTO mini_delivery(broadcast_id,recipient) SELECT ?,telegram_id FROM people',(pub_id,))
        c.execute('UPDATE mini_broadcasts SET state="queued" WHERE id=?',(pub_id,))
    return {'ok':True}
