# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python パッケージです。J-Quants API や RSS フィードを用いたデータ収集、DuckDB によるデータ保管、ETL パイプライン、データ品質チェック、監査ログ（発注→約定トレース）などを備え、戦略レイヤや実行レイヤと連携できる基盤機能群を提供します。

主な特徴
- J-Quants API クライアント（株価日足 / 財務 / 市場カレンダー）  
  - レート制限（120 req/min）準拠（内部 RateLimiter）
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB 保存は冪等（ON CONFLICT … DO UPDATE）
- RSS ベースのニュース収集（ニュース → raw_news）
  - URL 正規化・トラッキングパラメータ除去 → SHA-256 による記事 ID
  - SSRF や XML Bomb、巨大レスポンス対策（defusedxml、ホスト検査、受信サイズ制限）
  - 銘柄コード抽出・news_symbols への紐付け（重複排除、トランザクション）
- DuckDB によるスキーマ管理（Raw / Processed / Feature / Execution 層）
  - スキーマ初期化ユーティリティ（init_schema）
  - 監査ログ用スキーマ（signal_events / order_requests / executions）と初期化
- ETL パイプライン（差分更新・バックフィル・品質チェック）
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 品質チェック（欠損・重複・スパイク・日付不整合）を収集して返す（Fail-fast なし）
- 監視・監査（監査テーブルによりシグナルから約定までの完全トレーサビリティを確保）

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（短いコード例）
- 環境変数
- ディレクトリ構成

プロジェクト概要
----------------
KabuSys は日本株のデータ収集・前処理・品質管理・監査ログを行う基盤ライブラリです。戦略（strategy）や実行（execution）モジュールと組み合わせて自動売買システムを構築するための土台を提供します。データ層は DuckDB を使用し、ETL と品質チェックを備えています。

機能一覧
--------
- J-Quants API クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
- DuckDB スキーマ定義と初期化（init_schema, init_audit_db）
- ETL パイプライン（run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl）
- データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
- ニュース収集（fetch_rss, save_raw_news, extract_stock_codes, run_news_collection）
- マーケットカレンダー管理（is_trading_day, next_trading_day, prev_trading_day, calendar_update_job）
- 環境設定管理（.env 読み込み、自動ロード、Settings オブジェクト）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化関数

セットアップ手順
----------------
前提
- Python 3.9+（コードは typing の Union 代替や型注釈を使用）
- 必要な主要ライブラリ: duckdb, defusedxml
  - その他の標準ライブラリ（urllib, json, logging, datetime 等）を使用

例: 仮想環境と依存インストール
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) または .venv\Scripts\activate (Windows)

2. pip で依存をインストール（プロジェクトに pyproject.toml があればそちらを利用）
   - pip install duckdb defusedxml

3. パッケージを編集可能モードでインストール（任意）
   - pip install -e .

環境変数（.env）
- プロジェクトルートに .env または .env.local を置くと、kabusys.config が自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 必要な変数は後述の「環境変数」セクションを参照。

使い方（基本例）
----------------

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ファイルを作成して初期化
```

2) 監査ログDB（監査専用）初期化（任意）
```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/audit.duckdb")
```

3) J-Quants トークン取得（設定ファイル/環境変数から取得）
```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を利用
```

4) 日次 ETL 実行（カレンダー→価格→財務→品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=None)  # target_date None で今日
print(result.to_dict())
```

5) RSS ニュース収集と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 既知の銘柄コードセット（抽出に利用）
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

6) マーケットカレンダー関連ユーティリティ例
```python
from kabusys.data import calendar_management as cm
from datetime import date
d = date(2024, 1, 1)
is_trading = cm.is_trading_day(conn, d)
next_day = cm.next_trading_day(conn, d)
```

環境変数（Settings）
-------------------
kabusys.config.Settings が参照する主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD     : kabuステーション API のパスワード
- SLACK_BOT_TOKEN       : Slack 通知用ボットトークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL     : kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 実行環境 (development | paper_trading | live). デフォルト: development
- LOG_LEVEL             : ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL). デフォルト: INFO

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動読み込みします。
- 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

ディレクトリ構成
----------------
以下は主なファイル・モジュールの構成（パッケージルート = src/kabusys）です:

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py              # 環境変数/設定読み込み（.env 自動ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py    # J-Quants API クライアント（取得 + DuckDB 保存ユーティリティ）
    - news_collector.py    # RSS 取得、正規化、保存、銘柄抽出
    - schema.py            # DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py          # ETL（差分取得・backfill・品質チェック・run_daily_etl）
    - calendar_management.py # 市場カレンダーの補助関数とバッチ更新ジョブ
    - audit.py             # 監査ログ用スキーマ（signal_events, order_requests, executions）と初期化
    - quality.py           # データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py          # 戦略関連（拡張ポイント）
  - execution/
    - __init__.py          # 発注実行関連（拡張ポイント）
  - monitoring/
    - __init__.py          # 監視用（将来的な拡張ポイント）

設計上の注意点 / 重要事項
-----------------------
- J-Quants API はレート制限が厳しい（120 req/min）。内部で RateLimiter により間隔調整していますが、大量の並列リクエストは避けてください。
- jquants_client は 401 応答時に自動でトークンをリフレッシュし 1 回リトライします（再帰無限ループ対策あり）。
- DuckDB への INSERT は冪等化（ON CONFLICT）を採用しています。外部からの直接挿入やスキーマ変更により重複が生じる可能性があるため、quality.check_duplicates などで検査できます。
- news_collector は SSRF・XML 攻撃・巨大レスポンス対策を実装しています。外部 RSS を取り込む際は既知の信頼できるソースを優先してください。
- audit.init_audit_db はタイムゾーンを UTC に固定します（SET TimeZone='UTC'）。

拡張ポイント
------------
- strategy / execution / monitoring パッケージに戦略ロジックやブローカ接続、監視ダッシュボードを実装して統合できます。
- Slack 通知や外部監視（Prometheus / Grafana）連携は、monitoring モジュールに実装可能です。
- DuckDB 外に監査用に別 DB（例: PostgreSQL）を追加する場合は audit モジュールを参考に移植できます。

サポート / 貢献
----------------
- バグ報告や機能提案は issue を通してお願いします（リポジトリに issue tracker がある想定）。
- コード貢献は PR を歓迎します。スタイルとテストを含めて送ってください。

以上。必要であれば、README にチュートリアル的なフロー（CI/CD、cron での日次 ETL 実行、Docker 化の例など）を追加できます。どの内容を優先して詳しく記述するか教えてください。