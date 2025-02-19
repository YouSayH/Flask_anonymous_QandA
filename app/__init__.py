# app/__init__.py
import os
from flask import Flask
from datetime import timedelta
from werkzeug.middleware.proxy_fix import ProxyFix

def create_app():
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
                static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'),
                static_url_path='/static')

    # セッション情報の保護用の秘密鍵　環境変数 "SECRET_KEY" を読み込み（存在しない場合は警告用のデフォルト値）
    app.secret_key = os.environ.get('SECRET_KEY', 'default_development_key')
    
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # セッションの有効期限を30分に設定
    app.permanent_session_lifetime = timedelta(minutes=30)
    
    # ルートやその他の処理は blueprint で管理
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    return app
