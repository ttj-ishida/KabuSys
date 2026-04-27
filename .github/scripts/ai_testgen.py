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
lines = tests.strip().splitlines()
if lines and lines[0].startswith("```"):
    lines = lines[1:]
if lines and lines[-1].strip() == "```":
    lines = lines[:-1]
tests = "\n".join(lines)

os.makedirs("tests", exist_ok=True)
with open("tests/test_generated.py", "w", encoding="utf-8") as f:
    f.write(tests)

print("テストファイルを生成しました: tests/test_generated.py")
