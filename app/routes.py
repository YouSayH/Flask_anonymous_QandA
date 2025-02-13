# app/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3 as sql
from functools import wraps
from datetime import datetime
import pytz

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
        student_number = request.form['student_number'].strip()
        passphrase = request.form['passphrase'].strip()
        
        con = get_db_connection()
        user = con.execute("SELECT * FROM users WHERE student_number = ?", (student_number,)).fetchone()
        con.close()
        
        if user and user['passphrase'] == passphrase:
            session['user_id'] = user['id']
            session['student_number'] = user['student_number']
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
    cur = con.execute("SELECT id, question_content, created_at FROM questions ORDER BY created_at DESC")
    questions = cur.fetchall()
    con.close()
    return render_template("index.html", questions=questions)

@main.route('/question/<int:question_id>')
@login_required
def question_detail(question_id):
    con = get_db_connection()
    question = con.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    answers = con.execute("SELECT * FROM answers WHERE question_id = ? ORDER BY created_at DESC", (question_id,)).fetchall()
    con.close()
    return render_template("question.html", question=question, answers=answers)

@main.route('/ask', methods=['POST'])
@login_required
def ask():
    question_content = request.form['question']
    if question_content:
        con = get_db_connection()
        con.execute(
            "INSERT INTO questions (question_content, date, user_id) VALUES (?, CURRENT_TIMESTAMP, ?)",
            (question_content, session['user_id'])
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
            "INSERT INTO answers (question_id, answer_content, user_id) VALUES (?, ?, ?)",
            (question_id, answer_content, session['user_id'])
        )
        con.commit()
        con.close()
    return redirect(url_for('main.question_detail', question_id=question_id))
