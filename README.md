# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム骨組みです。マーケットデータの蓄積（DuckDB）、特徴量生成、シグナル生成、発注管理、モニタリング等の基盤を提供することを目的としています。

バージョン: 0.1.0

---

## 概要

- DuckDB を用いたローカルデータベーススキーマ（Raw / Processed / Feature / Execution 層）を定義・初期化します。
- 環境変数ベースの設定管理を提供します（.env / .env.local の自動読み込みをサポート）。
- strategy, execution, data, monitoring といったモジュール構成を想定したパッケージ骨子です（各機能の実装は個別に拡張）。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動ロード（OS 環境変数より優先しない挙動）
  - 必須値取得メソッド（未設定時は ValueError を送出）
  - KABUSYS_ENV / LOG_LEVEL 等の検証
- データベース（DuckDB）
  - Raw / Processed / Feature / Execution の各レイヤー向けテーブル定義
  - インデックス作成
  - init_schema(db_path) による初期化（冪等）
- パッケージ構成（拡張ポイント）
  - kabusys.data: データ取得・ETL・スキーマ初期化
  - kabusys.strategy: 戦略実装領域
  - kabusys.execution: 発注ロジック・注文管理
  - kabusys.monitoring: モニタリング・ログ・外部通知（Slack 等）

---

## 前提（推奨環境）

- Python 3.10+
  - 型アノテーション（PEP 604 の Union 表記 Path | None）等を利用しているため Python 3.10 以上を想定しています。
- 依存パッケージ（最低限）
  - duckdb

（プロジェクトに requirements.txt がある場合はそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローンする
   ```bash
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell の場合は .venv\Scripts\Activate.ps1)
   ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb
   # その他必要なパッケージがある場合は個別にインストールしてください
   ```

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を作成してください。
   - 自動読み込みの挙動:
     - OS 環境変数 > .env.local > .env
     - テスト等で自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必要な環境変数の例:
     ```
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     KABUSYS_ENV=development   # development / paper_trading / live
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     ```
   - `.env.example` をプロジェクトに置いておくと環境準備が容易です（コード中のエラーメッセージで .env.example を参照する旨が示されています）。

---

## 使い方（簡単な例）

- 設定を参照する
  ```python
  from kabusys.config import settings

  print(settings.env)                  # 'development' / 'paper_trading' / 'live'
  print(settings.jquants_refresh_token)  # 未設定なら例外
  print(settings.duckdb_path)          # Path オブジェクト
  ```

- DuckDB スキーマを初期化する
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  # settings.duckdb_path には Path が返る（デフォルト: data/kabusys.duckdb）
  conn = init_schema(settings.duckdb_path)
  # conn は duckdb の接続オブジェクト（DuckDBPyConnection）
  ```

- 既存 DB に接続する（スキーマ初期化は行わない）
  ```python
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  ```

- 自動 .env ロードを無効化して手動で設定したい場合
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成

リポジトリ内の主要ファイル・ディレクトリ（抜粋）:

```
src/
  kabusys/
    __init__.py            # パッケージメタ情報 (version: 0.1.0)
    config.py              # 環境変数・設定管理
    data/
      __init__.py
      schema.py            # DuckDB スキーマ定義と init_schema()
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py
```

- data/schema.py に全テーブル（raw / processed / feature / execution 層）とインデックス、init_schema/get_connection が実装されています。
- config.py が .env 自動ロード（プロジェクトルート検出）、必須環境変数取得、設定プロパティを提供します。

---

## DuckDB スキーマ概要

テーブルは概念的に以下の層に分かれています。

- Raw Layer: 取得した未加工の外部データ（raw_prices, raw_financials, raw_news, raw_executions など）
- Processed Layer: 整形済みの市場データ（prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等）
- Feature Layer: 戦略 / AI 用の特徴量（features, ai_scores）
- Execution Layer: シグナル・注文・約定・ポジション・ポートフォリオ情報（signals, signal_queue, orders, trades, positions, portfolio_performance 等）

すべてのテーブルは init_schema() によって作成され、すでに存在する場合はスキップされます（冪等性）。

---

## 環境変数に関する補足

- 必須（コード中で _require() によって要求されるもの）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

- 任意・デフォルトあり
  - KABUSYS_ENV (default: development) — 有効値: development, paper_trading, live
  - LOG_LEVEL (default: INFO) — 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)

- 自動読み込みの振る舞い
  - プロジェクトルートは __file__ を起点に上位ディレクトリを探索し、.git または pyproject.toml を検出したディレクトリをルートとします。
  - 自動読み込みを停止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 開発メモ / 拡張ポイント

- strategy, execution, monitoring モジュールは拡張用の骨格になっているため、ここに戦略ロジック、発注ラッパ、モニタリングフロー（Slack 通知など）を実装します。
- DuckDB のスキーマは将来の拡張を想定しているため、DDL は schema.py にまとめられています。外部キーやインデックスの追加はこのファイルを通して行ってください。
- テスト時に .env に依存しないよう、KABUSYS_DISABLE_AUTO_ENV_LOAD を利用するか、テスト専用の .env.local を用意してください。

---

必要であれば README に以下を追加できます:
- 実行例（サンプルスクリプト）
- CI / テストの手順
- 依存関係の明細（requirements.txt の生成）
- ライセンス表記

追加希望があれば教えてください。