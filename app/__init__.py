# app/__init__.py

import os
from flask import Flask
from datetime import timedelta
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

def create_app():
    """
    Flaskアプリケーションのファクトリ関数です。
    テンプレートフォルダや静的ファイルのフォルダを指定し、
    アプリケーション全体の設定やミドルウェアの登録を行います。
    """
    # 環境変数の読み込み
    load_dotenv()
    
    # Flaskインスタンスを作成。テンプレートや静的ファイルのディレクトリを指定しています。
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
                static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'),
                static_url_path='/static')

    # セッション情報を安全に扱うための秘密鍵を設定します。
    # 環境変数 "SECRET_KEY" を取得し、存在しない場合は警告用のデフォルト値を利用します。
    app.secret_key = os.environ.get('SECRET_KEY', 'default_development_key')
    
    # ProxyFixミドルウェアを適用して、プロキシ環境下でも正確なリクエスト情報が取得できるようにします。
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # セッションの有効期限を30分に設定しています。
    app.permanent_session_lifetime = timedelta(minutes=30)
    
    # ルートやその他の処理は blueprint で管理します。
    # app/routes.py内の'main'ブループリントをインポートし、アプリケーションに登録しています。
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    return app
