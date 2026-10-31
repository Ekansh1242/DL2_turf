import re
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tests.test_booking_flow import db
from app.api.v1 import auth
from app.api.v1.model_evaluation import router as evaluation_router
from app.api.v1.admin_agent import router as analytics_router
from app.core import security
from app.db.session import get_db

@pytest.fixture
def client(db,monkeypatch):
    monkeypatch.setenv('ADMIN_EMAILS', 'staff@example.com')
    app=FastAPI()
    app.include_router(auth.router)
    app.include_router(evaluation_router)
    app.include_router(analytics_router)
    app.dependency_overrides[get_db]=lambda:db
    with TestClient(app) as client:
        yield client


def issue(client,email='ekansh@rknec.edu'):
    with patch.object(auth,'is_email_configured',return_value=True),patch.object(auth,'send_plain_email',return_value=True) as send:
        response=client.post('/api/v1/auth/request-otp',json={'email':email})
    assert response.status_code==200, response.text
    code=re.search(r'\b\d{6}\b',send.call_args.args[2]).group()
    assert code not in response.text
    return code


def verify(client,code,email='ekansh@rknec.edu'):
    return client.post('/api/v1/auth/verify-otp',json={'email':email,'code':code,'name':'Student','department':'CS'})


def test_otp_single_use_and_hashed_storage(client,db):
    code=issue(client)
    row=db.get(auth.LoginChallenge,'ekansh@rknec.edu')
    assert row.digest != code and len(row.digest)==64
    response=verify(client,code)
    assert response.status_code==200
    assert response.json()['role']=='student'
    assert verify(client,code).status_code==400


def test_email_only_login_no_longer_exists(client):
    assert client.post('/api/v1/auth/login',json={'email':'sports.office@rknec.edu','name':'Admin'}).status_code==404


def test_otp_expires(client,db):
    code=issue(client)
    row=db.get(auth.LoginChallenge,'ekansh@rknec.edu')
    row.expires_at=datetime.utcnow()-timedelta(seconds=1);db.commit()
    assert verify(client,code).status_code==400


def test_wrong_otp_locks_after_five(client):
    code=issue(client)
    wrong='000000' if code!='000000' else '111111'
    for _ in range(5):assert verify(client,wrong).status_code==400
    assert verify(client,code).status_code==400


def test_resend_has_cooldown(client):
    issue(client)
    with patch.object(auth,'is_email_configured',return_value=True),patch.object(auth,'send_plain_email') as send:
        assert client.post('/api/v1/auth/request-otp',json={'email':'ekansh@rknec.edu'}).status_code==429
        send.assert_not_called()


def test_resend_invalidates_old_code(client,db):
    first=issue(client)
    row=db.get(auth.LoginChallenge,'ekansh@rknec.edu')
    row.sent_at=datetime.utcnow()-timedelta(seconds=61);db.commit()
    with patch.object(auth.secrets,'randbelow',return_value=(int(first)+1)%1000000):
        second=issue(client)
    assert verify(client,first).status_code==400
    assert verify(client,second).status_code==200


def test_smtp_failure_does_not_create_session(client):
    with patch.object(auth,'is_email_configured',return_value=True),patch.object(auth,'send_plain_email',return_value=False):
        r=client.post('/api/v1/auth/request-otp',json={'email':'ekansh@rknec.edu'})
    assert r.status_code==503 and 'access_token' not in r.json()


def test_verified_admin_and_admin_only_evaluation(client,db):
    code=issue(client,'staff@example.com')
    response=verify(client,code,'staff@example.com')
    assert response.status_code==200 and response.json()['role']=='admin'
    token=response.json()['access_token']
    headers={'Authorization':'Bearer '+token}
    report=client.get('/api/v1/admin/model/evaluation',headers=headers)
    assert report.status_code==200 and 'bilstm' in report.json()
    assert client.get('/api/v1/admin/model/dataset/train',headers=headers).status_code==200
    assert client.get('/api/v1/admin/model/dataset/not-a-split',headers=headers).status_code==422
    student=security.create_access_token(db.test_user.id)
    assert client.get('/api/v1/admin/model/evaluation',headers={'Authorization':'Bearer '+student}).status_code==403
    assert client.get('/api/v1/admin/model/evaluation').status_code==401


def test_unconfigured_external_email_rejected(client):
    assert client.post('/api/v1/auth/request-otp',json={'email':'random@gmail.com'}).status_code==403


def test_expired_token_rejected(client,db):
    now=datetime.now(timezone.utc)
    token=jwt.encode({'sub':db.test_user.id,'role':'admin','iat':now-timedelta(hours=2),'exp':now-timedelta(hours=1),'jti':'test'},security.JWT_SECRET,algorithm='HS256')
    assert client.get('/api/v1/admin/model/evaluation',headers={'Authorization':'Bearer '+token}).status_code==401


def test_claiming_admin_role_does_not_override_database(client,db):
    token=security.create_access_token(db.test_user.id,role='admin')
    assert client.get('/api/v1/admin/model/evaluation',headers={'Authorization':'Bearer '+token}).status_code==403


def test_email_request_hourly_limit(client,db):
    from app.api.v1.auth import LoginThrottle, digest
    db.add(LoginThrottle(key=digest('request-email','ekansh@rknec.edu'),started_at=datetime.utcnow(),count=10));db.commit()
    with patch.object(auth,'is_email_configured',return_value=True),patch.object(auth,'send_plain_email') as send:
        assert client.post('/api/v1/auth/request-otp',json={'email':'ekansh@rknec.edu'}).status_code==429
        send.assert_not_called()


def test_local_analytics_no_openai_call(client,db,monkeypatch):
    monkeypatch.setenv('ANALYTICS_BACKEND','local')
    monkeypatch.setenv('ADMIN_EMAILS','ekansh@rknec.edu')
    from app.domain.models.models import UserRole
    db.test_user.role=UserRole.admin;db.commit()
    token=security.create_access_token(db.test_user.id,'admin')
    with patch('app.agents.analytics_agent.get_llm_client',side_effect=AssertionError('No API call allowed')):
        r=client.post('/api/v1/admin/analytics/ask',json={'question':'Which equipment gets damaged most?'},headers={'Authorization':'Bearer '+token})
    assert r.status_code==200 and r.json()['mode']=='local_rules'
    assert r.json()['tool']=='equipment_issues'


def test_balanced_dataset():
    from collections import Counter
    from ml.train import load
    for split,n in [('train',700),('validation',150),('test',150)]:
        assert Counter(r['intent'] for r in load(split))=={'book':n,'cancel':n,'availability':n,'other':n}
