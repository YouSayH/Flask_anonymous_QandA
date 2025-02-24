# app/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3 as sql
from functools import wraps 
from datetime import datetime
import pytz

# 質問に用いる固定のカテゴリー一覧です。（「すべて」は含めず、後で全件表示として扱います）
CATEGORIES = [
    '基本情報技術者試験', 'ITパスポート', 'セキュリティ教科', 'ディジタル情報', 
    '坂上先生教科', 'コンピュータ基礎', '情報システム(要件定義)', 'データサイエンスとAI',
    'マネジメントと戦略', 'データベース', 'ネットワーク基礎', 'データ構造とアルゴリズム',
    'プログラミング演習Python', 'プログラミング演習C言語', 'プログラミング演習Java',
    'Webアプリ', '画像制作', '動画制作', 'AR・VR', '半導体とアプリケーション',
    'ホームページ制作', 'PCスキルアップ', 'プレゼン', '地域経済', '情報総合実習', 'その他'
]

# Flaskのブループリントを作成し、ルーティングをグループ化しています。
main = Blueprint('main', __name__)

def get_db_connection():
    """
    SQLite3データベース 'hajimeteno.db' への接続を確立します。
    ・クエリ結果を辞書形式で扱えるように設定
    ・日本標準時（JST）を返す CURRENT_TIMESTAMP 関数を登録
    """
    # データベースファイルに接続
    con = sql.connect('hajimeteno.db')
    # 結果を辞書形式（キーでアクセスできる）にするための設定
    con.row_factory = sql.Row
    # タイムゾーンを日本標準時に設定（SQLiteのPRAGMA timezoneは参考情報）
    con.execute("PRAGMA timezone = '+09:00'")
    
    def get_jst_datetime():
        """
        現在の日本標準時を 'YYYY-MM-DD HH:MM:SS' 形式の文字列で返します。
        """
        return datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')
    
    # CURRENT_TIMESTAMP 関数を上書きし、日本時刻を返すように設定
    con.create_function('CURRENT_TIMESTAMP', 0, get_jst_datetime)
    return con

def login_required(f):
    """
    ログイン状態をチェックするためのデコレータです。
    ・セッションに 'user_id' がなければログイン画面へリダイレクトします。
    ・ログイン済みの場合、元の関数を実行します。
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('ログインが必要です。')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

# --------------- ログイン関連のルート ---------------

@main.route('/login', methods=['GET', 'POST'])
def login():
    """
    ログインページの表示と認証処理を行います。
    ・GETリクエストの場合はログインページ（login.html）を表示。
    ・POSTリクエストの場合は、フォームから送信された学籍番号とパスワードをチェックし、
      正しければセッションにユーザー情報を保存します。
    """
    if request.method == 'POST':
        # フォームから学籍番号とパスワードを取得（前後の空白を削除）
        st_num = request.form['st_num'].strip()
        pass_w = request.form['pass_w'].strip()
        
        # データベース接続してユーザー情報を取得
        con = get_db_connection()
        user = con.execute("SELECT * FROM users WHERE st_num = ?", (st_num,)).fetchone()
        con.close()
        
        # ユーザーが存在し、パスワードが一致する場合
        if user and user['pass_w'] == pass_w:
            session['user_id'] = user['id']
            session['st_num'] = user['st_num']
            session.permanent = True  # セッションの有効期限が30分に設定されます
            flash('ログイン成功しました。')
            return redirect(url_for('main.index'))
        else:
            # 認証失敗時のエラーメッセージを表示
            flash('学籍番号または合言葉が正しくありません。')
            return redirect(url_for('main.login'))
    
    # GETリクエスト時にログインページをレンダリング
    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    """
    ログアウト処理を行います。
    セッション情報をクリアし、ログインページにリダイレクトします。
    """
    session.clear()
    flash('ログアウトしました。')
    return redirect(url_for('main.login'))

# --------------- 質問・回答機能関連のルート ---------------

@main.route('/')
@login_required
def index():
    """
    トップページ（質問一覧）の表示処理です。
    ・データベースから全ての質問を取得し、作成日時の新しい順に並べます。
    ・カテゴリー一覧と「すべて」を現在のカテゴリーとしてテンプレートに渡します。
    """
    con = get_db_connection()
    cur = con.execute(
        "SELECT id, question_content, category, created_at FROM questions ORDER BY created_at DESC"
    )
    questions = cur.fetchall()
    con.close()
    return render_template("index.html", questions=questions, categories=CATEGORIES, current_category='すべて')

@main.route('/category/<category>')
@login_required
def category(category):
    """
    選択されたカテゴリーに基づいて質問一覧をフィルタリングして表示します。
    ・カテゴリーが 'すべて' の場合は全ての質問を表示します。
    ・その他の場合は、指定されたカテゴリーに一致する質問のみ取得します。
    """
    con = get_db_connection()
    if category == 'すべて':
        cur = con.execute(
            "SELECT id, question_content, category, created_at FROM questions ORDER BY created_at DESC"
        )
    else:
        cur = con.execute(
            "SELECT id, question_content, category, created_at FROM questions WHERE category = ? ORDER BY created_at DESC",
            (category,)
        )
    questions = cur.fetchall()
    con.close()
    return render_template("index.html", questions=questions, categories=CATEGORIES, current_category=category)

@main.route('/question/<int:question_id>')
@login_required
def question_detail(question_id):
    """
    個別の質問詳細ページを表示します。
    ・指定された質問IDに対応する質問内容と、その質問に対する全ての回答を取得します。
    ・現在のログインユーザーが質問の投稿者かどうかをチェックして、テンプレートに渡します。
    """
    con = get_db_connection()
    question = con.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    answers = con.execute("SELECT * FROM answers WHERE question_id = ? ORDER BY created_at DESC", (question_id,)).fetchall()
    con.close()
    # ログインユーザーが質問の投稿者であるかを確認
    is_question_owner = question['user_id'] == session['user_id']
    return render_template("question.html", question=question, answers=answers, is_question_owner=is_question_owner)

@main.route('/select_best/<int:question_id>', methods=['POST'])
@login_required
def select_best(question_id):
    """
    質問に対してベストアンサーを選択する処理です。
    ・まず、現在のユーザーが質問の投稿者であるかを確認します。
    ・フォームで選択された回答IDを元に、質問テーブルのベストアンサー関連のカラムを更新します。
    """
    con = get_db_connection()
    # 質問の投稿者情報を取得
    question = con.execute("SELECT user_id FROM questions WHERE id = ?", (question_id,)).fetchone()
    
    # 現在のユーザーが質問の投稿者でなければ権限なしとして処理終了
    if not question or question['user_id'] != session['user_id']:
        con.close()
        flash('ベストアンサーを選ぶ権限がありません。')
        return redirect(url_for('main.question_detail', question_id=question_id))

    # フォームから選択された回答のIDを取得
    selected_answer_id = request.form.get('best_answer')
    if selected_answer_id:
        answer = con.execute(
            "SELECT user_id, st_num FROM answers WHERE id = ?",
            (selected_answer_id,)
        ).fetchone()
        if answer:
            best_answer_user_id = answer['user_id']
            best_st_num = answer['st_num']
            # 質問テーブルにベストアンサーの情報を更新
            con.execute(
                "UPDATE questions SET best_answer_id = ?, best_answer_user_id = ?, best_st_num = ? WHERE id = ?",
                (selected_answer_id, best_answer_user_id, best_st_num, question_id)
            )
            con.commit()
            flash('ベストアンサーが更新されました。')
        else:
            flash('回答が見つかりませんでした。')
    else:
        flash('ベストアンサーを選択してください。')
    con.close()
    return redirect(url_for('main.question_detail', question_id=question_id))

@main.route('/ask', methods=['POST'])
@login_required
def ask():
    """
    ユーザーが新たに質問を投稿する処理です。
    ・フォームから質問内容とカテゴリーを取得し、データベースに挿入します。
    ・正しく投稿された場合、トップページにリダイレクトします。
    """
    question_content = request.form['question']
    category = request.form['category']
    if question_content and category:
        con = get_db_connection()
        con.execute(
            "INSERT INTO questions (question_content, category, date, user_id) VALUES (?, ?, CURRENT_TIMESTAMP, ?)",
            (question_content, category, session['user_id'])
        )
        con.commit()
        con.close()
    return redirect(url_for('main.index'))

@main.route('/answer/<int:question_id>', methods=['POST'])
@login_required
def answer(question_id):
    """
    指定された質問に対して回答を投稿する処理です。
    ・フォームから回答内容を取得し、該当の質問IDと共にデータベースに保存します。
    ・投稿完了後、質問詳細ページにリダイレクトします。
    """
    answer_content = request.form['answer']
    if answer_content:
        con = get_db_connection()
        con.execute(
            "INSERT INTO answers (question_id, answer_content, user_id, st_num) VALUES (?, ?, ?, ?)",
            (question_id, answer_content, session['user_id'], session['st_num'])
        )
        con.commit()
        con.close()
    return redirect(url_for('main.question_detail', question_id=question_id))
