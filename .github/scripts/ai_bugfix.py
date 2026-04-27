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
# 最初のフェンス開始行と最後のフェンス終了行の間を採用する。
lines = fixed.strip().splitlines()
first_fence = next((i for i, l in enumerate(lines) if l.startswith("```")), None)
last_fence = next(
    (i for i in range(len(lines) - 1, -1, -1) if lines[i].strip() == "```"), None
)
if first_fence is not None and last_fence is not None and first_fence < last_fence:
    lines = lines[first_fence + 1 : last_fence]
else:
    # フォールバック: 先頭・末尾のフェンスのみ除去
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
fixed = "\n".join(lines)

with open("ai_patch.diff", "w", encoding="utf-8") as f:
    f.write(fixed)

print("パッチファイルを生成しました: ai_patch.diff")
