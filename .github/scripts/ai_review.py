import os
import requests
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"].strip())
model = os.environ.get("OPENAI_MODEL", "gpt-4o")

with open("diff.txt") as f:
    diff = f.read()

if not diff.strip():
    print("差分がありません。レビューをスキップします。")
    exit(0)

prompt = f"""
あなたはシニアソフトウェアエンジニアです。

以下のPull Requestの変更をレビューしてください。

レビュー観点
- バグ
- セキュリティ
- 可読性
- 設計
- パフォーマンス

diff:
{diff}
"""

response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "You are a senior software engineer."},
        {"role": "user", "content": prompt}
    ]
)

review = response.choices[0].message.content

repo = os.environ["REPO"]
pr = os.environ["PR_NUMBER"]
token = os.environ["GITHUB_TOKEN"]

url = f"https://api.github.com/repos/{repo}/issues/{pr}/comments"

resp = requests.post(
    url,
    headers={"Authorization": f"Bearer {token}"},
    json={"body": f"## AI Code Review\n\n{review}"}
)

if resp.status_code == 201:
    print("AIレビューコメントをPRに投稿しました。")
else:
    print(f"コメント投稿に失敗しました: {resp.status_code} {resp.text}")
    exit(1)
