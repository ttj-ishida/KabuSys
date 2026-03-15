# KabuSys

日本株向けの自動売買（アルゴリズムトレーディング）用ライブラリ/フレームワークのコア部分です。データ層（DuckDB スキーマ）、環境設定管理、監査ログ（トレーサビリティ）など、戦略・発注の基盤となる機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした内部ライブラリ群です。

- 市場データ・財務データ・ニュースなどの永続化（DuckDB）
- 加工済みデータ・特徴量・AI スコアの管理
- シグナル生成から発注、約定までの監査トレーサビリティ
- 環境変数ベースの設定管理（.env 自動読み込み機能）
- 発注/戦略/監視のためのパッケージ構成（拡張ポイント）

このリポジトリはフレームワークのコア実装（スキーマ定義、設定読み込み、監査テーブル等）を含み、戦略や実際の発注ロジックは別モジュールで実装して利用します。

---

## 機能一覧

- 環境設定管理
  - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - export 形式、クォート・エスケープ・インラインコメント対応のパーサ
  - 必須設定取得（未設定の場合は例外）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化

- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス作成（クエリパターンを考慮）
  - init_schema / get_connection API
  - ":memory:" を使ったインメモリ DB に対応

- 監査ログ（data.audit）
  - シグナル→発注要求→約定 のトレーサビリティテーブル群
  - 冪等キー（order_request_id）設計、ステータス管理、UTC タイムゾーン保存
  - init_audit_schema / init_audit_db API

- パッケージ構成（拡張ポイント）
  - kabusys.strategy, kabusys.execution, kabusys.monitoring（将来的な戦略・発注・監視機能を想定）

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈 Path | None, union リテラルを使用）
- pip が利用可能

1. リポジトリをクローン / 作業ディレクトリへ移動

2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 最低限必要な依存: duckdb
   ```bash
   pip install duckdb
   ```
   （プロジェクトをパッケージ化している場合は `pip install -e .` を使って開発インストールできます。）

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml を含む場所）に `.env` または `.env.local` を置くと自動的に読み込まれます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu API のパスワード
   - SLACK_BOT_TOKEN: Slack ボットトークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   オプション:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   
   例（.env の最小例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   ```

---

## 使い方（基本例）

- 設定値の利用
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  base_url = settings.kabu_api_base_url
  is_live = settings.is_live
  ```

- DuckDB スキーマ初期化（永続 DB）
  ```python
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path を返します
  # conn は duckdb.DuckDBPyConnection
  ```

- DuckDB スキーマ初期化（インメモリ）
  ```python
  from kabusys.data.schema import init_schema

  conn = init_schema(":memory:")
  ```

- 既存 DB へ接続
  ```python
  from kabusys.data.schema import get_connection

  conn = get_connection(settings.duckdb_path)
  ```

- 監査ログの初期化（既存接続へ追加）
  ```python
  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn)
  ```

- 監査専用 DB を初期化して接続を得る
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

設定管理の挙動メモ:
- 自動読み込み順序: OS 環境 > .env.local > .env
- .env のパーサは export プレフィックス、クォート、バックスラッシュエスケープ、コメント（#）の取り扱いに対応
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

KABUSYS_ENV の許容値:
- development / paper_trading / live
LOG_LEVEL の許容値:
- DEBUG / INFO / WARNING / ERROR / CRITICAL

---

## ディレクトリ構成

プロジェクト内の主要なファイル・フォルダ構成（主要箇所）:

```
src/
  kabusys/
    __init__.py           # パッケージ初期化、__version__
    config.py             # 環境変数・設定管理
    data/
      __init__.py
      schema.py           # DuckDB スキーマ定義・初期化 (init_schema, get_connection)
      audit.py            # 監査ログスキーマ (init_audit_schema, init_audit_db)
      # ... (データ関連モジュール)
    strategy/
      __init__.py         # 戦略用パッケージ（拡張ポイント）
    execution/
      __init__.py         # 発注・実行関連パッケージ（拡張ポイント）
    monitoring/
      __init__.py         # 監視・メトリクス関連（拡張ポイント）
```

主要テーブル（抜粋）:
- Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
- Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature レイヤー: features, ai_scores
- Execution レイヤー: signals, signal_queue, orders, trades, positions, portfolio_performance
- 監査関連: signal_events, order_requests, executions (監査トレーサビリティ)

---

## 開発上の注意点

- DuckDB の初期化関数は冪等（既存テーブルがあればスキップ）です。既存データを破壊するものではありませんが、スキーマを更新する変更を行う場合は適切なマイグレーション方針を検討してください。
- 監査テーブルは削除しない前提で設計されています（ON DELETE RESTRICT など）。履歴を確実に残す運用を想定しています。
- タイムスタンプは監査スキーマで UTC に固定して保存します（init_audit_schema は `SET TimeZone='UTC'` を実行します）。
- order_request_id などの冪等キーを活用し、二重発注防止を行う設計になっています。

---

## 今後の拡張ポイント（例）

- strategy パッケージに戦略実装を追加
- execution パッケージにブローカー API 実装（kabu API 等）を追加
- monitoring でメトリクス収集・アラート・Slack 通知等を実装
- マイグレーションツール / バージョニングを導入してスキーマ変更を管理

---

必要に応じて README に含めたい追加情報（例: 実際の .env.example、依存パッケージ一覧、ライセンス、貢献ガイドなど）があれば指示してください。