import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"].strip())
model = os.environ.get("OPENAI_MODEL", "gpt-4o")

code = ""

for root, dirs, files in os.walk("."):
    # .github, .git, __pycache__ は除外
    dirs[:] = [
        d for d in dirs if d not in {".git", ".github", "__pycache__", "node_modules"}
    ]
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
        {
            "role": "system",
            "content": (
                "You are a senior software engineer specializing in bug detection and code review. "
                "Output ONLY valid unified diff format. "
                "Do NOT output any conversational text, explanations, or markdown formatting "
                "(such as ```diff or ```python). "
                "If there are no bugs, output an empty string."
            ),
        },
        {"role": "user", "content": prompt},
    ],
)

fixed = response.choices[0].message.content

# マークダウンのコードフェンスを除去する
# LLMが「説明文 + ```diff ... ``` + 締め文」を返す場合も考慮し、
# 最初のフェンス開始行から直後のクローズフェンスまでを採用する。
# （最後のフェンスを採用すると複数ブロック間の説明文を巻き込む恐れがある）
lines = fixed.strip().splitlines()
first_open = next((i for i, ln in enumerate(lines) if ln.startswith("```")), None)
if first_open is not None:
    first_close = next(
        (i for i in range(first_open + 1, len(lines)) if lines[i].strip() == "```"),
        None,
    )
    if first_close is not None:
        lines = lines[first_open + 1 : first_close]
    else:
        # クローズフェンスなし: 開始フェンス行のみ除去
        lines = lines[first_open + 1 :]
fixed = "\n".join(lines)

with open("ai_patch.diff", "w", encoding="utf-8") as f:
    f.write(fixed)

print("パッチファイルを生成しました: ai_patch.diff")
