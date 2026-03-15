import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
model = os.environ.get("OPENAI_MODEL", "gpt-4o")

code = ""

for root, dirs, files in os.walk("src"):
    dirs[:] = [d for d in dirs if d not in {"__pycache__"}]
    for f in files:
        if f.endswith(".py"):
            with open(os.path.join(root, f)) as fp:
                code += f"# File: {os.path.join(root, f)}\n" + fp.read() + "\n\n"

if not code.strip():
    print("src/ にPythonファイルが見つかりません。スキップします。")
    exit(0)

# README生成
readme_prompt = f"""
あなたは技術ドキュメントの専門家です。
以下のコードベースのREADME.mdを日本語で作成してください。

含める内容:
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成

コード:
{code[:120000]}
"""

readme_response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "You are a technical documentation specialist."},
        {"role": "user", "content": readme_prompt}
    ]
)

readme = readme_response.choices[0].message.content

with open("README.md", "w", encoding="utf-8") as f:
    f.write(readme)

print("README.md を生成しました。")

# CHANGELOG生成
changelog_prompt = f"""
以下のコードベースの変更履歴をCHANGELOG.md形式（Keep a Changelog準拠）で日本語で作成してください。
コードの内容から推測して記載してください。

コード:
{code[:60000]}
"""

changelog_response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "You are a technical documentation specialist."},
        {"role": "user", "content": changelog_prompt}
    ]
)

changelog = changelog_response.choices[0].message.content

with open("CHANGELOG.md", "w", encoding="utf-8") as f:
    f.write(changelog)

print("CHANGELOG.md を生成しました。")
