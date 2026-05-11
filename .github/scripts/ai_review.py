import os

import requests
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"].strip())
model = os.environ.get("OPENAI_MODEL", "gpt-4o")

repo = os.environ["REPO"]
pr = os.environ["PR_NUMBER"]
token = os.environ["GITHUB_TOKEN"]
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json",
}

with open("diff.txt") as f:
    diff = f.read()

if not diff.strip():
    print("差分がありません。レビューをスキップします。")
    exit(0)

# PRの詳細（タイトル・本文）を取得
pr_url = f"https://api.github.com/repos/{repo}/pulls/{pr}"
pr_resp = requests.get(pr_url, headers=headers)
pr_data = pr_resp.json() if pr_resp.status_code == 200 else {}
pr_title = pr_data.get("title") or "No Title"
pr_body = pr_data.get("body") or ""

# PRのコメントを取得
comments_url = f"https://api.github.com/repos/{repo}/issues/{pr}/comments"
comments_resp = requests.get(comments_url, headers=headers)
comments_data = comments_resp.json() if comments_resp.status_code == 200 else []
comments_text = "\n".join(
    [
        f"- {c.get('user', {}).get('login', 'User')}: {c.get('body') or ''}"
        for c in comments_data
    ]
)
if not comments_text:
    comments_text = "なし"

prompt = f"""
あなたはシニアソフトウェアエンジニアです。

以下のPull Requestの変更をレビューしてください。
作者の意図（PRのタイトル、本文、これまでのコメント）を最大限に尊重し、それに沿ったレビューを行ってください。

【PR情報】
タイトル: {pr_title}
本文:
{pr_body}

【これまでのコメント】
{comments_text}

【レビュー観点】
- バグ
- セキュリティ
- 可読性
- 設計
- パフォーマンス

【コードの差分 (diff)】
{diff}
"""

response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "You are a senior software engineer."},
        {"role": "user", "content": prompt},
    ],
)

review = response.choices[0].message.content

url = f"https://api.github.com/repos/{repo}/issues/{pr}/comments"

resp = requests.post(
    url,
    headers={"Authorization": f"Bearer {token}"},
    json={"body": f"## AI Code Review\n\n{review}"},
)

if resp.status_code == 201:
    print("AIレビューコメントをPRに投稿しました。")
else:
    print(f"コメント投稿に失敗しました: {resp.status_code} {resp.text}")
    exit(1)
