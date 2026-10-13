import os
from flask import request,session,redirect,render_template,g,jsonify
from werkzeug.security import generate_password_hash
from db import cursor
from security import authenticate,safe_next,csrf_token,audit


def register_auth(app):
    @app.route('/login',methods=['GET','POST'])
    def login():
        error=None
        if request.method=='POST':
            user=authenticate(request.form.get('email',''),request.form.get('password',''))
            if user:
                destination=safe_next(request.form.get('next'))
                session.clear();session['user_id']=user['id'];csrf_token()
                if user['must_change_password']:return redirect('/change-password')
                if not destination:
                    with cursor() as cur:
                        cur.execute('SELECT r.landing_path FROM roles r JOIN user_roles ur ON ur.role_id=r.id WHERE ur.user_id=%s AND r.is_active=TRUE AND (ur.expires_at IS NULL OR ur.expires_at>NOW()) ORDER BY r.priority,r.id LIMIT 1',(user['id'],))
                        row=cur.fetchone();destination=safe_next(row['landing_path']) if row else '/chat'
                return redirect(destination or '/chat')
            error='Email hoặc mật khẩu không đúng'
        emails=[]
        if os.getenv('APP_ENV')=='dev':
            with cursor() as cur:
                cur.execute('SELECT email FROM users WHERE id BETWEEN 1 AND 9 ORDER BY id');emails=[r['email'] for r in cur.fetchall()]
        return render_template('login.html',error=error,emails=emails,next_path=safe_next(request.args.get('next')) or '',allow_guest=os.getenv('ALLOW_GUEST_CHAT','false').lower()=='true'),401 if error else 200

    @app.post('/guest')
    def guest_login():
        if os.getenv('ALLOW_GUEST_CHAT','false').lower()!='true':return jsonify(error='guest-disabled'),403
        session.clear();session['guest']=True;csrf_token();return redirect('/chat')

    @app.post('/logout')
    def logout():
        session.clear();return redirect('/login')

    @app.route('/change-password',methods=['GET','POST'])
    def change_password():
        if not g.user:return redirect('/login')
        error=None
        if request.method=='POST':
            password=request.form.get('password','')
            if len(password)<10 or password!=request.form.get('confirm'):error='Mật khẩu phải có ít nhất 10 ký tự và xác nhận trùng khớp.'
            else:
                with cursor() as cur:
                    cur.execute('UPDATE users SET password_hash=%s,password_updated_at=NOW(),must_change_password=FALSE WHERE id=%s',(generate_password_hash(password),g.user['id']))
                    audit(cur,'password_changed','user',g.user['id'],actor=g.user['id'])
                return redirect('/dashboard' if 'dashboard:view' in __import__('security').permissions() else '/chat')
        return render_template('change_password.html',error=error)
