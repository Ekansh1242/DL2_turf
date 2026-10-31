from unittest.mock import patch, MagicMock
from datetime import datetime
import pytest
from tests.test_booking_flow import db, _run, _intent, _make_booking
from app.services import email_service
from app.services.booking_notification import notify_booking

def test_smtp_delivery_has_tls_and_pdf(monkeypatch):
    for name,value in {'SMTP_HOST':'smtp.example.com','SMTP_USER':'sender@example.com','SMTP_PASS':'test-only','SMTP_FROM':'sender@example.com'}.items():
        monkeypatch.setattr(email_service,name,value)
    with patch.object(email_service.smtplib,'SMTP') as smtp:
        assert email_service.send_booking_confirmation_email('student@example.com','Confirmed','Booked',b'%PDF-test','receipt.pdf')
        server=smtp.return_value.__enter__.return_value
        server.starttls.assert_called_once()
        server.login.assert_called_once_with('sender@example.com','test-only')
        msg=server.send_message.call_args.args[0]
        assert msg['To']=='student@example.com'
        assert next(msg.iter_attachments()).get_content_type()=='application/pdf'

def test_email_failure_does_not_undo_booking(db):
    result=_make_booking(db)
    with patch('app.services.booking_notification.build_receipt_pdf',side_effect=RuntimeError('pdf failed')):
        assert notify_booking(db,result.booking_id) is False
    from app.domain.models.models import Booking
    assert db.get(Booking,result.booking_id).status.value=='confirmed'

@pytest.mark.asyncio
async def test_ai_commit_sends_email(db):
    with patch('app.services.booking_notification.notify_booking',return_value=True) as notify:
        final=await _run(db,_intent(hour=8),datetime(2026,8,10,7,45))
    notify.assert_called_once_with(db,final['booking_id'])
    assert final['email_sent'] is True

def test_manual_commit_and_rejection_email(db):
    from app.api.v1.bookings import confirm_booking, ConfirmBookingIn
    request=ConfirmBookingIn(resource_id=db.test_resource.id,slot_start=datetime(2026,8,10,14),slot_end=datetime(2026,8,10,15))
    with patch('app.api.v1.bookings.now_local',return_value=datetime(2026,8,10,13,45)),patch('app.services.booking_notification.notify_booking',return_value=True) as notify:
        result=confirm_booking(request,db,db.test_user.id)
        assert result.success and result.email_sent
        notify.assert_called_once_with(db,result.booking_id)
        notify.reset_mock()
        assert not confirm_booking(request,db,db.test_user.id).success
        notify.assert_not_called()

def test_missing_smtp_skips(monkeypatch):
    monkeypatch.setattr(email_service,'SMTP_HOST',None)
    with patch.object(email_service.smtplib,'SMTP') as smtp:
        assert not email_service.send_plain_email('a@example.com','subject','text')
        smtp.assert_not_called()

def test_dataset_disjoint():
    from ml.train import load, gold_tags
    seen=set()
    for split in ['train','validation','test']:
        for row in load(split):
            assert row['text'] not in seen
            seen.add(row['text'])
            assert gold_tags(row)
            assert all(row['text'][e['start']:e['end']] for e in row['entities'])

def test_metrics_penalize_wrong_span():
    from ml.evaluate import measure
    row={'text':'football','intent':'book','entities':[{'label':'sport','start':0,'end':8}]}
    bad={'intent':'book','entities':[],'fields':dict.fromkeys(['sport','date','time','players'])}
    result=measure([row],[bad])
    assert result['entity_micro']['f1']==0 and result['complete_request_accuracy']==0

def test_local_normalization():
    from app.core.local_nlu import parse_booking
    fake=MagicMock()
    fake.predict.return_value={'intent':'book','fields':{'sport':'table tennis','date':'tomorrow','time':'6 pm','players':'4'}}
    with patch('app.core.local_nlu.predictor',return_value=fake):
        intent,p=parse_booking('request',datetime(2026,11,1,10))
    assert intent=='book' and p.sport=='table_tennis'
    assert p.date_iso=='2026-11-02' and p.preferred_hour==18 and p.players==4

@pytest.mark.asyncio
async def test_trained_model_in_real_booking_graph(db,monkeypatch):
    from app.agents.graph import build_ai_booking_graph
    from contextlib import ExitStack
    monkeypatch.setenv('BOOKING_NLU_BACKEND','local')
    with ExitStack() as stack:
        for node in ['booking_node','scheduling_conflict_node','commit_node']:
            stack.enter_context(patch(f'app.agents.nodes.{node}.now_local',return_value=datetime(2026,8,10,7,45)))
        notify=stack.enter_context(patch('app.services.booking_notification.notify_booking',return_value=True))
        result=await build_ai_booking_graph(db).ainvoke({'raw_text':'book football today at 8 am for 10 players','user_id':db.test_user.id,'request_id':'local-test','trace':[]})
    assert result['status']=='confirmed' and result['sport']=='football'
    assert result['players']==10 and result['email_sent']
    notify.assert_called_once_with(db,result['booking_id'])
