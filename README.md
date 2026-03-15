# KabuSys

日本株自動売買システムの骨組み（スキャフォールディング）です。本リポジトリはパッケージ構成と基本メタ情報のみを含む最小限の実装で、実際のデータ取得、売買ロジック、注文実行、モニタリング機能は各サブパッケージに実装していく想定です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買（アルゴリズムトレーディング）システム向けのパッケージ構成です。以下のコンポーネントを想定しており、各コンポーネントを実装・拡張することで自動売買システムを構築します。

- data: 市場データの取得・前処理（ティッカー、板情報、板寄せ、OHLC など）
- strategy: 売買戦略（シグナル生成、ポジション管理）
- execution: 注文送信・注文管理（API ラッパー、注文追跡、約定処理）
- monitoring: ログ・メトリクス・アラート（ダッシュボード、通知）

このリポジトリはパッケージの雛形（__init__.py を含む構成）を提供します。実際のアルゴリズムや外部 API の統合はこれをベースに実装してください。

---

## 機能一覧（想定）

現時点では骨組みのみですが、実装すべき代表的な機能は以下です。

- データ取得
  - 株価（時系列）取得
  - 板情報取得
  - 歴史的データの保存/読み込み
- 戦略
  - シグナル生成（移動平均、モメンタム等）
  - リスク管理、ポジションサイジング
- 実行
  - 注文送信（成行・指値）
  - 注文状態管理（未約定・部分約定・約定）
  - 再注文・キャンセル処理
- モニタリング
  - ログ出力
  - パフォーマンス計測（P&L、シャープレシオ等）
  - アラート（メール/Slack 等）

---

## セットアップ手順

推奨環境
- Python 3.8 以上

手順（開発環境での利用例）

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows (PowerShell): .\.venv\Scripts\Activate.ps1

3. 依存関係のインストール
   - 本リポジトリに pyproject.toml / setup.py があれば:
     - pip install -e .
   - まだパッケージ化されていない場合は、開発時は PYTHONPATH を通す方法:
     - Unix/macOS: export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
     - Windows (PowerShell): $env:PYTHONPATH = "$(pwd)\src;$env:PYTHONPATH"

4. 必要な追加ライブラリ（例）
   - requests / pandas / numpy / websockets など、実装に応じて pip で追加

---

## 使い方（基本）

パッケージは `src/kabusys` 配下にあり、最小限の初期化が行われています。まずはパッケージの存在確認とバージョン確認を行えます。

例: Python REPL / スクリプトでの確認
- バージョン表示:
  - python -c "import kabusys; print(kabusys.__version__)"
- 利用可能なサブパッケージ:
  - python -c "import kabusys; print(kabusys.__all__)"

各サブパッケージは実装を追加していくことで機能します。簡単な実装例（擬似コード）:

- data モジュールに関数を追加
  - src/kabusys/data/market.py
    - def fetch_price(ticker): ...

- strategy モジュールに戦略クラスを追加
  - src/kabusys/strategy/simple_ma.py
    - class SimpleMA: def generate_signal(...)

- execution モジュールに注文クライアントを追加
  - src/kabusys/execution/client.py
    - class ExecutionClient: def send_order(...)

- monitoring モジュールにロギング/メトリクスを追加
  - src/kabusys/monitoring/logging.py

使用例（擬似コード）
- from kabusys.data.market import fetch_price
- from kabusys.strategy.simple_ma import SimpleMA
- from kabusys.execution.client import ExecutionClient
- from kabusys.monitoring.logging import setup_logger

- price = fetch_price("7203")  # トヨタの例
- strat = SimpleMA(...)
- sig = strat.generate_signal(price)
- if sig == "BUY":
    client.send_order(ticker="7203", side="BUY", size=100)

注意: 上記は例示であり、実際に動作するには各モジュールの具体実装が必要です。

---

## ディレクトリ構成

現状のファイル構成（主要ファイルのみ）

- src/
  - kabusys/
    - __init__.py            # パッケージ初期化、__version__ を定義
    - data/
      - __init__.py
      # データ取得/前処理モジュールを置く場所
    - strategy/
      - __init__.py
      # 戦略ロジックを置く場所
    - execution/
      - __init__.py
      # 注文実行/APIクライアントを置く場所
    - monitoring/
      - __init__.py
      # ログ・監視関連を置く場所

README と LICENSE、テスト用ディレクトリなどを追加することを推奨します:
- README.md
- pyproject.toml / setup.cfg / setup.py（パッケージ化に必要）
- tests/（ユニットテスト）

---

## 開発ガイドライン（簡易）

- 各サブパッケージの責務を明確にする（data / strategy / execution / monitoring）
- 公開 API は各サブパッケージの __init__.py で整理する
- 単体テストを追加して振る舞いを保証する（pytest 等）
- 機密情報（API キー等）は環境変数または安全なシークレット管理を利用する

例: サブパッケージの __init__.py に API を追加する
- src/kabusys/data/__init__.py
  - from .market import fetch_price
  - __all__ = ["fetch_price"]

---

## 貢献・連絡

バグ報告、機能提案、プルリクエストは歓迎します。Issue を立てるか、プルリク時に詳細な説明を添えてください。

---

## ライセンス

プロジェクトのライセンスファイル（LICENSE）を追加してください。特に指定がない場合は明示的なライセンスを付与するまで社内・限定利用に留めてください。

---

このリポジトリは現在「骨組み」であり、実運用には各コンポーネントの具体実装、十分なテスト、リスク管理が必要です。必要があれば README に具体的な実装例や API 仕様テンプレートも追加できます。必要でしたら追加してほしい項目を教えてください。