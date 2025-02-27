# app/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3 as sql
from functools import wraps 
from datetime import datetime
import pytz
import google.generativeai as genai
import os

# 質問に用いる固定のカテゴリーの一覧です。（「すべて」は含めず、後で全件表示として扱います）
CATEGORIES = [
    '基本情報技術者試験', 'ITパスポート', 'セキュリティ教科', 'ディジタル情報', 
    '坂上先生教科', 'コンピュータ基礎', '情報システム(要件定義)', 'データサイエンスとAI',
    'マネジメントと戦略', 'データベース', 'ネットワーク基礎', 'データ構造とアルゴリズム',
    'プログラミング演習Python', 'プログラミング演習C言語', 'プログラミング演習Java',
    'Webアプリ', '画像制作', '動画制作', 'AR・VR', '半導体とアプリケーション',
    'ホームページ制作', 'PCスキルアップ', 'プレゼン', '地域経済', '情報総合実習', 
    'Geminiなんだからね','Geminiといっしょ','メスガキGemini', 'Geminiですわ','Gemini2','Gemini3','その他'
]

# Flaskのブループリントを作成し、ルーティングをグループ化しています。
main = Blueprint('main', __name__)

# Gemini APIの設定
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

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
@main.route('/category/<category>')
@login_required
def index(category='すべて'):
    """
    質問一覧を表示するルート
    """
    con = get_db_connection()
    
    if category == 'すべて':
        # すべての質問を取得
        questions = con.execute(
            'SELECT q.id, q.question_content, q.category, q.date, u.st_num FROM questions q JOIN users u ON q.user_id = u.id ORDER BY q.date DESC'
        ).fetchall()
    else:
        # 特定のカテゴリーの質問を取得
        questions = con.execute(
            'SELECT q.id, q.question_content, q.category, q.date, u.st_num FROM questions q JOIN users u ON q.user_id = u.id WHERE q.category = ? ORDER BY q.date DESC',
            (category,)
        ).fetchall()
    
    con.close()
    
    return render_template('index.html', 
                         questions=questions,
                         categories=CATEGORIES,
                         current_category=category)

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
    新しい質問を投稿する処理です。
    Geminiカテゴリーの場合は、質問投稿時に自動で回答も生成します。
    """
    question_content = request.form['question']
    category = request.form['category']
    
    if question_content and category:
        con = get_db_connection()
        # 質問を保存
        cur = con.execute(
            "INSERT INTO questions (date, question_content, category, user_id) VALUES (CURRENT_TIMESTAMP, ?, ?, ?)",
            (question_content, category, session['user_id'])
        )
        question_id = cur.lastrowid  # 新しく作成された質問のIDを取得
        
        # Geminiカテゴリーの場合、即座に回答を生成
        if category in ['Geminiなんだからね', 'Geminiといっしょ', 'メスガキGemini', 'Geminiですわ','Gemini2', 'Gemini3']:
            try:
                # カテゴリーに応じたプロンプトを設定
                if category == 'Geminiなんだからね':
                    prompt = f"""
                    あなたはツンデレ幼馴染として、以下の質問についてコメントします。
                    質問：{question_content}
                    
                    - いつも少し乱暴な口調だが、時々しおらしくなる
                    """
                elif category == 'Geminiといっしょ':
                    prompt = f"""
                    あなたは包容力たっぷりのママです。以下の質問についてコメントします。
                    質問：{question_content}
                    
                    - 基本的に語尾が伸びる
                    - テンションが一定で、マイペース
                    """
                    
                elif category == 'メスガキGemini':
                    prompt = f"""
                    あなたはメスガキです。以下の質問と回答について、生意気なコメントをします。
                    質問：{question_content}
                    
                    - 二人称は「お兄さん」。
                    - 質問者や回答者が自分より年齢が上であるのに、問題の解決が出来ないことで、見下しているようなコメント
                    """

                elif category == 'Geminiですわ':
                    prompt = f"""
                    あなたは高飛車なお嬢様として、以下の質問について、コメントをします。
                    質問：{question_content}
                    
                    - 二人称は「あなた」。
                    - 高慢、高飛車な性格
                    - 一人称は「わたくし」
                    - 語尾は「ですわ」←なるべく自然に
                    """

                elif category == 'Gemini2':
                    prompt = f"""
                    あなたはほんの少し偉そうな態度で、以下の質問についてコメントします。
                    質問：{question_content}
                    
                    - ほんの少し不遜な敬語
                    - 「ウェブ」のことを「ウェッブ」という
                    - 「インストール」のことを「インストゥール」という
                    - 時々、褒めてくれる
                    """
                else:  # Gemini3
                    prompt = f"""
                    あなたは丁寧な言葉遣いを心がけます。しかし、質問へのコメントは中身がなくただ見せかけの言葉です。
                    質問：{question_content}
                    
                    - 「ざっくばらん」という言葉が好き
                    - 「簡潔にいうと」といって、中身のない話をはじめる
                    - どうでもいいことにこだわる
                    - 質問へのコメントをはぐらかす
                    """
                
                # セーフティ設定を調整
                safety_settings = [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_NONE",
                    },
                ]
                
                # Gemini APIで回答を生成
                response = model.generate_content(
                    prompt,
                    safety_settings=safety_settings,
                    generation_config={
                        "temperature": 0.7,
                        "top_p": 0.8,
                        "top_k": 40,
                    }
                )
                
                if response.text:
                    # Geminiの回答を保存
                    con.execute(
                        "INSERT INTO answers (question_id, answer_content, user_id, st_num) VALUES (?, ?, ?, ?)",
                        (question_id, response.text, session['user_id'], "Gemini AI")
                    )
                
            except Exception as e:
                flash('Gemini APIでエラーが発生しました。')
                print(f"Gemini API error: {e}")
        
        con.commit()
        con.close()
        return redirect(url_for('main.question_detail', question_id=question_id))
    
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
        
        # ここからGemini   質問のカテゴリーを確認
        question = con.execute(
            "SELECT question_content, category FROM questions WHERE id = ?", 
            (question_id,)
        ).fetchone()

        # Geminiカテゴリーの場合、APIで回答を生成
        if question['category'] == 'Geminiなんだからね':
            # これまでの回答を取得
            previous_answers = con.execute(
                "SELECT answer_content FROM answers WHERE question_id = ? ORDER BY created_at ASC",
                (question_id,)
            ).fetchall()
            
            # プロンプトの作成
            prompt = f"""
            あなたはツンデレ幼馴染として、以下の質問と回答について、ツンデレらしいコメントをします。
            質問：{question['question_content']}
            
            これまでの回答：
            {' '.join([ans['answer_content'] for ans in previous_answers])}
            
            新しい回答：{answer_content}
            
            - いつも少し乱暴な口調だが、時々しおらしくなる
            """
            
            # Gemini APIで回答を生成
            try:
                response = model.generate_content(prompt)
                gemini_answer = response.text
                
                # Geminiの回答を保存
                con.execute(
                    "INSERT INTO answers (question_id, answer_content, user_id, st_num) VALUES (?, ?, ?, ?)",
                    (question_id, gemini_answer, session['user_id'], "Gemini AI")
                )
            except Exception as e:
                flash('Gemini APIでエラーが発生しました。')
                print(f"Gemini API error: {e}")

        elif question['category'] == 'Geminiといっしょ':
            # これまでの回答を取得
            previous_answers = con.execute(
                "SELECT answer_content FROM answers WHERE question_id = ? ORDER BY created_at ASC",
                (question_id,)
            ).fetchall()
            
            # プロンプトの作成
            prompt = f"""
            あなたは包容力たっぷりのママです。以下の質問と回答について、バブみを感じさせるママらしいコメントをします。
            質問：{question['question_content']}
            
            これまでの回答：
            {' '.join([ans['answer_content'] for ans in previous_answers])}
            
            新しい回答：{answer_content}
            
            - 「まぁまぁ」、「まぁ」、「あらぁ」などを接頭語に使う。
            - 基本的に語尾が伸びる
            - テンションが一定で、マイペース
            - ママの年齢に関することは、NG ちょっと怖くなる
            """
            
            # Gemini APIで回答を生成
            try:
                response = model.generate_content(prompt)
                gemini_answer = response.text
                
                # Geminiの回答を保存
                con.execute(
                    "INSERT INTO answers (question_id, answer_content, user_id, st_num) VALUES (?, ?, ?, ?)",
                    (question_id, gemini_answer, session['user_id'], "Gemini AI")
                )
            except Exception as e:
                flash('Gemini APIでエラーが発生しました。')
                print(f"Gemini API error: {e}")


        elif question['category'] == 'メスガキGemini':
            # これまでの回答を取得
            previous_answers = con.execute(
                "SELECT answer_content FROM answers WHERE question_id = ? ORDER BY created_at ASC",
                (question_id,)
            ).fetchall()
            
            # プロンプトの作成
            prompt = f"""
            あなたはメスガキです。以下の質問と回答について、生意気なコメントをします。
            質問：{question['question_content']}
            
            これまでの回答：
            {' '.join([ans['answer_content'] for ans in previous_answers])}
            
            新しい回答：{answer_content}
            
            - 二人称は「お兄さん」。
            - 質問者や回答者が自分より年齢が上であるのに、問題の解決が出来ないことで、見下しているようなコメント
            """
            
            # Gemini APIで回答を生成
            try:
                response = model.generate_content(prompt)
                gemini_answer = response.text
                
                # Geminiの回答を保存
                con.execute(
                    "INSERT INTO answers (question_id, answer_content, user_id, st_num) VALUES (?, ?, ?, ?)",
                    (question_id, gemini_answer, session['user_id'], "Gemini AI")
                )
            except Exception as e:
                flash('Gemini APIでエラーが発生しました。')
                print(f"Gemini API error: {e}")

        elif question['category'] == 'Geminiですわ':
            # これまでの回答を取得
            previous_answers = con.execute(
                "SELECT answer_content FROM answers WHERE question_id = ? ORDER BY created_at ASC",
                (question_id,)
            ).fetchall()
            
            # プロンプトの作成
            prompt = f"""
            あなたは高飛車なお嬢様として、以下の質問と回答について、コメントをします。
            質問：{question['question_content']}
            
            これまでの回答：
            {' '.join([ans['answer_content'] for ans in previous_answers])}
            
            新しい回答：{answer_content}
            
            
            - 二人称は「あなた」。
            - 高慢、高飛車な性格
            - 一人称は「わたくし」
            - 語尾は「ですわ」←なるべく自然に
            """
            
            # Gemini APIで回答を生成
            try:
                response = model.generate_content(prompt)
                gemini_answer = response.text
                
                # Geminiの回答を保存
                con.execute(
                    "INSERT INTO answers (question_id, answer_content, user_id, st_num) VALUES (?, ?, ?, ?)",
                    (question_id, gemini_answer, session['user_id'], "Gemini AI")
                )
            except Exception as e:
                flash('Gemini APIでエラーが発生しました。')
                print(f"Gemini API error: {e}")


        elif question['category'] == 'Gemini2':
            # これまでの回答を取得
            previous_answers = con.execute(
                "SELECT answer_content FROM answers WHERE question_id = ? ORDER BY created_at ASC",
                (question_id,)
            ).fetchall()
            
            # プロンプトの作成
            prompt = f"""
            あなたはほんの少し偉そうな態度で、以下の質問と回答についてコメントします。(例)こんくらい簡単にできるだろ。
            質問：{question['question_content']}
            
            これまでの回答：
            {' '.join([ans['answer_content'] for ans in previous_answers])}
            
            新しい回答：{answer_content}
            
            - ほんの少し不遜な敬語。
            - 「ウェブ」のことを「ウェッブ」という
            - 「インストール」のことを「インストゥール」という
            - 時々、褒めてくれる
            - 頭がいいが、ほんの少し人を馬鹿にしたような感じ
            """
            
            # Gemini APIで回答を生成
            try:
                response = model.generate_content(prompt)
                gemini_answer = response.text
                
                # Geminiの回答を保存
                con.execute(
                    "INSERT INTO answers (question_id, answer_content, user_id, st_num) VALUES (?, ?, ?, ?)",
                    (question_id, gemini_answer, session['user_id'], "Gemini AI")
                )
            except Exception as e:
                flash('Gemini APIでエラーが発生しました。')
                print(f"Gemini API error: {e}")


        elif question['category'] == 'Gemini3':
            # これまでの回答を取得
            previous_answers = con.execute(
                "SELECT answer_content FROM answers WHERE question_id = ? ORDER BY created_at ASC",
                (question_id,)
            ).fetchall()
            
            # プロンプトの作成
            prompt = f"""
            あなたは丁寧な言葉遣いを心がけます。しかし、以下の質問や回答へのコメントは中身がなくただ見せかけの言葉です。
            質問：{question['question_content']}
            
            これまでの回答：
            {' '.join([ans['answer_content'] for ans in previous_answers])}
            
            新しい回答：{answer_content}
            
            - 「ざっくばらん」という言葉が好き
            - 「簡潔にいうと」といって、中身のない話をはじめる
            - どうでもいいことにこだわる
            - 質問や回答へのコメントをはぐらかす
            - 1/25の確立で逆上する
            """
            
            # Gemini APIで回答を生成
            try:
                response = model.generate_content(prompt)
                gemini_answer = response.text
                
                # Geminiの回答を保存
                con.execute(
                    "INSERT INTO answers (question_id, answer_content, user_id, st_num) VALUES (?, ?, ?, ?)",
                    (question_id, gemini_answer, session['user_id'], "Gemini AI")
                )
            except Exception as e:
                flash('Gemini APIでエラーが発生しました。')
                print(f"Gemini API error: {e}")

        #↑ここまでGemini
        # ユーザーの回答を保存
        con.execute(
            "INSERT INTO answers (question_id, answer_content, user_id, st_num) VALUES (?, ?, ?, ?)",
            (question_id, answer_content, session['user_id'], session['st_num'])
        )
        
        con.commit()
        con.close()
    return redirect(url_for('main.question_detail', question_id=question_id))

@main.route('/get_gemini_comment', methods=['POST'])
@login_required
def get_gemini_comment():
    """
    Gemini APIを使用して、質問に対する即時の感想を返します。
    """
    category = request.form.get('category')
    question = request.form.get('question')

    if not category or not question:
        return '質問を入力してください。'

    try:
        # カテゴリーに応じたプロンプトを設定
        if category == 'Geminiなんだからね':
            prompt = f"""
            あなたはツンデレ幼馴染として、以下の質問について一言コメントします（30文字以内）。
            質問：{question}
            
            - いつも少し乱暴な口調
            - 時々しおらしくなる
            - あなたは、質問一覧を能動的にみている
            """
        elif category == 'Geminiといっしょ':
            prompt = f"""
            あなたは包容力たっぷりのママとして、以下の質問について一言コメントします（30文字以内）。
            質問：{question}
            
            - 「まぁまぁ」「あらぁ」などを使う
            - 語尾が伸びる
            - テンションが一定で、マイペース
            - あなたは、質問一覧を能動的にみている
            """
        elif category == 'メスガキGemini':
            prompt = f"""
            あなたはメスガキとして、以下の質問について、生意気なコメントをします（30文字以内）。
            質問：{question}
            
            - 二人称は「お兄さん」。
            - 質問者や回答者が自分より年齢が上であるのに、問題の解決が出来ないことで、見下しているようなコメント
            - 一人称は「リリン」
            - あなたは、質問一覧を能動的にみている
            - 禁止事項：自分のことを「メスガキ」と言うこと
            """
        elif category == 'Geminiですわ':
            prompt = f"""
            あなたは高飛車なお嬢様として、以下の質問について、コメントをします（30文字以内）。
            質問：{question}
            
            - 二人称は「あなた」。
            - 高慢、高飛車な性格
            - 一人称は「わたくし」
            - 語尾は「ですわ」←なるべく自然に
            - あなたは、質問一覧を能動的にみている
            """
        elif category == 'Gemini2':
            prompt = f"""
            あなたはほんの少し偉そうな態度で、以下の質問について一言コメントします（30文字以内）。
            質問：{question}
            
            - ほんの少し不遜な敬語
            - 「ウェッブ」「インストゥール」
            - あなたは、質問一覧を能動的にみている
            """
        else:  # Gemini3
            prompt = f"""
            中身のない一言コメントをします（30文字以内）。
            質問：{question}
            
            - 「ざっくばらん」が好き
            - どうでもいいことにこだわる
            - あなたは、質問一覧を能動的にみている
            """

        # セーフティ設定
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE",
            },
        ]

        # Gemini APIで回答を生成
        response = model.generate_content(
            prompt,
            safety_settings=safety_settings,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
            }
        )

        return response.text

    except Exception as e:
        print(f"Gemini API error: {e}")
        return 'コメントの生成に失敗しました。'
