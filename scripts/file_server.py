import os
import glob
import datetime
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import HTMLResponse

app = FastAPI()

# ファイルをリストアップし、情報を取得する関数
def list_files(directory):
    files = []
    now = time.time()
    thirty_days_ago = now - 30 * 24 * 60 * 60  # 30日前のタイムスタンプ

    for root, dirs, filenames in os.walk(directory):
        for filename in filenames:
            path = os.path.join(root, filename)
            stats = os.stat(path)
            modified_time = stats.st_mtime

            # 30日以上経過したファイルを削除
            if modified_time < thirty_days_ago:
                # os.remove(path)
                # print("セキュリティの観点から、30日経過したファイルは削除しました")
                print("デバッグ中なので大事なファイルが削除されないようにコメントアウト")
                print()
                continue

            files.append({
                'name': filename,
                'path': path,
                'url': f'/download/{path}',
                'modified': datetime.datetime.fromtimestamp(modified_time),
                'size': stats.st_size
            })

    # 更新日時の新しい順にソート
    return sorted(files, key=lambda x: x['modified'], reverse=True)


@app.get("/", response_class=HTMLResponse)
async def index():
    # 現在のスクリプトのディレクトリを取得（デバッグ中）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print("デバッグ。ファイルサーバー")
    print(script_dir)   # app にいる

    # outputsディレクトリ内のrun_*にマッチするディレクトリを取得
    source_dirs = glob.glob(os.path.join("playground", "UI", "outputs", "run_*"))
    # source_dirs = glob.glob(os.path.join(script_dir))
    all_files = []
    for dir in source_dirs:
        all_files.extend(list_files(dir))

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            table {
                border-collapse: collapse;
                width: 100%;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
            }
        </style>
    </head>
    <body>
        <h1>ファイルリスト</h1>
        <table>
            <tr>
                <th>ファイル名</th>
                <th>更新日時</th>
                <th>サイズ</th>
            </tr>
            {file_rows}
        </table>
    </body>
    </html>
    """
    file_rows = "".join([
        f'<tr><td><a href="{file["url"]}">{file["name"]}</a></td>'
        f'<td>{file["modified"].strftime("%Y-%m-%d %H:%M:%S")}</td>'
        f'<td>{file["size"] // 1024} KB</td></tr>'
        for file in all_files
    ])
    return HTMLResponse(content=html_content.replace("{file_rows}", file_rows))


@app.get("/download/{filepath:path}")
async def download_file(filepath: str):
    if os.path.isfile(filepath):
        return FileResponse(filepath, filename=os.path.basename(filepath))
    else:
        raise HTTPException(status_code=404, detail="File not found")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("FILE_SERVER_PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)