# KabuSys

日本株向け自動売買基盤（KabuSys）の軽量ライブラリ。  
市場データ取得・前処理・特徴量生成・取引実行・モニタリングのための基盤的モジュール群を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムを構築するための基盤ライブラリです。  
- 環境設定管理（.env の自動読み込み、必須項目の検査）  
- DuckDB を用いた多層データスキーマ（Raw / Processed / Feature / Execution）定義と初期化  
- 戦略、実行、モニタリング用の名前空間（拡張用のプレースホルダ）

このリポジトリはコアとなるデータスキーマと設定管理に重点を置いており、戦略や実際の取引ロジックはこの上に実装します。

---

## 主な機能

- 環境変数管理
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml がある場所）から自動読み込み
  - 自動読み込み無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）
  - 必須項目未設定時に明確なエラーを返す Settings クラス
- DuckDB スキーマ
  - Raw / Processed / Feature / Execution の4層でテーブルを定義
  - 冪等なスキーマ初期化（init_schema）
  - インデックス定義、外部キー、制約を含む堅牢なDDL
- モジュール構成（拡張用）
  - data, strategy, execution, monitoring 用のパッケージプレースホルダ

---

## 必要環境

- Python 3.10 以上（型アノテーションの構文等に依存）
- duckdb Python パッケージ

（実際の運用では kabuステーション API や J-Quants、Slack などの外部サービス連携に対応するライブラリが別途必要になります）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール（最低限）
   ```
   pip install --upgrade pip
   pip install duckdb
   ```
   開発用途でパッケージとして扱う場合:
   ```
   pip install -e .
   ```
   （setuptools / pyproject 設定がある場合）

4. 環境変数の設定
   プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数が未設定の場合）。

   サンプル `.env`:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_api_password
   # KABU_API_BASE_URL は省略可能（デフォルト: http://localhost:18080/kabusapi）

   # Slack
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678

   # DB パス（オプション）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 動作環境（development / paper_trading / live）
   KABUSYS_ENV=development

   # ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
   LOG_LEVEL=INFO
   ```

   注意:
   - .env ファイルのパースは一般的なシェル形式をサポート（export PREFIX=val、クォート、コメント 等の基本処理）。
   - OS 環境変数が優先され、.env の上書きを許可するかは `.env.local` の使用や内部ロジックで制御されます。

---

## 使い方（基本例）

1. Settings を使って環境設定へアクセス
   ```python
   from kabusys.config import settings

   # 必須項目は未設定だと ValueError が発生します
   print("DuckDB path:", settings.duckdb_path)
   print("Is live:", settings.is_live)
   ```

2. DuckDB スキーマを初期化
   ```python
   from kabusys.data.schema import init_schema

   # settings.duckdb_path は .env の DUCKDB_PATH またはデフォルト (data/kabusys.duckdb)
   conn = init_schema(settings.duckdb_path)
   # conn は duckdb の接続オブジェクト（duckdb.DuckDBPyConnection）
   ```

3. 既存DBへの接続（スキーマの初期化はしない）
   ```python
   from kabusys.data.schema import get_connection
   conn = get_connection("data/kabusys.duckdb")
   ```

4. 開発フローの例
   - strategy パッケージに戦略ロジックを実装して features / signals を生成
   - execution モジュールで signal_queue→orders→trades のフローを実装
   - monitoring で portfolio_performance 等を集計して Slack に通知

（戦略・実行・モニタリングは本リポジトリの拡張点です）

---

## 環境変数の自動読み込み動作

- 自動読み込みは kabusys.config モジュールの読み込み時に行われます。
- 検索対象:
  - 現在モジュールの親ディレクトリから上へ辿り、最初に見つかった .git または pyproject.toml をプロジェクトルートとみなします。
  - そのプロジェクトルート内の `.env`（優先度低）および `.env.local`（優先度高）を読み込む。
- 無効化:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを行いません（テスト等で便利）。
- .env の取り扱い:
  - export 付き、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントなどの基本的な形式に対応。
  - 既存の OS 環境変数は保護され、.env による上書きは制御されます。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                    # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py                  # DuckDB スキーマ定義 & 初期化 API (init_schema, get_connection)
    - strategy/
      - __init__.py                # 戦略モジュール（実装はここに追加）
    - execution/
      - __init__.py                # 実行モジュール（実装はここに追加）
    - monitoring/
      - __init__.py                # モニタリング・収集用（実装はここに追加）

主要テーブル（DuckDB）:
- Raw Layer:
  - raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer:
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer:
  - features, ai_scores
- Execution Layer:
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

インデックスや制約もDDLに組み込まれており、頻出クエリに対応した設計です。

---

## 開発・運用に関する注意点

- settings のプロパティは必須項目を要求します。実行環境で必要な環境変数が揃っていることを確認してください（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
- DUCKDB に対するスキーマ初期化は冪等（既存テーブルはスキップ）です。初回起動時に init_schema を呼び出してください。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかを指定します。運用モードにより挙動（例: 実際の注文送信）を切り替えてください。
- 実際の取引接続（kabuステーション API など）や外部サービス連携はこの基盤の外側／上位モジュールで実装することを想定しています。セキュリティ（API鍵の保護等）に留意してください。

---

必要に応じて README を拡張します。戦略テンプレートや実行フロー（signal→order→trade）のサンプルを追加したい場合は、どの領域のサンプルを優先するか教えてください。