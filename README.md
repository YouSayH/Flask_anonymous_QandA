# 匿名Q\&Aアプリ

学科内利用を想定した、Flask製の匿名質問応答ウェブアプリケーションです。
最大の特徴は、特定のカテゴリに投稿された質問や回答に対し、設定されたキャラクター（ペルソナ）になりきったAIが自動でコメントを生成する機能です。

## ✨ 主な機能

  * **ユーザー認証**: 学籍番号とパスワードによるログイン機能
  * **匿名投稿**: 質問や回答を匿名で行うことができます
  * **カテゴリ機能**: 質問をカテゴリ別に分類・閲覧できます
  * **ベストアンサー**: 質問者は回答の中からベストアンサーを選出できます
  * **AIによる自動応答**: 特定の「Gemini」カテゴリでは、Googleの生成AIが様々なキャラクターとして質問や回答に自動でコメントします

## 🛠️ 使用技術

  * **バックエンド**: Python, Flask, Gunicorn
  * **データベース**: SQLite3
  * **フロントエンド**: HTML, CSS, JavaScript
  * **API**: Google Generative AI (Gemini)
  * **その他**: python-dotenv, Werkzeug, pytz

## 🚀 セットアップと実行方法

### 1\. 前提条件

  * Python 3
  * `venv` (Pythonの仮想環境)

### 2\. インストール手順

1.  **リポジトリをクローンします**

    ```bash
    git clone https://github.com/yousayh/flask_anonymous_qanda.git
    cd flask_anonymous_qanda
    ```

2.  **仮想環境を作成して有効化します**

    ```bash
    # Mac/Linux
    python3 -m venv venv
    source venv/bin/activate

    # Windows
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **必要なライブラリをインストールします**

    ```bash
    pip install Flask gunicorn python-dotenv Werkzeug pytz google-generativeai
    ```

    *(注: Windows環境でGunicornの代わりにWaitressを使用する場合は、`pip install waitress` も実行してください)*

4.  **環境変数を設定します**
    プロジェクトのルートディレクトリに `.env` ファイルを作成し、以下の内容を記述します。

    ```env
    # Flaskのセッション情報を暗号化するためのキー
    SECRET_KEY='あなただけのユニークで推測されにくい文字列'

    # Google AI Studioで取得したAPIキー
    GEMINI_API_KEY='あなたのGemini_API_キー'
    ```

5.  **データベースを初期化します**
    以下のコマンドでデータベースファイル (`hajimeteno.db`) とテーブルを作成します。

    ```bash
    sqlite3 hajimeteno.db < schema.sql
    ```

6.  **ログインユーザーを登録します**
    アプリケーションにはユーザー登録機能がありません。管理者が手動で `users` テーブルにログイン情報を追加する必要があります。
    *(注: `schema.sql` の `users` と `answers` テーブルのCREATE文はコメントアウトされています。利用するにはコメントを解除してデータベースを再初期化してください)*

    ```sql
    -- 例: ターミナルでsqlite3を起動してユーザーを追加
    -- sqlite3 hajimeteno.db
    -- INSERT INTO users (st_num, pass_w) VALUES ('学籍番号', 'パスワード');
    ```

### 3\. アプリケーションの実行

  * **開発環境での実行**

    ```bash
    flask run
    ```

    または

    ```bash
    python run.py
    ```

  * **本番環境での実行 (Linux/Mac)**

    ```bash
    gunicorn --bind 0.0.0.0:5000 run:app
    ```

  * **本番環境での実行 (Windows)**
    GunicornはWindowsでは使用できないため、Waitressを使用します。

    ```bash
    waitress-serve --host 0.0.0.0 --port 5000 run:app
    ```

## ☁️ デプロイ構成

このアプリケーションは、AWS EC2上でリバースプロキシとしてNginxを、ウェブサーバーとしてGunicornを配置する構成を想定して作られています。
