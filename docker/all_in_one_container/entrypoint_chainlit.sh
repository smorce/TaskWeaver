#!/bin/bash

USER_ID=${TASKWEAVER_UID:-10002}
GROUP_ID=${TASKWEAVER_GID:-10002}

echo "Starting with UID: $USER_ID, GID: $GROUP_ID"
useradd -u $USER_ID -o -m taskweaver
groupmod -g $GROUP_ID taskweaver

# ファイルの所有権を変更
chown -R taskweaver:taskweaver /app

# ファイルサーバーをバックグラウンドで起動
# localhost の部分をクラウドランのアドレスにする
echo "***FastAPIのファイルサーバーを起動します***   http://localhost:8080"
python file_server.py &

su taskweaver -c "cd playground/UI/ && python -m chainlit run --host 0.0.0.0 --port 8000 app.py"