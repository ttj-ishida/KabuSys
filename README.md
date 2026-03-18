# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants から市場データ（株価・財務・マーケットカレンダー）や RSS ニュースを取得し、DuckDB に冪等的に蓄積、品質チェック、ETL パイプライン、監査ログ（発注〜約定のトレーサビリティ）を提供します。

主な設計方針
- API レート制御・リトライ・トークン自動リフレッシュを備えた J-Quants クライアント
- DuckDB を用いた 3 層（Raw / Processed / Feature）スキーマ
- ニュース収集での SSRF 対策・XML 安全処理・トラッキングパラメータ除去
- ETL は差分更新（バックフィル含む）で冪等性を担保
- データ品質チェックを組み込み（欠損、スパイク、重複、日付不整合）

バージョン: 0.1.0

---

## 機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - トークン取得・自動リフレッシュ、呼び出しごとのレートリミットとリトライ
- DuckDB スキーマ定義・初期化（raw_prices / raw_financials / raw_news / market_calendar / features / signals / orders / executions など多数）
- ETL パイプライン
  - run_daily_etl: カレンダー→株価→財務→品質チェックの一括処理（差分＋バックフィル）
  - 個別 ETL (run_prices_etl / run_financials_etl / run_calendar_etl)
- ニュース収集モジュール
  - RSS フィード取得・前処理（URL 除去・空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）
  - SSRF 保護（スキーム検証・プライベートIP拒否・リダイレクト検査）
  - raw_news / news_symbols への冪等保存（チャンク処理・トランザクション）
  - 銘柄コード抽出（4 桁数字・既知コードフィルタ）
- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出（前日比）、重複チェック、日付整合性チェック
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルによる発注〜約定のトレース
  - UTC タイムゾーン固定、冪等キー（order_request_id / broker_execution_id）など

---

## セットアップ手順

前提
- Python 3.10+（typing の一部を使用）
- DuckDB（Python パッケージ duckdb）
- defusedxml（RSS 安全パース用）

インストール例（プロジェクトルートで）
1. 仮想環境作成・有効化（任意）
2. 必要パッケージをインストール
   - pip install duckdb defusedxml

（パッケージ化されていれば）ローカルインストール:
   - pip install -e .

環境変数
- このライブラリは .env / .env.local（プロジェクトルートに .git or pyproject.toml があると自動読み込み）および OS 環境変数を参照します。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（必須は明示）
- JQUANTS_REFRESH_TOKEN  (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL      (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN        (必須) — Slack 通知用（本プロジェクトで利用する場合）
- SLACK_CHANNEL_ID       (必須) — Slack チャンネル ID
- DUCKDB_PATH            (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH            (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV            (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL              (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

サンプル .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易ガイド）

1) DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイル作成とテーブル作成を行う
```
- ":memory:" を渡すとインメモリ DB が使えます。

2) 日次 ETL の実行（J-Quants から差分取得して保存・品質チェック）
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```
- ETL は market_calendar → prices → financials → 品質チェック の順で実行します。
- id_token を引数で注入可能（テスト用）。省略時は内部キャッシュと settings.jquants_refresh_token を使用。

3) ニュース収集ジョブ
```
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に使う既知の銘柄コードセット（例: {"7203","6758",...}）
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: 新規挿入件数, ...}
```
- fetch_rss / save_raw_news / save_news_symbols を個別に呼んでカスタム処理も可能。
- HTTP リクエストの挙動をテストしたい場合、news_collector._urlopen をモックできます。

4) J-Quants の直接利用例
```
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings から refresh token を読みトークンを取得
records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
```
- クライアントは 120 req/min のレート制御、リトライ、401 自動リフレッシュを備えます。
- ページネーション対応で pagination_key を使って全件取得します。

5) 監査スキーマの初期化（監査専用 DB を作る場合）
```
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```
- init_audit_db は UTC タイムゾーンを設定し、監査テーブル群を作成します。

---

## 主要 API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.kabu_api_base_url, settings.env, settings.log_level など

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB connection
  - get_connection(db_path)

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
  - save_raw_news(conn, articles) -> list[new_ids]
  - save_news_symbols(conn, news_id, codes) -> int
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30) -> dict

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5) -> list[QualityIssue]

- kabusys.data.calendar_management
  - is_trading_day(conn, d), next_trading_day(conn, d), prev_trading_day(conn, d), get_trading_days(conn, start, end), calendar_update_job(conn)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成

プロジェクトの主要ファイル（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py            — RSS ニュース収集と DB 保存（SSRF 対策等）
    - pipeline.py                  — ETL パイプライン（差分取得・品質チェック）
    - schema.py                    — DuckDB スキーマ定義・初期化
    - calendar_management.py       — カレンダー更新・営業日判定ロジック
    - audit.py                     — 監査ログテーブル定義・初期化
    - quality.py                   — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py                  — 戦略用モジュール（拡張ポイント）
  - execution/
    - __init__.py                  — 発注・実行管理モジュール（拡張ポイント）
  - monitoring/
    - __init__.py                  — 監視・アラート用（拡張ポイント）

README に含まれないが主要な実装ポイント:
- J-Quants のレート制御は固定間隔スロットリング（_RateLimiter）
- ニュース ID は正規化 URL の SHA-256（先頭 32 文字）
- 多くの DB 保存関数は ON CONFLICT DO UPDATE / DO NOTHING を使用し冪等性を確保
- テスト容易性のため id_token 注入や _urlopen の差し替えをサポート

---

## 運用・トラブルシュートメモ

- 環境変数が見つからない場合、settings のプロパティは ValueError を投げます。例: settings.jquants_refresh_token
- 自動 .env 読み込みはプロジェクトルートの検出に .git または pyproject.toml を使用します。CI などで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使ってください。
- J-Quants のレート制限（120 req/min）を超えると 429 を受け取り Retry-After ヘッダでバックオフします。クライアントは指数バックオフとリトライを行いますが、短時間に大量リクエストを行わない運用設計を推奨します。
- news_collector は外部 URL をフェッチするため、ネットワークの到達性やファイアウォール設定に注意してください。内部アドレスや非 http/https スキームは拒否されます。
- DuckDB ファイルのバックアップ・権限管理を適切に行ってください。大規模データではファイルサイズが増大します。

---

## 開発者向けノート

- strategy / execution / monitoring モジュールは拡張ポイントとして用意されています。戦略ロジック・発注ロジック・監視ロジックはここに実装してください。
- 単体テストでは settings の自動ロードを無効化し、明示的に環境変数を注入するか、モックを利用してください。
- news_collector._urlopen や jquants_client の id_token 注入（get_id_token 引数）により外部依存を差し替えてテスト可能です。

---

必要であれば以下も提供します:
- requirements.txt / poetry/pyproject.toml の雛形
- .env.example のテンプレートファイル
- 具体的な ETL スケジュール・systemd / cron / Airflow 連携例

ほかに README に追記したい使い方や、運用ガイド（例: cron ジョブ例、Slack 通知の使い方等）があれば教えてください。