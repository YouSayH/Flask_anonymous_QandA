学科限定の匿名質問サイトを作りました。
ログインの為の学籍番号とパスワードは、管理者がusersテーブルのst_numとpass_wに設定してください。
構成はAWS EC2でリバースプロキシサーバー(Nginx)とwebサーバー(Gunicorn)で作っています。

インストールすべきもの
<br>
・python3 ・venv ・Flask ・Gunicorn
<br>
・Werkzeug ・SQLite3 ・pytz
