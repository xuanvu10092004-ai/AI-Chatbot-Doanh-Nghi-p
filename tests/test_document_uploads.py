from io import BytesIO
import hashlib
from pathlib import Path
import subprocess

import pytest

from app import app
from db import cursor
from document_parser import MAX_BYTES

SAMPLES = Path(__file__).resolve().parents[1] / 'data/samples/documents'


@pytest.fixture(autouse=True)
def document_storage(tmp_path):
    old = app.config.get('DOCUMENT_STORAGE')
    app.config['DOCUMENT_STORAGE'] = tmp_path
    yield tmp_path
    with cursor() as cur:
        cur.execute('SELECT id,published_doc_id FROM document_uploads WHERE title LIKE %s', ('Kiểm thử parser %',))
        rows = cur.fetchall()
        for row in rows:
            cur.execute("DELETE FROM rbac_audit_log WHERE target_type='document' AND target_id=%s", (row['id'],))
            cur.execute('DELETE FROM document_uploads WHERE id=%s', (row['id'],))
            if row['published_doc_id']:
                cur.execute('DELETE FROM kb_documents WHERE id=%s', (row['published_doc_id'],))
    if old is None:app.config.pop('DOCUMENT_STORAGE',None)
    else:app.config['DOCUMENT_STORAGE']=old


def upload(client, file='text.pdf', **fields):
    data = {'title':'Kiểm thử parser '+file, 'category_id':'1', **fields,
            'file':(BytesIO((SAMPLES/file).read_bytes()),file)}
    return client.post('/api/documents',data=data)


def counts():
    with cursor() as cur:
        cur.execute('SELECT COUNT(*) AS n FROM kb_documents');kb=cur.fetchone()['n']
        cur.execute('SELECT COUNT(*) AS n FROM document_uploads');docs=cur.fetchone()['n']
    return kb,docs


@pytest.mark.parametrize('file', ['text.pdf','table.docx','table.xlsx','large.pdf','large.xlsx'])
def test_upload_preview_and_metadata_without_publishing(auth_client,file):
    auth_client.login(1);before=counts()
    response=upload(auth_client,file)
    assert response.status_code==201
    row=response.get_json()
    assert row['status'] in {'ready','needs_review'} and row['extraction']['blocks']
    assert row['sha256']==hashlib.sha256((SAMPLES/file).read_bytes()).hexdigest() and row['size_bytes']==(SAMPLES/file).stat().st_size
    assert row['published_doc_id'] is None and row['reviewed_at'] is None
    assert counts()==(before[0],before[1]+1)
    assert auth_client.get(f"/api/documents/{row['id']}/file").data==(SAMPLES/file).read_bytes()
    assert 'stored_name' not in row and 'uploaded_by' not in row
    blocked=auth_client.post(f"/api/documents/{row['id']}/publish",json={'version':row['version']})
    assert blocked.status_code==409 and counts()[0]==before[0]


def test_scan_requires_manual_repair_and_explicit_review(auth_client):
    auth_client.login(1);before=counts()[0]
    row=upload(auth_client,'scan.pdf').get_json()
    assert row['status']=='needs_review' and row['extraction']['text']==''
    assert row['extraction']['metadata']['text_page_coverage']==0
    endpoint=f"/api/documents/{row['id']}/review"
    values={'version':row['version'],'title':row['title'],'content':'','confirmed':True,'notes':'Đã xem bản gốc.'}
    assert auth_client.put(endpoint,json=values).status_code==400
    values.update(content='Nội dung mô phỏng được nhập và đối chiếu thủ công.',notes='')
    assert auth_client.put(endpoint,json=values).status_code==400
    values.update(notes='Đã đối chiếu toàn bộ trang scan.',confirmed=False)
    assert auth_client.put(endpoint,json=values).status_code==400
    values['confirmed']=True
    reviewed=auth_client.put(endpoint,json=values)
    assert reviewed.status_code==200
    reviewed=reviewed.get_json()
    assert reviewed['reviewed_at'] and counts()[0]==before
    stale=auth_client.post(f"/api/documents/{row['id']}/publish",json={'version':row['version']})
    assert stale.status_code==409
    published=auth_client.post(f"/api/documents/{row['id']}/publish",json={'version':reviewed['version']})
    assert published.status_code==200 and published.get_json()['status']=='published'
    assert counts()[0]==before+1
    assert auth_client.post(f"/api/documents/{row['id']}/publish",json={'version':reviewed['version']}).status_code==409


@pytest.mark.parametrize('user', [None,3,5,8])
def test_upload_permission_enforced_before_parser(auth_client,monkeypatch,user):
    auth_client.login(user)
    def forbidden(*args,**kwargs):pytest.fail('Không được chạy parser nếu không có quyền')
    monkeypatch.setattr('document_service.subprocess.run',forbidden)
    before=counts();assert upload(auth_client).status_code==403
    assert auth_client.get('/api/documents').status_code==403
    assert counts()==before


def test_branch_and_category_permissions_and_rag_visibility(auth_client):
    auth_client.login(2)
    response=upload(auth_client,branch_id='2');assert response.status_code==403
    row=upload(auth_client).get_json();assert row['branch_id']==1
    reviewed=auth_client.put(f"/api/documents/{row['id']}/review",json={'version':row['version'],'title':row['title'],'content':row['extraction']['text'],'confirmed':True}).get_json()
    published=auth_client.post(f"/api/documents/{row['id']}/publish",json={'version':reviewed['version']}).get_json()
    with cursor() as cur:
        cur.execute('SELECT user_id FROM v_user_kb_access WHERE doc_id=%s',(published['published_doc_id'],))
        users={r['user_id'] for r in cur.fetchall()}
    assert 3 in users and 4 not in users
    auth_client.login(1)
    other=upload(auth_client,branch_id='2').get_json()
    auth_client.login(2)
    assert auth_client.get(f"/api/documents/{other['id']}").status_code==404
    assert auth_client.get(f"/api/documents/{other['id']}/file").status_code==404
    assert auth_client.post(f"/api/documents/{other['id']}/process").status_code==404
    assert other['id'] not in {r['id'] for r in auth_client.get('/api/documents').get_json()['rows']}
    with cursor() as cur:
        cur.execute("SELECT id,required_permission_id FROM kb_categories WHERE code='internal'");category=cur.fetchone()
        cur.execute('SELECT data_scope FROM role_permissions WHERE role_id=%s AND permission_id=%s',(2,category['required_permission_id']));grant=cur.fetchone()
        cur.execute('DELETE FROM role_permissions WHERE role_id=%s AND permission_id=%s',(2,category['required_permission_id']))
    try:
        assert upload(auth_client,category_id=str(category['id'])).status_code==403
    finally:
        if grant:
            with cursor() as cur:cur.execute('INSERT INTO role_permissions(role_id,permission_id,data_scope) VALUES(%s,%s,%s)',(2,category['required_permission_id'],grant['data_scope']))


def test_invalid_metadata_format_size_and_csrf_do_not_write(auth_client,document_storage):
    auth_client.login(1);before=counts()
    assert upload(auth_client,title='').status_code==400
    assert upload(auth_client,category_id='missing').status_code==400
    assert upload(auth_client,category_id='999999').status_code==403
    for file in ['empty.xlsx','wrong_extension.pdf','corrupt.docx']:
        assert upload(auth_client,file).status_code==400
    assert auth_client.post('/api/documents',data={'title':'Kiểm thử parser quá lớn','category_id':'1','file':(BytesIO(b'%PDF-'+b'x'*MAX_BYTES),'large.pdf')}).status_code==413
    assert auth_client.post('/api/documents',data={'title':'Kiểm thử parser cũ','category_id':'1','file':(BytesIO(b'legacy'),'file.doc')}).status_code==400
    assert auth_client.post('/api/documents',data={'title':'Kiểm thử parser CSRF','category_id':'1','file':(BytesIO((SAMPLES/'text.pdf').read_bytes()),'text.pdf')},without_csrf=True).status_code==403
    assert counts()==before and list(document_storage.iterdir())==[]


def test_corrupt_pdf_records_failure_without_writing_kb(auth_client):
    auth_client.login(1);before=counts()[0]
    row=upload(auth_client,'corrupt.pdf').get_json()
    assert row['status']=='failed' and row['error_code']=='unreadable_file'
    assert row['extraction'] is None and counts()[0]==before
    assert auth_client.get('/api/documents').get_json()['rows'][0]['id']==row['id']


def test_timeout_records_error_and_allows_retry(auth_client,monkeypatch):
    auth_client.login(1)
    with monkeypatch.context() as patch:
        def timeout(*args,**kwargs):raise subprocess.TimeoutExpired('parser',45)
        patch.setattr('document_service.subprocess.run',timeout)
        row=upload(auth_client).get_json()
    assert row['status']=='failed' and row['error_code']=='processing_timeout'
    retried=auth_client.post(f"/api/documents/{row['id']}/process")
    assert retried.status_code==200 and retried.get_json()['status']=='ready'


def test_text_review_refuses_empty_title_and_excess_content(auth_client):
    auth_client.login(1);row=upload(auth_client).get_json();before=counts()[0]
    data={'title':'','content':'Văn bản hợp lệ','confirmed':True,'version':row['version']}
    assert auth_client.put(f"/api/documents/{row['id']}/review",json=data).status_code==400
    data.update(title=row['title'],content='a'*60001)
    assert auth_client.put(f"/api/documents/{row['id']}/review",json=data).status_code==400
    assert counts()[0]==before


def test_abandoned_processing_can_be_recovered(auth_client):
    auth_client.login(1);row=upload(auth_client).get_json()
    with cursor() as cur:
        cur.execute("UPDATE document_uploads SET status='processing',processing_started_at=NOW() WHERE id=%s",(row['id'],))
    assert auth_client.post(f"/api/documents/{row['id']}/process").status_code==409
    with cursor() as cur:
        cur.execute('UPDATE document_uploads SET processing_started_at=DATE_SUB(NOW(),INTERVAL 3 MINUTE) WHERE id=%s',(row['id'],))
    response=auth_client.post(f"/api/documents/{row['id']}/process")
    assert response.status_code==200 and response.get_json()['status']=='ready'


def test_original_filename_cannot_choose_storage_path(auth_client,document_storage):
    auth_client.login(1)
    response=auth_client.post('/api/documents',data={'title':'Kiểm thử parser tên file','category_id':'1','file':(BytesIO((SAMPLES/'text.pdf').read_bytes()),'../../text.pdf')})
    assert response.status_code==201 and response.get_json()['original_name']=='text.pdf'
    assert len(list(document_storage.iterdir()))==1
    assert all(path.parent==document_storage and path.name!='text.pdf' for path in document_storage.iterdir())


def test_storage_failure_is_clear_and_does_not_write(auth_client,monkeypatch):
    auth_client.login(1);before=counts()
    def denied():raise PermissionError('private_filesystem_details')
    monkeypatch.setattr('document_service.storage_root',denied)
    response=upload(auth_client)
    assert response.status_code==503
    assert 'private_filesystem_details' not in response.get_data(as_text=True)
    assert counts()==before


def test_unresolved_formula_is_not_published_even_when_confirmed(auth_client):
    auth_client.login(1);before=counts()[0]
    row=upload(auth_client,'formula.xlsx').get_json()
    data={'title':row['title'],'content':row['extraction']['text'],'notes':'Đã xem file gốc.','confirmed':True,'version':row['version']}
    response=auth_client.put(f"/api/documents/{row['id']}/review",json=data)
    assert response.status_code==400 and 'ô thiếu' in response.get_json()['message']
    assert counts()[0]==before
