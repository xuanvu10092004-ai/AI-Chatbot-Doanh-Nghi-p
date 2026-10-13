from flask import render_template,jsonify
from security import require_permission,permissions
from dashboard_service import WIDGETS,widget_data


def register_dashboard(app):
    @app.get('/dashboard')
    @require_permission('dashboard:view')
    def dashboard_page():
        visible=[{'code':code,'title':title} for code,(title,codes) in WIDGETS.items() if all(c in permissions() for c in codes)]
        return render_template('dashboard.html',widgets=visible)
    for code,(_,codes) in WIDGETS.items():
        def handler(widget=code):return jsonify(rows=widget_data(widget))
        app.add_url_rule('/api/dashboard/'+code,endpoint='widget_'+code,view_func=require_permission(*codes)(handler))
