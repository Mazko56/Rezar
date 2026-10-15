"""Telegram WebApp authenticated API. Do not use query-string Telegram IDs for authorization."""
import os, json, time, hmac, hashlib, csv, io, re, datetime
from pathlib import Path
from urllib.parse import parse_qsl
from fastapi import FastAPI, HTTPException, Header, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from pydantic import BaseModel, Field
from . import admin_db as adb
from . import content, integrations, storage

app=FastAPI(title='REZAR Admin')
FRONT=Path(__file__).resolve().parent.parent/'miniapp'/'index.html'

SCREEN_NAMES = {
  'home':'Головна / вступ','presentation':'Мініпрезентація','pick':'Підібрати авто',
  'calc':'Розрахунок під ключ','quiz_ready':'Анкета сформована',
  'access1':'Доступи — Секретність','access2':'Доступи — Важливість',
  'access3':'Доступи — Ексклюзивність','korea1':'Корея — Вибір',
  'korea2':'Корея — Вигода','korea3':'Корея — Переваги',
  'korea4':'Чому Rezar','manager':'Зв’язок з менеджером',
  'bonus':'Доступи після заявки','auctions':'Аукціони','dealers':'Дилери'
}
SCREEN_DEFAULTS = {
  'home':content.HOME, 'pick':content.PICK_INTRO, 'calc':content.CALC_INTRO,
  'quiz_ready':content.QUIZ_READY,'access1':content.ACCESS_1,
  'access2':content.ACCESS_2,'access3':content.ACCESS_3,
  'korea1':content.KOREA_1,'korea2':content.KOREA_2,'korea3':content.KOREA_3,
  'korea4':content.KOREA_4,'manager':content.MANAGER,
  'bonus':content.BONUS_ACCESS,'auctions':content.AUCTIONS,'dealers':content.DEALERS,
  'presentation':''
}

def _valid_date(v):
    if not v:return None
    try: return datetime.date.fromisoformat(v)
    except ValueError:raise HTTPException(422,'Неправильна дата')



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
    return {'id':uid,'role':role,'bot_username':os.getenv('BOT_USERNAME','TestRezar_bot').lstrip('@')}

@app.get('/api/stats')
def stats(start:str='',end:str='',x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'stats')
    _valid_date(start);_valid_date(end)
    if start and end and start>end:raise HTTPException(422,'Дата початку більша за дату завершення')
    with adb.connection() as c:
        def val(sql,*params): return c.execute(sql,params).fetchone()[0]
        filter_sql=''
        args=[]
        if start:filter_sql+=' AND date(first_start)>=?';args.append(start)
        if end:filter_sql+=' AND date(first_start)<=?';args.append(end)
        data={
          'users':val('SELECT COUNT(*) FROM people'),
          'new_today':val('SELECT COUNT(*) FROM people WHERE date(first_start)=date("now")'),
          'new_period':val('SELECT COUNT(*) FROM people WHERE 1=1'+filter_sql,*args),
          'phones':val('SELECT COUNT(*) FROM people WHERE phone IS NOT NULL AND trim(phone)!=""'),
          'completed_quizzes':val('SELECT COUNT(*) FROM quiz_sessions WHERE completed=1'),
          'crm_sent':val('SELECT COUNT(*) FROM people WHERE crm_sent=1'),
          'crm_errors':val("SELECT COUNT(*) FROM mini_crm_issues WHERE status IN ('pending','retry_requested')"),
          'broadcasts':val('SELECT COUNT(*) FROM mini_broadcasts'),
          'events':val('SELECT COUNT(*) FROM mini_events'),
        }
    return data

@app.get('/api/users')
def users(q:str='',x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'users')
    q=q.strip()[:100]
    with adb.connection() as c:
        rows=c.execute("""SELECT telegram_id,username,first_name,first_start,last_activity,
          car,year,budget,phone,completed,source,first_source,crm_sent,crm_lead_id
          FROM people WHERE CAST(telegram_id AS TEXT) LIKE ? OR
          COALESCE(phone,'') LIKE ? OR COALESCE(username,'') LIKE ? OR
          COALESCE(first_name,'') LIKE ? ORDER BY COALESCE(last_activity,first_start) DESC LIMIT 200""",
          tuple('%'+q+'%' for _ in range(4))).fetchall()
    return [dict(r) for r in rows]

@app.get('/api/csv')
def export_csv(start:str='',end:str='',kind:str='all',x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'users')
    _valid_date(start);_valid_date(end)
    if start and end and start>end:raise HTTPException(422,'Неправильний період')
    if kind not in ('all','phones','completed','crm_sent'):raise HTTPException(422,'Invalid export type')
    terms=['1=1'];args=[]
    if start:terms.append('date(first_start)>=?');args.append(start)
    if end:terms.append('date(first_start)<=?');args.append(end)
    if kind=='phones':terms.append("phone IS NOT NULL AND trim(phone)!=''")
    elif kind=='completed':terms.append('completed=1')
    elif kind=='crm_sent':terms.append('crm_sent=1')
    cols=['telegram_id','username','first_name','first_start','last_activity','first_source','last_source',
          'phone','phone_received_at','completed','car','year','budget','crm_sent','crm_lead_id','crm_sent_at']
    with adb.connection() as c:
        rows=[dict(r) for r in c.execute('SELECT '+','.join(cols)+' FROM people WHERE '+' AND '.join(terms),args)]
    s=io.StringIO();w=csv.DictWriter(s,fieldnames=cols);w.writeheader();w.writerows(rows)
    return StreamingResponse(iter([s.getvalue().encode('utf-8-sig')]),media_type='text/csv',
        headers={'Content-Disposition':'attachment; filename="rezar-users.csv"'})

class Content(BaseModel):
    key:str=Field(pattern=r'^[a-z][a-z0-9_]{0,45}$')
    body:str=Field(max_length=4000)
    media_file_id:str=''
    buttons_json:str='[]'

@app.get('/api/content')
def content_list(x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'content')
    data={x['key']:x for x in adb.list_content()}
    result=[]
    for key,label in SCREEN_NAMES.items():
        override=data.get(key)
        result.append({'key':key,'label':label,'body':override['body'] if override else SCREEN_DEFAULTS[key],
           'media_file_id':override['media_file_id'] if override else '',
           'buttons_json':override['buttons_json'] if override else '[]',
           'customized':bool(override)})
    return result

@app.put('/api/content')
def content_save(item:Content,x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'content')
    if item.key not in SCREEN_NAMES:raise HTTPException(422,'Unknown screen')
    try:
        buttons=json.loads(item.buttons_json)
        if not isinstance(buttons,list) or len(buttons)>20:raise ValueError()
        for b in buttons:
            if not isinstance(b,dict) or not isinstance(b.get('text'),str) or len(b['text'])>64 or not isinstance(b.get('callback'),str) or not re.fullmatch(r'[a-zA-Z0-9_:\-]{1,64}',b['callback']):raise ValueError()
    except (ValueError,TypeError):raise HTTPException(422,'Buttons must be a list of {text,callback}')
    with adb.connection() as c:
        c.execute('INSERT INTO mini_content(key,body,media_file_id,buttons_json) VALUES(?,?,?,?) ON CONFLICT(key) DO UPDATE SET body=excluded.body,media_file_id=excluded.media_file_id,buttons_json=excluded.buttons_json,updated_at=CURRENT_TIMESTAMP',(item.key,item.body,item.media_file_id,item.buttons_json))
    return {'ok':True}

@app.delete('/api/content/{key}')
def content_reset(key:str,x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'content')
    if key not in SCREEN_NAMES:raise HTTPException(404,'Unknown screen')
    with adb.connection() as c:c.execute('DELETE FROM mini_content WHERE key=?',(key,))
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
    # A retry must not pretend to work until a CRM delivery worker exists.
    raise HTTPException(409,'KeyCRM worker not connected: retry unavailable')

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


@app.post('/api/media/upload')
async def media_upload(file: UploadFile=File(...),x_telegram_init_data:str=Header(default='')):
    uid=require(x_telegram_init_data,'content')
    if file.content_type not in ('image/jpeg','image/png'):
        raise HTTPException(422,'Дозволені лише JPG та PNG')
    payload=await file.read(8*1024*1024+1)
    if len(payload)>8*1024*1024:raise HTTPException(413,'Фото завелике (до 8 MB)')
    if not (payload.startswith(b'\xff\xd8') or payload.startswith(b'\x89PNG\r\n\x1a\n')):
        raise HTTPException(422,'Невірний формат фото')
    import httpx
    token=os.getenv('BOT_TOKEN','').strip()
    if not token:raise HTTPException(503,'BOT_TOKEN не налаштовано')
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            r=await client.post(f'https://api.telegram.org/bot{token}/sendPhoto',
                data={'chat_id':str(uid),'disable_notification':'true'},
                files={'photo':(file.filename or 'photo.jpg',payload,file.content_type)})
            result=r.json()
        if not result.get('ok'):
            raise HTTPException(502,'Telegram не прийняв фото. Відкрийте чат із ботом.')
        photos=result['result'].get('photo') or []
        if not photos:raise HTTPException(502,'Telegram не повернув фото')
        return {'file_id':photos[-1]['file_id']}
    except (httpx.RequestError,ValueError,KeyError) as exc:
        raise HTTPException(502,'Помилка завантаження в Telegram') from None

@app.get('/api/integrations')
def integration_list(x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'stats')
    with adb.connection() as c:
        pending=[dict(r) for r in c.execute("SELECT channel,COUNT(*) AS pending FROM mini_outbox WHERE status='pending' GROUP BY channel")]
    return {'providers':integrations.report(),'queue':pending}

@app.get('/api/events')
def event_list(x_telegram_init_data:str=Header(default='')):
    require(x_telegram_init_data,'stats')
    with adb.connection() as c:return [dict(r) for r in c.execute('SELECT id,telegram_id,event_name,source_code,created_at FROM mini_events ORDER BY id DESC LIMIT 50')]
