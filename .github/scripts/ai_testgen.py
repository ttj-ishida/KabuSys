import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"].strip())
model = os.environ.get("OPENAI_MODEL", "gpt-4o")

code = ""

for root, dirs, files in os.walk("src"):
    for file in files:
        if file.endswith(".py"):
            with open(os.path.join(root, file)) as f:
                code += f.read()

if not code.strip():
    print("src/ にPythonファイルが見つかりません。スキップします。")
    exit(0)

prompt = f"""
あなたは優秀なシニアソフトウェアエンジニアです。
以下のコードに対するpytestユニットテストを生成してください。

要件:
- pytestを使用する
- 各関数・クラスの主要な動作をカバーする
- エッジケースも含める
- モックが必要な外部依存はunittest.mockを使用する

コード:
{code[:100000]}
"""

response = client.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "system",
            "content": (
                "You are a senior software engineer specializing in Python testing. "
                "Output ONLY valid Python code. "
                "Do NOT output any conversational text, explanations, or markdown formatting "
                "(such as ```python or ```)."
            ),
        },
        {"role": "user", "content": prompt},
    ],
)

tests = response.choices[0].message.content

# マークダウンのコードフェンスを除去して純粋なPythonコードのみ抽出
# LLMが「説明文 + ```python ... ``` + 締め文」を返す場合も考慮し、
# 最初のフェンス開始行と最後のフェンス終了行の間を採用する。
lines = tests.strip().splitlines()
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
tests = "\n".join(lines)

os.makedirs("tests", exist_ok=True)
with open("tests/test_generated.py", "w", encoding="utf-8") as f:
    f.write(tests)

print("テストファイルを生成しました: tests/test_generated.py")
