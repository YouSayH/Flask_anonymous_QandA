from app import create_app

app = create_app()

if __name__ == '__main__':
    # EC2上で動作させる場合、ホストは'0.0.0.0'に設定して外部からのアクセスを許可します。
    app.run(host='0.0.0.0', port=5000, debug=False)
