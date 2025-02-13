from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3 as sql
from functools import wraps
from datetime import datetime, timedelta
import pytz  # タイムゾーン処理用のライブラリを追加

# Flaskアプリケーションのインスタンスを生成します。
app = Flask(__name__)

# セッション情報の暗号化と改竄防止のための秘密鍵を設定します。
# ※本番環境では、秘密鍵はソースコードに直接書かず、環境変数などから読み込む方法にしてください。
app.secret_key = 'your_secret_key_here'  

def get_db_connection():
    """
    SQLite3データベース 'hajimeteno.db' への接続を確立する関数です。
    
    - データベースから取得したレコードを辞書形式で扱えるようにするため、row_factoryを設定しています。
    - これにより、クエリ結果の各カラムに対してカラム名をキーとしてアクセスできるようになります。
    - また、SQLite3データベース接続を確立し、日本時間でのタイムスタンプを使用するように設定します。

    """
    con = sql.connect('hajimeteno.db')
    con.row_factory = sql.Row
    
    # データベースで日本時間を使用するように設定
    con.execute("PRAGMA timezone = '+09:00'")
    
    # 現在時刻を取得する関数を定義
    def get_jst_datetime():
        return datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')
    
    # SQLiteに関数を登録
    con.create_function('CURRENT_TIMESTAMP', 0, get_jst_datetime)
    
    return con

def login_required(f):
    """
    ログイン必須のデコレータです。
    
    このデコレータを関数に適用することで、その関数を呼び出す前にユーザーがログインしているかを確認します。
    もしログインしていなければ、ログインページへリダイレクトし、エラーメッセージを表示します。
    
    @wraps(f) を用いることで、デコレートされた関数のメタ情報（関数名やドキュメント文字列など）が失われないようにしています。
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
         # セッション（ユーザーごとに保持される情報）に 'user_id' キーが存在するかどうかでログイン状態を判断
         if 'user_id' not in session:
             flash('ログインが必要です。')  # ログインが必要な旨のメッセージを表示
             return redirect(url_for('login'))  # ログインページへリダイレクト
         # ログイン済みの場合、元の関数をそのまま実行する
         return f(*args, **kwargs)
    return decorated_function

# ================================================================================================
# ログイン関連のルート
# ================================================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    ログインページのルートです。
    
    - GETリクエストの場合: ログインフォーム (login.html) を表示します。
    - POSTリクエストの場合: ユーザーが入力した学籍番号を用いて認証を行い、認証成功ならセッションに情報を保存しトップページへリダイレクト、
      認証失敗の場合はエラーメッセージを表示して再度ログインページへリダイレクトします。
    """
    if request.method == 'POST':
         # フォームから送信された 'student_number' の値を取得し、前後の不要な空白を削除する
         student_number = request.form['student_number'].strip()
         passphrase = request.form['passphrase'].strip()
         
         # データベース接続を確立してユーザー情報を取得する
         con = get_db_connection()
         # SQLインジェクション対策のため、プレースホルダー（?）を利用して学籍番号をクエリに埋め込む
         user = con.execute("SELECT * FROM users WHERE student_number = ?", (student_number,)).fetchone()
         con.close()  # 接続を閉じる

         if user and user['passphrase'] == passphrase:
             # ユーザー情報が取得できた場合、セッションにユーザーIDと学籍番号を保存し、ログイン状態とする
             session['user_id'] = user['id']
             session['student_number'] = user['student_number']
             session.permanent = True  
             app.permanent_session_lifetime = timedelta(minutes=30)  # セッションの有効期限を30分に設定
             
             flash('ログイン成功しました。')
             return redirect(url_for('index'))  # ログイン成功後はトップページへリダイレクト
         else:
             # ユーザーが存在しなかった場合、エラーメッセージを表示し、再度ログインページへリダイレクト
             flash('学籍番号または合言葉が正しくありません。')
             return redirect(url_for('login'))
    # GETリクエストの場合は、login.htmlテンプレートをレンダリングしてログインフォームを表示
    return render_template('login.html')

@app.route('/logout')
@login_required  # ログアウト処理にもログイン必須のチェックを入れる
def logout():
    """
    ログアウト処理のルートです。
    
    セッション情報をすべてクリアし、ログアウト状態にした後、ログインページへリダイレクトします。
    """
    session.clear()  # セッション内の全情報を削除
    flash('ログアウトしました。')
    return redirect(url_for('login'))

# ================================================================================================
# 質問・回答機能のルート
# ================================================================================================

@app.route('/')
@login_required
def index():
    """
    トップページ（質問一覧）のルートです。
    
    データベースから全ての質問を取得し、新しい順（作成日時の降順）に表示します。
    """
    con = get_db_connection()
    # 質問ID、質問内容、作成日時を取得し、作成日時の新しい順にソート
    cur = con.execute("SELECT id, question_content, created_at FROM questions ORDER BY created_at DESC")
    questions = cur.fetchall()  # すべての質問レコードをリストとして取得
    con.close()
    # index.htmlテンプレートに質問一覧を渡してレンダリング
    return render_template("index.html", questions=questions)

@app.route('/question/<int:question_id>')
@login_required
def question_detail(question_id):
    """
    質問詳細ページのルートです。
    
    指定された質問IDに対応する質問内容と、その質問に対する全ての回答を取得して表示します。
    """
    con = get_db_connection()
    # 質問IDに対応する質問内容を取得
    question = con.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    # 同じ質問IDに紐づく回答を、作成日時の新しい順に取得
    answers = con.execute("SELECT * FROM answers WHERE question_id = ? ORDER BY created_at DESC", (question_id,)).fetchall()
    con.close()
    # question.htmlテンプレートに質問と回答のデータを渡してレンダリング
    return render_template("question.html", question=question, answers=answers)

@app.route('/ask', methods=['POST'])
@login_required
def ask():
    """
    質問投稿処理のルートです。
    
    フォームから送信された質問内容をデータベースに保存し、保存後はトップページへリダイレクトします。
    """
    # フォームから 'question' という名前のデータを取得
    question_content = request.form['question']
    if question_content:
        # 質問内容が空でなければ、データベースに接続して質問を登録する
        con = get_db_connection()
        # INSERTクエリにより、質問内容、現在のタイムスタンプ（CURRENT_TIMESTAMP）、および投稿者のユーザーIDを保存
        con.execute("INSERT INTO questions (question_content, date, user_id) VALUES (?, CURRENT_TIMESTAMP, ?)", 
                    (question_content, session['user_id']))
        con.commit()  # データベースに変更を確定する
        con.close()
    # 投稿後、トップページ（質問一覧）へリダイレクト
    return redirect(url_for('index'))

@app.route('/answer/<int:question_id>', methods=['POST'])
@login_required
def answer(question_id):
    """
    回答投稿処理のルートです。
    
    指定された質問IDに対して、フォームから送信された回答内容をデータベースに保存し、
    投稿後は該当する質問の詳細ページへリダイレクトします。
    """
    # フォームから 'answer' という名前のデータを取得
    answer_content = request.form['answer']
    if answer_content:
        # 回答内容が空でなければ、データベースに接続して回答を登録する
        con = get_db_connection()
        # INSERTクエリにより、対象の質問ID、回答内容、回答者のユーザーIDを保存
        con.execute("INSERT INTO answers (question_id, answer_content, user_id) VALUES (?, ?, ?)", 
                    (question_id, answer_content, session['user_id']))
        con.commit()  # 変更を確定する
        con.close()
    # 回答投稿後、元の質問詳細ページへリダイレクトして、最新の情報を表示する
    return redirect(url_for('question_detail', question_id=question_id))

# ================================================================================================
# アプリケーションの起動
# ================================================================================================

if __name__ == '__main__':
    """
    このスクリプトが直接実行された場合にFlaskの開発用サーバを起動します。
    
    debug=True とすることで、コードの変更時に自動リロードされ、エラー発生時に詳細なデバッグ情報が表示されます。
    ※開発中のみ利用し、本番環境では必ず適切な設定に変更してください。
    """
    app.run(debug=True)
