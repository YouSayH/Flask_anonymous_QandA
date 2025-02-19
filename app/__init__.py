# app/__init__.py
import os
from flask import Flask
from datetime import timedelta
from werkzeug.middleware.proxy_fix import ProxyFix

def create_app():
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    # セッション情報の保護用の秘密鍵（本番環境では環境変数から読み込む等の対策を）
    app.secret_key = 'your_secret_key_here'
    
    # セッションの有効期限を30分に設定
    app.permanent_session_lifetime = timedelta(minutes=30)
    
    # ルートやその他の処理は blueprint で管理
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    return app
