# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）の README。  
このリポジトリはデータ収集（J-Quants／RSS）、ETL パイプライン、DuckDB スキーマ、品質チェック、マーケットカレンダー管理、監査ログ（発注→約定トレーサビリティ）など、取引システムの基盤機能群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための基盤モジュール群です。主に以下を目的としています。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新）
- RSS からのニュース収集（正規化・SSRF対策・トラッキング除去）
- DuckDB を用いた 3 層データモデル（Raw / Processed / Feature）と実行層（orders/trades/positions）
- 日次 ETL パイプライン（差分更新、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（signal → order_request → executions のトレースが可能）

設計方針として、冪等性（ON CONFLICT の活用）、安全性（SSRF・XML攻撃対策）、可観測性（fetched_at、created_at、監査ログ）を重視しています。

---

## 主な機能一覧

- データ取得（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レートリミット（120 req/min）、指数バックオフ、401 自動 refresh（1 回）
  - DuckDB への冪等保存（save_daily_quotes 等）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、URL 正規化（utm_* 等除去）、記事 ID は SHA-256（先頭32文字）
  - defusedxml による XML パース（XML Bomb 対策）
  - SSRF 対策（リダイレクト先検査、プライベート IP 拒否）
  - raw_news / news_symbols への冪等保存（チャンク/トランザクション）

- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（init_schema）
  - インデックス作成、DuckDB 接続取得

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl：カレンダー→株価→財務→品質チェックの一括処理
  - 差分更新・backfill 対応、品質チェック統合（kabusys.data.quality）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、期間内営業日取得、calendar_update_job（夜間バッチ）

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のテーブル初期化（init_audit_schema / init_audit_db）
  - 発注フローのトレーサビリティ設計

- データ品質チェック（kabusys.data.quality）
  - 欠損検出、スパイク検出（前日比閾値）、重複、日付不整合チェック
  - QualityIssue により問題の一覧を返す（error / warning）

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションの union 型などを使用）
- Git リポジトリのルートに `.env` / `.env.local` を置くことで自動読み込みが働きます（後述）

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - duckdb
   - defusedxml
   例:
   - pip install duckdb defusedxml

   （ネットワーク操作は標準ライブラリ urllib を利用しているため、requests 等は必須ではありませんが、運用用に追加ライブラリがある場合は適宜）

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config の自動ロード）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（代表的なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN : Slack 通知に使用する Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）

任意（デフォルト値あり）
- KABU_API_BASE_URL : kabu ステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（モニタリングDB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

サンプル .env（参考）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（基本的な例）

以下は Python REPL / スクリプト内での簡単な利用例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数で指定されたパス（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)  # 既に init_schema で初期化済みを想定
result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# sources を省略するとデフォルトの RSS ソース（Yahoo Finance など）を使います
# known_codes があれば記事から銘柄抽出して news_symbols に紐付けます
known_codes = {"6758", "7203"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

4) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print("saved:", saved)
```

5) 監査ログ DB 初期化（監査専用 DB を分ける場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意点:
- J-Quants API 呼び出しは内部でレート制御・リトライ・トークン更新を行います。大量リクエスト時は設定を尊重してください。
- news_collector は外部 URL 取得時に SSRF 対策を行います。ローカルネットワークへのアクセスは拒否される場合があります。
- ETL は各ステップで例外を捕捉し、可能な限り処理を継続して結果を返す設計です。細かなエラー判定は ETLResult と QualityIssue で確認してください。

---

## 主要 API（抜粋）

- kabusys.config.settings
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(...)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - 各チェック: check_missing_data / check_spike / check_duplicates / check_date_consistency

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（取得・保存）
    - news_collector.py             -- RSS ニュース収集（SSRF 対策・正規化）
    - schema.py                     -- DuckDB スキーマ定義・初期化
    - pipeline.py                   -- ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py        -- マーケットカレンダー管理（営業日関数等）
    - audit.py                      -- 監査ログ（signal/order_request/executions）
    - quality.py                    -- データ品質チェック
  - strategy/                       -- 戦略層（空のパッケージ。戦略実装はここに配置）
    - __init__.py
  - execution/                      -- 発注/実行層（空のパッケージ）
    - __init__.py
  - monitoring/                     -- 監視/メトリクス（空のパッケージ）
    - __init__.py

---

## 運用上の注意 / ベストプラクティス

- 環境分離: KABUSYS_ENV によって開発 / ペーパー / ライブを切り替え、誤発注を防止してください。
- 秘密情報管理: トークンやパスワードは OS 環境変数や秘密管理ツールで管理し、リポジトリに平文で置かないでください。
- DB バックアップ: DuckDB ファイルは定期バックアップを推奨します。監査ログは消さない運用が前提です。
- テストと検証: ETL・発注ロジックはまず paper_trading 環境で十分に検証してください。
- レート制限: J-Quants のレート制限（120 req/min）を遵守してください。ライブラリは基礎制御を行いますが、利用側で過度の並列リクエストを行わないでください。

---

## 追加情報 / 拡張

- strategy / execution / monitoring はパッケージの枠のみ用意してあります。具体的な戦略、ポートフォリオ最適化、ブローカー統合（kabuステーション等）やモニタリングの実装はこの上に構築してください。
- 必要に応じて Slack 通知等を実装して ETL 結果や品質チェックアラートを送信できます（設定は settings.slack_* を利用）。

---

必要であれば、README にサンプルワークフロー（cron ジョブ、systemd タイマー、Docker-compose 例）、requirements.txt、CI 用テスト例の追記も対応します。どの追加情報が欲しいか教えてください。