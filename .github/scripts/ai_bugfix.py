import os
import requests
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"].strip())
model = os.environ.get("OPENAI_MODEL", "gpt-4o")

code = ""

for root, dirs, files in os.walk("."):
    # .github, .git, __pycache__ は除外
    dirs[:] = [d for d in dirs if d not in {".git", ".github", "__pycache__", "node_modules"}]
    for file in files:
        if file.endswith(".py"):
            with open(os.path.join(root, file)) as f:
                code += f"# File: {os.path.join(root, file)}\n" + f.read() + "\n\n"

prompt = f"""
あなたは優秀なシニアソフトウェアエンジニアです。
以下のコードにバグがあれば修正してください。

観点:
- バグ・ロジックエラー
- セキュリティ脆弱性
- 例外処理の不備
- リソースリーク

修正が必要な箇所を特定し、unified diff形式で出力してください。

コード:
{code[:100000]}
"""

response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "You are a senior software engineer specializing in bug detection and code review."},
        {"role": "user", "content": prompt}
    ]
)

fixed = response.choices[0].message.content

with open("ai_patch.diff", "w", encoding="utf-8") as f:
    f.write(fixed)

print("パッチファイルを生成しました: ai_patch.diff")
