import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from app import admin_web, admin_db, storage, integrations


def init_data(user_id=5138418509):
    args={'auth_date':str(int(time.time())),'user':json.dumps({'id':user_id},separators=(',',':'))}
    data='\n'.join(f'{k}={v}' for k,v in sorted(args.items()))
    secret=hmac.new(b'WebAppData',os.environ['BOT_TOKEN'].encode(),hashlib.sha256).digest()
    args['hash']=hmac.new(secret,data.encode(),hashlib.sha256).hexdigest()
    return urlencode(args)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('BOT_DATA_DIR',str(tmp_path))
    monkeypatch.setenv('BOT_TOKEN','12345:TESTBOTTOKEN')
    monkeypatch.setenv('BOT_USERNAME','TestRezar_bot')
    return TestClient(admin_web.app)


def headers(tid=5138418509):
    return {'X-Telegram-Init-Data':init_data(tid)}


def test_root_and_security(client):
    assert client.get('/').status_code==200
    assert client.get('/api/stats').status_code==401
    assert client.get('/api/stats',headers=headers(1111)).status_code==403
    assert client.get('/api/stats',headers=headers()).status_code==200
    assert client.get('/api/me',headers=headers()).json()['bot_username']=='TestRezar_bot'


def test_stats_and_csv_on_fresh_db(client):
    data=client.get('/api/stats',headers=headers()).json()
    assert data['users']==0 and data['new_today']==0 and data['completed_quizzes']==0
    r=client.get('/api/csv?start=2026-10-01&end=2026-10-31',headers=headers())
    assert r.status_code==200
    assert 'first_start' in r.text
    assert client.get('/api/csv?start=nope',headers=headers()).status_code==422


def test_content_update_and_reset(client):
    body=client.get('/api/content',headers=headers()).json()
    assert any(x['key']=='korea2' and x['body'] for x in body)
    x={'key':'korea2','body':'Новий текст','media_file_id':'AgACtest','buttons_json':json.dumps([{'text':'Далі','callback':'korea:3'}])}
    assert client.put('/api/content',json=x,headers=headers()).status_code==200
    row=next(x for x in client.get('/api/content',headers=headers()).json() if x['key']=='korea2')
    assert row['body']=='Новий текст' and row['customized']
    assert client.delete('/api/content/korea2',headers=headers()).json()['ok']
    after=next(x for x in client.get('/api/content',headers=headers()).json() if x['key']=='korea2')
    assert after['body']!='Новий текст' and not after['customized']
    assert client.put('/api/content',json={**x,'buttons_json':'BAD'},headers=headers()).status_code==422


def test_labels_and_roles(client):
    label={'code':'audi_02','utm_campaign':'audi_ua','utm_content':'banner_02'}
    r=client.post('/api/labels',json=label,headers=headers());assert r.status_code==200
    assert r.json()['url']=='https://t.me/TestRezar_bot?start=audi_02'
    assert client.post('/api/labels',json=label,headers=headers()).status_code==409
    assert client.post('/api/admins',json={'id':98765,'role':'marketer'},headers=headers()).status_code==200
    assert client.get('/api/labels',headers=headers(98765)).status_code==200
    assert client.get('/api/users',headers=headers(98765)).status_code==403
    assert client.get('/api/integrations',headers=headers(98765)).status_code==200
    assert client.delete('/api/admins/5138418509',headers=headers()).status_code==403
    assert client.delete('/api/admins/98765',headers=headers()).status_code==200


def test_publications(client):
    assert client.post('/api/publications',json={'body':'Новини від REZAR'},headers=headers()).status_code==200
    draft=client.get('/api/publications',headers=headers()).json()[0]
    assert draft['state']=='draft'
    assert client.post(f"/api/publications/{draft['id']}/send",headers=headers()).status_code==200
    assert client.get('/api/publications',headers=headers()).json()[0]['state']=='queued'


def test_metadata_and_outbox(client):
    from types import SimpleNamespace
    u=SimpleNamespace(id=774,username='tester',first_name='Тест',language_code='uk')
    storage.record_user(u,start_param='audi_02')
    storage.record_user(u,start_param='new_99')
    p=storage.read(774)
    assert p['first_source']=='audi_02' and p['last_source']=='new_99'
    assert p['first_start'] and p['last_activity']
    admin_db.log_event(774,'bot_start','audi_02')
    admin_db.queue_outbox('keycrm','lead-1',integrations.keycrm_payload(p,'lead-1'))
    admin_db.queue_outbox('keycrm','lead-1',integrations.keycrm_payload(p,'lead-1'))
    with admin_db.connection() as c:
        assert c.execute('select count(*) from mini_outbox').fetchone()[0]==1
    assert len(client.get('/api/events',headers=headers()).json())==1
    assert client.get('/api/stats',headers=headers()).json()['users']==1
    assert client.get('/api/integrations',headers=headers()).json()['queue'][0]['pending']==1


def test_retry_not_falsely_sent(client):
    with admin_db.connection() as c:
        c.execute("insert into mini_crm_issues(lead_id,error) values('L123','timeout')")
    r=client.post('/api/issues/1/retry',headers=headers())
    assert r.status_code==409
    with admin_db.connection() as c:
        assert c.execute('select status from mini_crm_issues where id=1').fetchone()[0]=='pending'


def test_media_upload_rejects_wrong_type(client):
    bad = client.post('/api/media/upload',
        files={'file':('shell.txt',b'not a picture','text/plain')},headers=headers())
    assert bad.status_code==422
    unauthorized = client.post('/api/media/upload',
        files={'file':('photo.png',b'\x89PNG\r\n\x1a\nblah','image/png')})
    assert unauthorized.status_code==401


def test_format_payload_avoids_secrets(client):
    p={'telegram_id':777,'username':'user','phone':'+380630000000','first_source':'audi_01', 'last_source':'audi_01','start_param':'audi_01'}
    payload=integrations.keycrm_payload(p,'777:pick:1')
    assert payload['external_id']=='777:pick:1'
    assert 'API_KEY' not in payload
