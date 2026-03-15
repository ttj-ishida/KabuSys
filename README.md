# KabuSys

日本株自動売買システムのベースパッケージ（骨組み）。  
このリポジトリは「KabuSys」と名付けた自動売買フレームワークの最小構成で、データ取得・ストラテジ・注文実行・監視の4つの主要コンポーネントを想定しています。現在はパッケージ構成のみが含まれ、実際のロジックは各モジュールに実装していく形になります。

---

## 概要

KabuSys は、日本株を対象とした自動売買アプリケーションを構築するためのフレームワークです。  
モジュールを分離して設計しているため、以下を容易に差し替え・拡張できます。

- 市場データ取得（data）
- 売買ロジック（strategy）
- 注文実行（execution）
- 監視・ログ／アラート（monitoring）

現状はパッケージのひな型のみ含まれており、各サブパッケージに実装を追加して利用します。

---

## 機能一覧（予定・想定）

- 市場データ取得（リアルタイム / 過去データ）
- 売買ストラテジの定義・バックテスト・最適化
- 注文の発行／管理（マーケット・指値・成行など）
- リスク管理（ポジション制御、最大ドローダウン制限）
- ログと通知（メール／Slack等）

※ 現在のリポジトリは構造のみ。上記機能は各モジュールへ実装する想定です。

---

## 要件

- Python 3.8 以上（推奨：3.9+）
- （任意）仮想環境（venv / virtualenv / pyenv など）
- 実際に取引する場合は、証券会社API（kabuステーションやブローカーAPI等）のアカウント・認証情報が必要

依存パッケージは現状 requirements ファイルが無いため、実装に合わせて追加してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <このリポジトリのURL>
   cd <リポジトリ名>
   ```

2. 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. 開発用にインストール（ローカルで編集する場合）
   ```
   pip install -e .
   ```
   > 実装に必要なパッケージがあれば、requirements.txt を作成して `pip install -r requirements.txt` を実行してください。

4. （任意）テストフレームワークやリンターを導入する場合は、pytest / flake8 / black 等を追加でインストールしてください。

---

## 使い方（基本例）

現在のパッケージは構造のみのため、まずはパッケージがインポートできることを確認します。

Python REPL またはスクリプトで：
```python
import kabusys
print(kabusys.__version__)  # 0.1.0
```

各サブパッケージに具体的な実装を追加していきます。以下は実装例の骨子（サンプル）です。

- strategy/strategy_example.py（ストラテジの雛形）
```python
from kabusys.strategy import BaseStrategy  # 仮想のベースクラスを定義しておく

class SimpleStrategy(BaseStrategy):
    def on_market_data(self, data):
        # data に基づき売買判断を行う
        if self.should_buy(data):
            self.execution.place_order(symbol=data.symbol, side='BUY', qty=100)
```

- execution/api_client.py（注文実行インターフェース）
```python
class ExecutionClient:
    def place_order(self, symbol: str, side: str, qty: int, price: float = None):
        # 実際のAPI呼び出しを実装
        pass
```

- monitoring/logger.py（監視・通知）
```python
import logging

logger = logging.getLogger("kabusys")
logger.setLevel(logging.INFO)
# ハンドラやフォーマッタを設定
```

上のように、各サブパッケージに必要なクラス・関数を追加していってください。

---

## ディレクトリ構成

現在のリポジトリ（主要ファイルのみ）:

- src/
  - kabusys/
    - __init__.py            # パッケージ定義、バージョン情報
    - data/
      - __init__.py          # 市場データ関連（未実装）
    - strategy/
      - __init__.py          # ストラテジ関連（未実装）
    - execution/
      - __init__.py          # 注文実行関連（未実装）
    - monitoring/
      - __init__.py          # 監視・ログ関連（未実装）

README や将来的なファイル例（実装例）
- requirements.txt (未作成)
- setup.cfg / pyproject.toml (任意・未作成)
- tests/ (ユニットテストを配置するディレクトリ、未作成)

ツリー（簡潔表示）
```
src/
└── kabusys/
    ├── __init__.py
    ├── data/
    │   └── __init__.py
    ├── execution/
    │   └── __init__.py
    ├── monitoring/
    │   └── __init__.py
    └── strategy/
        └── __init__.py
```

---

## 開発上の注意・推奨

- API キーや認証情報はハードコードせず、環境変数や外部の設定ファイル（.env 等）で管理してください。
- 実際の売買を行う前に、必ずバックテストとペーパートレードで挙動検証を行ってください。
- 取引にはリスクが伴います。自己責任で行ってください。
- CI（自動テスト）やコード品質ツールの導入を推奨します。

---

この README は現在のコードベース（パッケージひな形）に基づく説明です。実装を進める際に必要な具体的なヘルパー関数、抽象クラス、インターフェース、および外部APIクライアントを追加していってください。必要であれば、テンプレート実装や具体例の追加も手伝います。