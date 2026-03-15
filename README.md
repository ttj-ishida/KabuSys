# KabuSys

日本株向けの自動売買基盤（ライブラリ）です。マーケットデータの永続化（DuckDB）、特徴量/AIスコア管理、シグナル→発注→約定の監査ログを想定したスキーマ、および環境設定管理を提供します。戦略・実行ロジックはプラグイン的に実装できる設計です。

主な目的:
- データレイク（Raw / Processed / Feature / Execution 層）を DuckDB で構築
- 発注フローの監査（トレーサビリティ）を DuckDB に保存
- 環境変数／.env の安全な読み込みと設定アクセス

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルートを自動検出）
  - 必須値取得時に未設定なら例外を発生
  - KABUSYS_ENV, LOG_LEVEL 等の検証

- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - init_schema(db_path) による冪等な初期化
  - get_connection(db_path) による接続取得

- 監査ログ（data.audit）
  - シグナル生成 → 発注要求 → 約定までの履歴を残す監査テーブル
  - 冪等キー／ステータス管理、UTC タイムゾーン設定
  - init_audit_schema(conn) / init_audit_db(db_path)

- パッケージ構造（拡張ポイント）
  - strategy, execution, monitoring などのサブパッケージ（プレースホルダ）を用意

---

## 動作要件

- Python 3.10 以上（型アノテーションに Union 演算子 `|` を使用）
- duckdb Python パッケージ

必要に応じて他の依存が追加される可能性があります（例: Slack 通知等）。

---

## セットアップ手順

1. リポジトリをクローンまたはプロジェクト配布を取得

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール（最低限）
   ```
   pip install duckdb
   ```

   プロジェクトをパッケージとしてインストールする場合:
   ```
   pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと、自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

   必須となる主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN — Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID — 通知先 Slack チャネル ID（必須）

   任意／デフォルト値
   - KABUSYS_ENV — environment（development / paper_trading / live） default: development
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...） default: INFO
   - KABU_API_BASE_URL — kabu API のベース URL（default: http://localhost:18080/kabusapi）
   - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
   - SQLITE_PATH — SQLite（monitoring 用）パス（default: data/monitoring.db）

   .env の書き方の例（.env.example を作る際の例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単な例）

- 設定値へアクセスする
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  if settings.is_live:
      print("ライブルール適用")
  ```

- DuckDB スキーマを初期化する
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  # ファイルパスまたは ":memory:"（インメモリ）を指定可能
  conn = init_schema(settings.duckdb_path)
  # これで全テーブルとインデックスが作成されます（冪等）
  ```

- 監査ログテーブルを既存接続に追加する
  ```python
  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn)
  # 監査ログ向けのテーブルとインデックスが作成されます
  ```

- 監査専用 DB を初期化して接続を得る
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/kabusys_audit.duckdb")
  ```

- 既存 DB に接続する（スキーマ初期化は行わない）
  ```python
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  ```

注意点:
- init_schema はテーブル作成（DDL）を行いますが、既存データの移行等は行いません。
- すべての TIMESTAMP は監査ログ初期化時に UTC に設定されます（init_audit_schema が SET TimeZone='UTC' を実行します）。
- .env パーサはシンプルなルールに従っており、クォートやコメントの扱いに配慮しています。詳細は kabusys.config モジュールの実装を参照してください。

---

## ディレクトリ構成

以下は主要なファイル・モジュールの構成（抜粋）です:

- src/kabusys/
  - __init__.py                — パッケージ定義（version 等）
  - config.py                  — 環境変数／設定管理（自動 .env ロード、Settings クラス）
  - data/
    - __init__.py
    - schema.py                — DuckDB のスキーマ定義と init_schema / get_connection
    - audit.py                 — 監査ログ（signal/events/order_requests/executions）定義と初期化
    - audit.py                 — 監査ログ初期化ユーティリティ
    - (その他: audit/monitoring 含める想定)
  - strategy/
    - __init__.py              — 戦略を実装するためのプレースホルダ
  - execution/
    - __init__.py              — 発注・ブローカー連携用のプレースホルダ
  - monitoring/
    - __init__.py              — モニタリング / メトリクス用プレースホルダ

主な SQL テーブル（抜粋）
- Raw 層: raw_prices, raw_financials, raw_news, raw_executions
- Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature 層: features, ai_scores
- Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- 監査ログ: signal_events, order_requests, executions（audit 用）

---

## 開発・テスト時の補足

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。配布パッケージやテストで一意に制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env パーサはシンプルな実装です。複雑なエスケープやシェル拡張は期待されません。必要に応じて .env の整形を行ってください。
- DuckDB ファイルの親ディレクトリが存在しない場合、init_* 関数は自動でディレクトリを作成します。

---

## 今後の拡張案（参考）

- broker コネクタ（複数ブローカー対応）
- 実行エンジン（注文の再試行、部分約定ハンドリング）
- バックテスト/シミュレーション用の時系列データ API
- Slack / Prometheus 等の監視・アラート連携

---

この README はコードベースの現状（schema, audit, config の設計）を元に作成しています。詳細な API や追加機能は今後のコミットで拡張される想定です。質問やドキュメントの追加要望があれば教えてください。