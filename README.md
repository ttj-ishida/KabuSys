# KabuSys

KabuSysは、日本株の自動売買システム向けに設計されたシンプルなPythonパッケージの骨組みです。データ取得、売買ロジック（ストラテジー）、発注処理、監視機能をサブパッケージとして分離しており、カスタム実装を追加して利用できるようになっています。

バージョン: 0.1.0

---

## 概要

このリポジトリは、自動売買システムを構築するための基本的なモジュール構成を提供します。各モジュールは責務ごとに分離されており、実際の取引所APIやデータソースに合わせて実装を差し替えたり拡張したりできます。

主な想定用途:
- 株価データの取得／整形
- 売買シグナルの生成（ストラテジー）
- 注文の発行・管理（発注エンジン）
- 動作監視・ロギング・アラート

---

## 機能一覧

現状はパッケージの骨組みのみを提供します。将来的に以下の機能を想定／実装できます。

- data
  - 株価・板情報の取得（リアルタイム・履歴）
  - データキャッシュ／前処理機能
- strategy
  - 売買アルゴリズム（シグナル生成）
  - バックテスト用のユーティリティ
- execution
  - 注文発行／取消し／注文状態監視
  - 取引所（API）クライアントラッパー（例: kabu API）
- monitoring
  - ログ、メトリクス収集（例: Prometheus, Sentry等）
  - アラート・通知（Slack, Email等）

このREADMEはテンプレートとして、具体的なロジックや外部依存はプロジェクトに合わせて実装してください。

---

## セットアップ手順

以下はローカルで開発／実行するための基本的な手順例です。

前提:
- Python 3.8+
- Git

1. リポジトリをクローン
   ```
   git clone <リポジトリのURL>
   cd <リポジトリ名>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - 本テンプレートでは requirements.txt がありません。必要なライブラリがある場合は `requirements.txt` を作成して以下を実行してください:
     ```
     pip install -r requirements.txt
     ```
   - 開発中にパッケージとして参照する場合:
     ```
     pip install -e .
     ```
     （setuptools / pyproject.toml があることを想定）

4. 環境変数 / 設定
   - 実際のAPIキーや接続情報（例: kabu APIのトークン）は環境変数や設定ファイルで管理してください。
   - 例:
     ```
     export KABU_API_TOKEN="your_token_here"
     ```

---

## 使い方（簡単な例）

パッケージをインポートし、基本情報を確認する例:

```python
import kabusys

print(kabusys.__version__)  # 0.1.0

# サブパッケージ（実装を追加して利用）
import kabusys.data
import kabusys.strategy
import kabusys.execution
import kabusys.monitoring
```

各サブパッケージの想定利用例（擬似コード）:

- データ取得
```python
from kabusys.data import DataClient

data_client = DataClient(api_key="...")
ohlcv = data_client.get_historical(symbol="7203.T", period="daily", limit=100)
```

- ストラテジーでシグナル生成
```python
from kabusys.strategy import Strategy

strategy = Strategy(params={...})
signal = strategy.generate(ohlcv)
if signal == "BUY":
    # 発注処理へ
    pass
```

- 発注（実際の取引APIラッパーを実装してください）
```python
from kabusys.execution import ExecutionClient

exec_client = ExecutionClient(api_key="...")
order = exec_client.send_order(symbol="7203.T", side="BUY", qty=100, price=None)
```

- 監視・アラート
```python
from kabusys.monitoring import Monitor

monitor = Monitor(config={...})
monitor.record_metric("strategy.signal", 1)
monitor.alert("order_failed", {"order_id": 123})
```

※ 上記クラス（DataClient, Strategy, ExecutionClient, Monitor）はテンプレートの想定であり、実装は各自で追加してください。

---

## ディレクトリ構成

現在の最小ファイル構成は以下のとおりです:

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py           # パッケージメタ情報（バージョン等）
│     ├─ data/
│     │  └─ __init__.py        # データ取得関連モジュール（未実装）
│     ├─ strategy/
│     │  └─ __init__.py        # 売買ロジック（未実装）
│     ├─ execution/
│     │  └─ __init__.py        # 注文発行・取引APIラッパー（未実装）
│     └─ monitoring/
│        └─ __init__.py        # ロギング・監視関連（未実装）
└─ README.md
```

---

## 開発・拡張のヒント

- 各サブパッケージ内にインターフェース（抽象クラス）を定義し、実際の実装クラスを分離するとテストや差し替えが容易になります。
- 取引や発注処理を実装する際は、必ずテスト環境（サンドボックス）を使用し、誤発注対策（チェック、フェイルセーフ）を入れてください。
- ロギングとメトリクスは早めに設計しておくと運用が楽になります（例: structured logging、Prometheus Exporter）。
- セキュリティ: APIキーは直接コードに書かない。環境変数や秘密管理ツールを利用してください。

---

## ライセンス・貢献

このリポジトリには現時点でライセンスファイルが含まれていません。公開・共有する場合は適切なライセンス（MIT, Apache 2.0等）を追加してください。

コントリビュートする場合は、IssueやPull Requestで目的・変更点を明示してください。

---

以上がこのプロジェクトのREADMEテンプレートです。実際の自動売買機能を実装する際は、取引所の仕様と法令・リスク管理を十分に理解した上で開発・運用してください。