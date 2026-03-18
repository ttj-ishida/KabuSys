# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
主にデータ収集・ETL、品質チェック、ニュース収集、DuckDB スキーマ管理、監査ログの初期化といった機能を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。J-Quants API や RSS を用いたデータ収集、DuckDB を用いたデータ永続化、データ品質チェック、マーケットカレンダー管理、監査ログ（発注〜約定のトレーサビリティ）などの機能を備えています。

設計上のポイント：
- API レート制限・リトライ（J-Quants）
- データ取得時の fetched_at による Look-ahead Bias 回避
- DuckDB への冪等保存（ON CONFLICT / DO UPDATE, DO NOTHING）
- RSS の SSRF 対策・XML安全パーシング
- 品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログの階層的トレーサビリティ（UUID連鎖）

---

## 主な機能一覧

- データ取得（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）: fetch_daily_quotes / save_daily_quotes
  - 財務データ（四半期 BS/PL）: fetch_financial_statements / save_financial_statements
  - JPX マーケットカレンダー: fetch_market_calendar / save_market_calendar
  - 認証用 get_id_token（リフレッシュ対応、401 時の自動リフレッシュ）

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード取得（gzip 対応・リダイレクト検査・受信サイズ制限）
  - 記事の正規化（URL トラッキング除去、ID は SHA-256 の先頭 32 文字）
  - DuckDB への冪等保存（raw_news、news_symbols）
  - 銘柄コード抽出（4 桁数値 + known_codes フィルタ）

- データスキーマ管理（src/kabusys/data/schema.py）
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(db_path) で初期化し接続を取得

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - run_daily_etl で市場カレンダー・株価・財務の差分取得、保存、品質チェックを実行
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別ジョブ

- カレンダー管理（src/kabusys/data/calendar_management.py）
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - calendar_update_job：夜間バッチで JPX カレンダー更新

- 品質チェック（src/kabusys/data/quality.py）
  - 欠損データ検出、スパイク検出、重複チェック、日付不整合チェック
  - run_all_checks でまとめて実行し QualityIssue オブジェクトを取得

- 監査ログ初期化（src/kabusys/data/audit.py）
  - init_audit_schema / init_audit_db による監査テーブル作成（UTC タイムゾーン固定）
  - signal_events / order_requests / executions などのテーブルを提供

- 設定管理（src/kabusys/config.py）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - Settings クラス経由で環境変数アクセス（必須キーは _require でチェック）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能

---

## 要件

- Python 3.10+
- 依存（主に）:
  - duckdb
  - defusedxml
- 実行環境により追加の HTTP/SSL ライブラリ等が必要となる場合があります。

（パッケージ化時に requirements.txt や pyproject.toml を用意してください）

---

## セットアップ手順

1. Python（3.10 以上）を用意する

2. リポジトリをクローン / コピーしてプロジェクトルートに移動

3. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (UNIX)
   - .venv\Scripts\activate     (Windows)

4. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （開発時）pip install -e .

5. 環境変数（.env）を用意する
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（デフォルト）。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

例: .env の最低限の項目例
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    KABU_API_PASSWORD=your_kabu_station_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C0123456789
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

注意: Settings で必須扱いになっているキーが未設定だと ValueError が発生します。

---

## 使い方（主な利用例）

以下は Python スクリプトから利用する基本例です。実際はアプリケーションコードに組み込んで使います。

1) DuckDB スキーマ初期化

```python
from kabusys.data import schema

# ファイルベース DB を初期化（親ディレクトリがなければ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（市場カレンダー、株価、財務、品質チェックを含む）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定しなければ今日
print(result.to_dict())
```

- run_daily_etl は内部で J-Quants への API 呼び出しを行います（jquants_refresh_token が必要）。
- J-Quants API のレート制限（120 req/min）を内部で尊重します。

3) ニュース収集ジョブ

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードセット（抽出に用いる）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

4) 監査テーブル初期化（発注/約定の監査ログ用）

```python
from kabusys.data.audit import init_audit_db

# 別 DB に監査ログを作ることも可能
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

5) 品質チェック単体実行

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

6) カレンダー更新バッチ

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

---

## 環境変数と設定

設定は環境変数（または .env / .env.local）を通して読み込まれます。主なキー:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 用パス（モニタリング等で使用）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動 .env 読み込みを無効化

Settings は kabusys.config.settings 経由で取得できます。

---

## ディレクトリ構成

リポジトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py               — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py     — J-Quants API クライアント（取得・保存）
      - news_collector.py     — RSS ニュース収集・保存
      - schema.py             — DuckDB スキーマ定義・初期化
      - pipeline.py           — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py— マーケットカレンダー管理
      - audit.py              — 監査ログの DDL/初期化
      - quality.py            — データ品質チェック
    - strategy/
      - __init__.py           — 戦略モジュール（拡張ポイント）
    - execution/
      - __init__.py           — 発注実行モジュール（拡張ポイント）
    - monitoring/
      - __init__.py           — 監視・メトリクス（拡張ポイント）
- pyproject.toml / setup.cfg / requirements.txt（該当する場合）

各モジュールは拡張を想定した設計になっており、strategy / execution / monitoring は実装を追加して利用します。

---

## 注意点・運用上のヒント

- J-Quants の API レート制限（120 req/min）や 401 リフレッシュの仕組み等を組み込んでいますが、運用時はさらにネットワークや API 使用状況に応じた監視を行ってください。
- DuckDB のファイルは同時書き込みに弱い点があるため、複数プロセスでの同時書き込みが発生する構成ではロックや排他を考慮してください。
- RSS の取得では SSRF や XML 関連攻撃を考慮した実装（defusedxml、リダイレクト検査、受信サイズ制限）になっていますが、運用側でも許可するソースの管理や頻度制御を行ってください。
- 品質チェックは Fail-Fast ではなく全件収集する方針です。ETL 実行後の戻り値（ETLResult）や品質結果を元に運用ルール（通知・再取得・人手対応）を決めてください。
- .env ファイルはプロジェクトルート（.git 又は pyproject.toml を基準）から自動読み込みされます。テスト等で自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

## 貢献

機能拡張（戦略、実行ブリッジ、監視ダッシュボード等）やテストの追加、ドキュメント改善を歓迎します。Issue / PR をお送りください。

---

以上が KabuSys の概要と使い方です。必要であればサンプルの CLI スクリプト、docker 化、CI 用のワークフロー例など追加ドキュメントも作成できます。どの部分を詳しく補足しますか？