# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants API や RSS 等から市場データ・財務データ・ニュースを収集し、DuckDB に保存、ETL（差分更新）・データ品質チェック・マーケットカレンダー管理・監査ログ（発注→約定トレーサビリティ）機能を提供します。

---

## 主な特徴

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - API レート制限（120 req/min）を守る RateLimiter 実装
  - 冪等性（DuckDB への ON CONFLICT 更新）
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して look-ahead bias を防止

- ETL パイプライン
  - 差分更新（DB の最終取得日を基に自動算出）
  - backfill による後出し修正の吸収
  - 市場カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損・重複・スパイク・日付不整合を検出）

- ニュース収集
  - RSS フィード収集・前処理・DuckDB 保存（raw_news）
  - URL 正規化（utm 等削除）、記事ID を SHA-256 で生成（先頭32文字）
  - SSRF 対策、受信サイズ上限、gzip 解凍の安全対策
  - 銘柄コード抽出と news_symbols テーブルへの紐付け

- マーケットカレンダー管理
  - JPX カレンダー差分更新ジョブ（カレンダー未取得時の曜日フォールバックあり）
  - 営業日判定、前後の営業日取得、期間の営業日リスト取得

- 監査ログ（Audit）
  - signal → order_request → executions へと UUID ベースでトレース可能
  - order_request_id を冪等キーとして二重発注防止
  - テーブル初期化ユーティリティ（UTC タイムゾーン固定オプションあり）

- データ品質チェック
  - 欠損値、主キー重複、前日比スパイク、将来日付 / 非営業日データ検出
  - QualityIssue を返し、重大度に応じたハンドリングが可能

---

## 必要条件 / 依存ライブラリ

（導入環境に応じて適宜インストールしてください）

- Python 3.9+
- duckdb
- defusedxml

例（pip）:
```
pip install duckdb defusedxml
```

---

## セットアップ

1. レポジトリをチェックアウト／インストール

   （パッケージ化されている場合は pip install -e . など）

2. 環境変数 / .env ファイル設定

   必須の環境変数（少なくとも以下を設定）:

   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード
   - SLACK_BOT_TOKEN       : Slack Bot トークン（通知等で利用する場合）
   - SLACK_CHANNEL_ID      : Slack チャネル ID

   任意 / デフォルトあり:

   - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL   : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動 .env ロードを無効化

   自動ロードの優先順: OS 環境変数 > .env.local > .env  
   （パッケージはプロジェクトルートを .git または pyproject.toml を基準に探索します）

---

## 初期化（DuckDB スキーマ）

DuckDB スキーマを初期化して接続を取得します。

Python 例:
```python
from kabusys.config import settings
from kabusys.data import schema

conn = schema.init_schema(settings.duckdb_path)
```

- init_schema(db_path) はテーブル群とインデックスを冪等的に作成します。
- ":memory:" を渡すとインメモリ DB を使用可能です。

監査ログ専用 DB を初期化する場合:
```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

または既存接続に監査スキーマを追加:
```python
audit.init_audit_schema(conn, transactional=True)
```

---

## ETL（データパイプライン）の使い方

日次 ETL を実行する例:
```python
from datetime import date
from kabusys.config import settings
from kabusys.data import schema, pipeline

conn = schema.init_schema(settings.duckdb_path)
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

run_daily_etl の主なオプション:
- id_token: 明示的に J-Quants トークンを渡せます（テスト用）
- run_quality_checks: True/False（デフォルト True）
- spike_threshold: スパイク検出閾値（デフォルト 0.5）
- backfill_days: 差分再取得のバックフィル日数（デフォルト 3）
- calendar_lookahead_days: カレンダー先読み（デフォルト 90）

個別ジョブ（価格 / 財務 / カレンダー）も実行できます:
- run_prices_etl(conn, target_date, ...)
- run_financials_etl(conn, target_date, ...)
- run_calendar_etl(conn, target_date, ...)

---

## ニュース収集（RSS）

RSS を取得して raw_news に保存し、銘柄紐付けも行えます。

例:
```python
from kabusys.data import news_collector, schema

conn = schema.init_schema(settings.duckdb_path)
sources = {"yahoo": "https://news.yahoo.co.jp/rss/categories/business.xml"}
known_codes = {"7203", "6758", ...}  # 銘柄コードセット
results = news_collector.run_news_collection(conn, sources=sources, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

ニュース収集のポイント:
- URL のスキームは http/https のみ許可
- リダイレクト先のホストがプライベートアドレスの場合は拒否（SSRF 対策）
- 受信サイズは MAX_RESPONSE_BYTES（10MB）で制限
- 記事 ID は正規化 URL の SHA-256（先頭 32 文字）
- DuckDB への保存はトランザクション化され、挿入された ID のみを返す

---

## マーケットカレンダー管理

夜間更新ジョブ:
```python
from kabusys.data import calendar_management

saved = calendar_management.calendar_update_job(conn)
print(f"saved: {saved}")
```

マーケットカレンダーAPI を使った以下のユーティリティあり:
- is_trading_day(conn, date)
- is_sq_day(conn, date)
- next_trading_day(conn, date)
- prev_trading_day(conn, date)
- get_trading_days(conn, start, end)

カレンダーが未取得の場合は土日フォールバックで判定します。

---

## 品質チェック（Quality）

ETL 後に品質チェックを実行する場合:
```python
from kabusys.data import quality

issues = quality.run_all_checks(conn, target_date=None, reference_date=None)
for issue in issues:
    print(issue)
```

返される QualityIssue はチェック名・重大度・サンプル行などを含みます。呼び出し側で重大度に応じた対応（停止、通知など）を行ってください。

---

## 監査ログ（Audit）について

監査テーブルは signal_events, order_requests, executions を提供し、
発注から約定までのフローを UUID ベースで完全にトレースできます。

- init_audit_db(db_path) : 監査専用データベースを作成してスキーマ初期化
- init_audit_schema(conn, transactional=False) : 既存 DuckDB へ監査スキーマを追加

設計上、タイムスタンプは UTC に固定されます（init_audit_schema が SET TimeZone='UTC' を実行）。

---

## 設定管理の挙動

- .env の自動読み込み:
  - パッケージ初期化時にプロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動読み込みします。
  - 読み込み順序: OS 環境変数 > .env.local (override=True) > .env (override=False)
  - 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- .env の構文:
  - コメント行（#）、export KEY=val 形式に対応
  - シングル/ダブルクォート内のエスケープに対応
  - インラインコメントの認識はクォートの有無で異なる（詳細は実装に準拠）

- Settings API:
  - kabusys.config.settings から設定を取得できます（プロパティで環境変数をラップ）
    - settings.jquants_refresh_token
    - settings.kabu_api_password
    - settings.kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - settings.slack_bot_token
    - settings.slack_channel_id
    - settings.duckdb_path, sqlite_path
    - settings.env, settings.log_level, settings.is_live, settings.is_paper, settings.is_dev

---

## 主要モジュール一覧（ディレクトリ構成）

src/kabusys/
- __init__.py                         (パッケージ定義、バージョン)
- config.py                           (環境変数 / 設定ロード)
- data/
  - __init__.py
  - jquants_client.py                  (J-Quants API クライアント、保存ロジック)
  - news_collector.py                  (RSS 収集・前処理・保存・銘柄抽出)
  - pipeline.py                        (ETL パイプライン / run_daily_etl 等)
  - calendar_management.py             (市場カレンダー管理)
  - schema.py                          (DuckDB スキーマ定義・初期化)
  - audit.py                           (監査ログスキーマ・初期化)
  - quality.py                         (データ品質チェック)
- strategy/
  - __init__.py                         (戦略関連モジュール置き場)
- execution/
  - __init__.py                         (発注・実行関連モジュール置き場)
- monitoring/
  - __init__.py                         (監視・メトリクス系置き場)

---

## 例: よく使うワークフロー（まとめ）

1. 環境変数を設定（.env を作成）
2. DB 初期化:
   - schema.init_schema(settings.duckdb_path)
   - audit.init_audit_schema(conn)（必要に応じて）
3. 日次 ETL 実行:
   - pipeline.run_daily_etl(conn)
4. ニュース収集:
   - news_collector.run_news_collection(conn, known_codes=...)
5. 品質チェック・監査ログを確認し、必要に応じてアラート・オペレーションを行う

---

## 補足 / 注意点

- 実際の発注・約定処理、kabu ステーションとの接続・ハンドリングは execution モジュールで扱う想定ですが、本リポジトリに含まれるコードは主にデータ基盤・収集・監査周りの基盤実装です。
- J-Quants API の利用規約・レート制限に従ってご利用ください。
- DuckDB に対する SQL はプレースホルダ（?）を使っている箇所が多く、SQL インジェクション対策が施されていますが、外部から受け取ったパラメータの取り扱いには常に注意してください。

---

もし README に追加したい利用例や CLI、CI の手順、あるいは strategy / execution の具体的な実装例（モック）などの追記が必要であれば教えてください。