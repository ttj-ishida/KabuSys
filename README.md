# KabuSys

日本株向けの自動売買プラットフォーム基盤ライブラリです。データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、DuckDB スキーマ管理、監査ログなど、トレーディングシステムのコア機能群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とするライブラリ群です。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得して DuckDB に保存
- RSS を使ったニュース収集と記事→銘柄紐付け
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日取得）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）を DuckDB に保持
- 実運用を考慮した設計（レートリミット、リトライ、SSRF 対策、メモリ/サイズ制限、冪等性）

設計上のポイント（簡潔）:
- J-Quants へのリクエストはレートリミット（120 req/min）とリトライを実装
- データの保存は冪等（ON CONFLICT）で上書き・重複排除
- ニュース収集は URL 正規化・トラッキング除去・SSRF 対策・gzip 制限あり
- すべての時間は UTC を基本（監査ログ等）

---

## 機能一覧

主要な機能（モジュール別）

- kabusys.config
  - 環境変数読み込み（.env, .env.local 自動ロード、無効化可能）
  - 必須設定の取得ラッパー（settings オブジェクト）
- kabusys.data.jquants_client
  - J-Quants API クライアント（株価日足・財務・マーケットカレンダー取得）
  - レートリミッタ、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB へ保存する save_* 関数（冪等）
- kabusys.data.news_collector
  - RSS 取得・パース・前処理（URL除去、正規化）
  - 記事ID を URL 正規化→SHA-256（先頭32文字）で生成
  - raw_news へ冪等保存、news_symbols への紐付け（チャンク挿入、トランザクション）
  - SSRF 対策・受信サイズ制限・XML 安全パーサ（defusedxml）
- kabusys.data.schema
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 用テーブル）
  - init_schema(), get_connection()
- kabusys.data.pipeline
  - 日次 ETL（calendar → prices → financials → 品質チェック）
  - 差分更新、バックフィル、品質チェック統合（ETLResult を返す）
- kabusys.data.calendar_management
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - 夜間カレンダー更新ジョブ（calendar_update_job）
- kabusys.data.quality
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - QualityIssue を返す設計（severity: error / warning）
- kabusys.data.audit
  - 監査ログ用テーブルと初期化（init_audit_schema / init_audit_db）

---

## 必要な環境 / 依存パッケージ

主な依存（プロジェクトに requirements.txt が無い場合の例）:

- Python 3.10+
- duckdb
- defusedxml

インストール例:
```bash
python -m pip install duckdb defusedxml
```

パッケージ配布がある場合は通常の pip インストール／開発インストールを行ってください（例: pip install -e .）。

---

## 環境変数（必須 / 主要）

必須（アプリ起動時に settings で参照されます）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID

任意・設定可能:

- KABUSYS_ENV — 環境: one of "development", "paper_trading", "live"（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視DB等に使う SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に 1 を設定

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml の親）から `.env` と `.env.local` を自動で読み込みます。
- 読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env のパース挙動:
- `export KEY=val` に対応、クォート・エスケープ、コメント処理などに配慮した実装です。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 必要なパッケージをインストール
   ```bash
   python -m pip install -r requirements.txt
   # requirements.txt がない場合:
   python -m pip install duckdb defusedxml
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` ファイルを作成するか、システム環境変数を設定してください。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. DuckDB スキーマを初期化
   - Python コンソールやスクリプトで次を実行:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ用スキーマを追加する場合:
     ```python
     from kabusys.data import audit
     audit.init_audit_schema(conn)
     # または専用 DB を作る:
     # conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（簡易例）

基本的な ETL の実行例（日次 ETL）:

```python
from kabusys.config import settings
from kabusys.data import schema, pipeline

# DB 初期化（初回のみ）
conn = schema.init_schema(settings.duckdb_path)

# 日次 ETL を実行（target_date を指定しないと今日が対象）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

ニュース収集の実行例:

```python
from kabusys.data import schema, news_collector

conn = schema.get_connection("data/kabusys.duckdb")
# sources を渡さないとデフォルト RSS を使用
res = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
print(res)  # source_name -> 新規保存件数
```

マーケットカレンダーの夜間更新ジョブ（例）:

```python
from kabusys.data import schema, calendar_management

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved calendar rows:", saved)
```

監査ログ利用例（order_requests / executions の初期化後に利用）:
- 監査用テーブルは audit.init_audit_schema(conn) によって作成してください。

ログレベルや実行モードの切替:
- settings.env (KABUSYS_ENV) を `development` / `paper_trading` / `live` に設定して挙動（実運用かテストか）を切替えられます。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（src 以下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理（settings）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + DuckDB 保存関数
    - news_collector.py             — RSS ニュース収集・DB 保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義 / init_schema
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        — カレンダー管理（営業日判定、更新ジョブ）
    - audit.py                      — 監査ログスキーマと初期化
    - quality.py                    — データ品質チェック
  - strategy/
    - __init__.py                   — 戦略層（拡張ポイント）
  - execution/
    - __init__.py                   — 発注 / ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py                   — 監視・メトリクス（拡張ポイント）

その他:
- pyproject.toml / setup.cfg 等（プロジェクトルート、.env 自動ロードの基準）

---

## 注意事項 / 運用上のポイント

- J-Quants の API レート制限（120 req/min）に厳密に従うよう実装されています。大量取得の際は注意してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト中などで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。
- ニュースの RSS 収集は外部 URL を取得するため、SSRF 対策・受信サイズ制限が組み込まれています。必要に応じてソースを検証して追加してください。
- DuckDB スキーマは冪等に作られます。既存 DB に対して安全に init_schema を呼べます。
- 品質チェックは Fail-Fast ではなく問題を列挙して返す設計です。ETL の継続／停止は呼び出し側で判断してください。
- 監査ログは UTC 保持を前提に設計されています（init_audit_schema は SET TimeZone='UTC' を実行します）。

---

## 拡張ポイント

- strategy / execution / monitoring パッケージは拡張向けに空のパッケージとして用意されています。実戦用の戦略実装、ブローカー統合、監視アラートなどをここに追加してください。
- ニュースソースの追加は data.news_collector.DEFAULT_RSS_SOURCES に URL を追加、または run_news_collection に sources 引数で指定できます。

---

README の内容やサンプルコードについて不明点があれば、どの使い方（ETL、ニュース収集、監査ログ、スキーマ定義など）を詳しく説明するか指示してください。必要に応じてサンプルスクリプトや unit test のテンプレートも作成します。