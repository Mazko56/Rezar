"""Connector contracts and readiness. No external API delivery is claimed here.

Pending entries remain in mini_outbox until vendor-approved API adapters are
configured and tested; marking them delivered without a response is forbidden.
"""
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Integration:
    code: str
    name: str
    env: tuple[str,...]
    note: str

CONNECTORS = (
    Integration('postgres', 'PostgreSQL', ('DATABASE_URL',), 'Потрібна міграція даних із SQLite'),
    Integration('keycrm', 'KeyCRM', ('KEYCRM_API_TOKEN', 'KEYCRM_API_URL'), 'Очікує погодження полів заявок та API-відправки'),
    Integration('graspil', 'Graspil', ('GRASPIL_API_KEY', 'GRASPIL_ENDPOINT'), 'Очікує документацію подій та API'),
    Integration('backup', 'Резервні копії R2 / S3', ('S3_ENDPOINT', 'S3_BUCKET', 'S3_ACCESS_KEY_ID', 'S3_SECRET_ACCESS_KEY'), 'Потрібне налаштування щоденного backup і тест відновлення'),
)

def report():
    result=[]
    for c in CONNECTORS:
        ready=all(bool(os.getenv(k, '').strip()) for k in c.env)
        result.append({'code':c.code,'name':c.name,'configured':ready,
            'missing':[k for k in c.env if not os.getenv(k,'').strip()],
            'status':'awaiting_implementation' if ready else 'awaiting_credentials',
            'note':c.note})
    return result


def keycrm_payload(person, lead_key):
    return {'external_id':lead_key,'phone':person.get('phone'),
        'telegram_id':person['telegram_id'],'username':person.get('username'),
        'first_name':person.get('first_name'),'first_source':person.get('first_source'),
        'last_source':person.get('last_source'),'utm_code':person.get('start_param')}


def graspil_event(event_name, person, details=None):
    return {'name':event_name,'telegram_id':person['telegram_id'],
        'start_code':person.get('start_param'),'details':details or {}}
