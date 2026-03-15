# KabuSys

KabuSys は日本株向けの自動売買（アルゴリズムトレード）システムの骨組み（スケルトン）です。現時点ではパッケージ構成と基本メタ情報のみが含まれており、各サブパッケージ（データ取得、戦略、注文実行、監視）の実装を追加して利用します。

バージョン: 0.1.0

---

## プロジェクト概要

このリポジトリは日本株の自動売買システムを構築するための基本パッケージ構造を提供します。以下のサブパッケージを想定しています。

- data: 市場データの取得・前処理
- strategy: 売買戦略の実装（シグナル生成）
- execution: 注文発行・約定管理
- monitoring: ログ、通知、ダッシュボード等の監視機能

本 README は現状の構造とセットアップ／使い方の例を示し、実装を拡張するためのガイドを提供します。

---

## 機能一覧（想定）

現状はスケルトンです。実装候補の機能は次の通りです。

- データ取得
  - リアルタイム/過去価格の取得（API 経由、CSV ロードなど）
  - データの正規化・補間・保存
- 戦略
  - 指数移動平均（EMA）クロスなどのシグナル生成
  - リスク管理（ポジションサイズ、最大ドローダウン）
- 注文実行
  - 証券会社 API への注文送信（成行/指値/取消）
  - 注文状態のトラッキング、再試行
- 監視
  - ログ記録、アラート（Slack/メール）
  - 実行状況のダッシュボード表示

---

## 要件

- Python 3.8+
- （任意）仮想環境の使用を推奨

外部 API やライブラリは用途に応じて追加してください（例: requests、pandas、numpy、websocket-client など）。

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   # macOS / Linux
   source .venv/bin/activate
   # Windows (PowerShell)
   .\.venv\Scripts\Activate.ps1
   ```

3. 必要パッケージをインストール
   - 現状 requirements.txt は含まれていません。実装に合わせて requirements.txt / pyproject.toml を作成し、以下のようにインストールしてください。
   ```
   pip install -r requirements.txt
   ```
   - 開発中は編集可能にインストールするためにローカルインストールすることを推奨します。
   ```
   pip install -e .
   ```

4. 環境変数 / API キー
   - 実際に証券会社 API を使う場合は API キーや認証情報が必要です。安全に管理してください（`.env` / Vault 等を利用）。

---

## 使い方（基本）

現状はパッケージ初期化のみ行われています。まずはパッケージをインポートしてバージョン確認ができます。

例:
```python
import kabusys

print(kabusys.__version__)  # -> "0.1.0"
```

簡単な開発・拡張例（各モジュールの雛形を自分で実装する）：

- data モジュール例
```python
# src/kabusys/data/api.py
def fetch_price(symbol):
    # 実装: API 呼び出しして価格を返す
    return {"symbol": symbol, "price": 1234.5}
```

- strategy モジュール例
```python
# src/kabusys/strategy/simple.py
class SimpleStrategy:
    def generate_signal(self, price):
        # 実装: シグナルを返す (例: "buy", "sell", "hold")
        return "hold"
```

- execution モジュール例
```python
# src/kabusys/execution/executor.py
class OrderExecutor:
    def send_order(self, symbol, side, size):
        # 実装: 証券会社 API へ注文を送信
        return {"status": "ok", "order_id": "abc123"}
```

- monitoring モジュール例
```python
# src/kabusys/monitoring/logger.py
def log(message):
    print(message)
```

これらを組み合わせた簡単なランナー:
```python
from kabusys.data.api import fetch_price
from kabusys.strategy.simple import SimpleStrategy
from kabusys.execution.executor import OrderExecutor
from kabusys.monitoring.logger import log

price_info = fetch_price("7203")  # トヨタなどの銘柄コード例
strategy = SimpleStrategy()
signal = strategy.generate_signal(price_info["price"])

if signal == "buy":
    executor = OrderExecutor()
    res = executor.send_order("7203", "buy", 100)
    log(f"order result: {res}")
```

---

## ディレクトリ構成

現状のファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py         # パッケージメタ情報（__version__ 等）
    - data/
      - __init__.py       # データ取得関連モジュールを配置
    - strategy/
      - __init__.py       # 戦略実装を配置
    - execution/
      - __init__.py       # 注文実行ロジックを配置
    - monitoring/
      - __init__.py       # 監視・ロギングを配置

README やライセンス、テストフォルダ（tests/）などはプロジェクトルートに追加することを推奨します。

ツリー（簡略）
```
.
└─ src/
   └─ kabusys/
      ├─ __init__.py
      ├─ data/
      │  └─ __init__.py
      ├─ strategy/
      │  └─ __init__.py
      ├─ execution/
      │  └─ __init__.py
      └─ monitoring/
         └─ __init__.py
```

---

## 開発ガイドライン / 拡張ポイント

- モジュール単位で責務を分離する（データ取得、シグナル生成、注文実行、監視）。
- テストを充実させる（ユニットテスト、統合テスト）。API コールはモック化する。
- 設定は YAML/TOML/JSON 等で分け、環境変数で上書きできるようにする。
- 注文実行は必ず失敗時のリトライやエラーハンドリングを実装する。
- 実運用ではバックテスト機能、ドライラン（注文を送らないテスト）、履歴管理を用意する。

---

## 貢献

- バグ報告、機能提案、プルリクエスト歓迎です。
- コーディング規約（PEP8）に従い、テストを含めて PR を作成してください。

---

## ライセンス

現状 README はテンプレートです。ライセンスファイル（LICENSE）をプロジェクトルートに追加してください。例: MIT License。

---

必要であれば、具体的な API（kabu.com 等）との接続サンプルや、サンプル戦略、テンプレートの requirements.txt / pyproject.toml / setup.cfg を作成して提供します。どのような実装（接続先の証券会社、使用ライブラリ、戦略の種類）を想定するか教えてください。