# app/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3 as sql
from functools import wraps 
from datetime import datetime
import pytz


# 固定のカテゴリーリスト（「すべて」は含めない）
CATEGORIES = [
    '基本情報技術者試験', 'ITパスポート', 'セキュリティ教科', 'ディジタル情報', 
    '坂上先生教科', 'コンピュータ基礎', '情報システム(要件定義)', 'データサイエンスとAI',
    'マネジメントと戦略', 'データベース', 'ネットワーク基礎', 'データ構造とアルゴリズム',
    'プログラミング演習Python', 'プログラミング演習C言語', 'プログラミング演習Java',
    'Webアプリ', '画像制作', '動画制作', 'AR・VR', '半導体とアプリケーション',
    'ホームページ制作', 'PCスキルアップ', 'プレゼン', '地域経済', '情報総合実習', 'その他'
]

# blueprintの作成
main = Blueprint('main', __name__)

def get_db_connection():
    """
    SQLite3データベースへの接続を確立します。
    レコードを辞書形式で扱えるようにし、日本時間用のCURRENT_TIMESTAMP関数を登録します。
    """
    con = sql.connect('hajimeteno.db')
    con.row_factory = sql.Row
    con.execute("PRAGMA timezone = '+09:00'")
    
    def get_jst_datetime():
        return datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')
    
    con.create_function('CURRENT_TIMESTAMP', 0, get_jst_datetime)
    return con

def login_required(f):
    """
    ログイン状態をチェックするデコレータ。
    セッションに'user_id'が存在しなければログイン画面へリダイレクトします。
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('ログインが必要です。')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

# --------------- ログイン関連 ---------------

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        st_num = request.form['st_num'].strip()
        pass_w = request.form['pass_w'].strip()
        
        con = get_db_connection()
        user = con.execute("SELECT * FROM users WHERE st_num = ?", (st_num,)).fetchone()
        con.close()
        
        if user and user['pass_w'] == pass_w:
            session['user_id'] = user['id']
            session['st_num'] = user['st_num']
            session.permanent = True  # セッションの有効期限を有効化
            flash('ログイン成功しました。')
            return redirect(url_for('main.index'))
        else:
            flash('学籍番号または合言葉が正しくありません。')
            return redirect(url_for('main.login'))
    
    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    session.clear()
    flash('ログアウトしました。')
    return redirect(url_for('main.login'))

# --------------- 質問・回答機能 ---------------

@main.route('/')
@login_required
def index():
    con = get_db_connection()
    cur = con.execute(
        "SELECT id, question_content, category, created_at FROM questions ORDER BY created_at DESC"
    )
    questions = cur.fetchall()
    con.close()
    # current_category が未指定の場合は全件表示として扱う（例：None または 'すべて'）
    return render_template("index.html", questions=questions, categories=CATEGORIES, current_category='すべて')

@main.route('/category/<category>')
@login_required
def category(category):
    con = get_db_connection()
    if category == 'すべて':
        # フィルタせず全件表示
        cur = con.execute(
            "SELECT id, question_content, category, created_at FROM questions ORDER BY created_at DESC"
        )
    else:
        # 選択されたカテゴリーの質問のみ取得
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
    con = get_db_connection()
    question = con.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    answers = con.execute("SELECT * FROM answers WHERE question_id = ? ORDER BY created_at DESC", (question_id,)).fetchall()
    con.close()
    # 現在のユーザーが質問投稿者かどうかをチェック
    is_question_owner = question['user_id'] == session['user_id']
    return render_template("question.html", question=question, answers=answers, is_question_owner=is_question_owner)

@main.route('/select_best/<int:question_id>', methods=['POST'])
@login_required
def select_best(question_id):
    con = get_db_connection()
    # 質問の所有者を確認
    question = con.execute("SELECT user_id FROM questions WHERE id = ?", (question_id,)).fetchone()
    
    # 質問投稿者でない場合はアクセスを拒否
    if not question or question['user_id'] != session['user_id']:
        con.close()
        flash('ベストアンサーを選ぶ権限がありません。')
        return redirect(url_for('main.question_detail', question_id=question_id))

    # 以下、元のコード
    selected_answer_id = request.form.get('best_answer')
    if selected_answer_id:
        answer = con.execute(
            "SELECT user_id, st_num FROM answers WHERE id = ?",
            (selected_answer_id,)
        ).fetchone()
        if answer:
            best_answer_user_id = answer['user_id']
            best_st_num = answer['st_num']
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
