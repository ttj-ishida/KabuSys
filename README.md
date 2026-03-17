# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
J-Quants や RSS などからマーケットデータ・ニュースを取得し、DuckDB に保存・整形、品質チェック、監査ログ、カレンダー管理、ETL パイプラインなどを提供します。

主な想定利用：
- データ収集（株価・財務・カレンダー・ニュース）
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- マーケットカレンダーの管理（営業日判定等）
- 監査ログ（シグナル → 発注 → 約定のトレース）
- DuckDB を中心としたデータレイク構築

---

## 機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX カレンダーの取得
  - レート制御（120 req/min）、リトライ、トークン自動リフレッシュ
  - 取得時刻（fetched_at）記録、DuckDB への冪等保存（ON CONFLICT）
- ニュース収集（RSS）
  - RSS フィード取得・前処理（URL除去・空白正規化）
  - URL 正規化・トラッキングパラメータ除去、ID（SHA-256）生成による冪等性
  - SSRF / XML Bomb 対策（スキーム検証、defusedxml、受信サイズ制限）
  - DuckDB へのバルク挿入（INSERT ... RETURNING）、銘柄抽出と紐付け
- ETL パイプライン
  - 差分取得（DB の最終日を参照）、バックフィル、品質チェック統合
  - run_daily_etl による一括実行（カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック
  - 欠損、異常値（スパイク）、重複、日付不整合の検出
  - QualityIssue データ構造で問題を集約
- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日リスト、SQ 日判定
  - DB データがない場合は曜日ベースでフォールバック
- 監査ログスキーマ
  - signal_events / order_requests / executions テーブル
  - 発注要求の冪等キー（order_request_id）、タイムスタンプは UTC 保存

---

## 動作要件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク通信（J-Quants API、RSS フィード）
- DuckDB をファイルで保存するディレクトリの書き込み権限

（実際のプロジェクトでは requirements.txt や pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / コピー
   - このパッケージは src/ 配下に入ったレイアウトを想定しています。

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Linux / macOS)
   - .venv\Scripts\activate (Windows)

3. インストール
   - pip install -e .
   - もしくは最低限の依存をインストール：
     - pip install duckdb defusedxml

4. 環境変数の設定
   - プロジェクトルートに .env もしくは .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードは無効化）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID
   - オプション:
     - KABUSYS_ENV — 実行環境: development / paper_trading / live（既定: development）
     - LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
     - DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（既定: data/monitoring.db）

例 .env（テンプレート）:
    JQUANTS_REFRESH_TOKEN=your_refresh_token
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    KABUSYS_ENV=development
    LOG_LEVEL=INFO
    DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（クイックスタート）

以下はライブラリを直接インポートして使う例です。通常はスクリプトやバッチから呼び出します。

1) スキーマ初期化（DuckDB）
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリがなければ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# 既存 DB に接続するだけなら:
# conn = schema.get_connection("data/kabusys.duckdb")
```

2) 日次 ETL の実行
```python
from kabusys.data import pipeline

# conn は schema.init_schema() で得た DuckDB 接続
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

主な引数:
- target_date: ETL 対象日（省略時は今日）
- id_token: J-Quants の id_token を注入可能（テスト用）
- run_quality_checks: 品質チェックの実行有無
- backfill_days: 差分取得時のバックフィル日数

3) RSS ニュース収集
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出に使う有効銘柄コードセット（例: {"7203", "6758", ...}）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set())
print(results)
```

4) マーケットカレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"保存件数: {saved}")
```

5) 監査ログスキーマの初期化（監査専用または既存接続へ追加）
```python
from kabusys.data.audit import init_audit_schema

# 既存 conn に監査テーブルを追加
init_audit_schema(conn)

# 監査専用 DB を作る場合:
# from kabusys.data.audit import init_audit_db
# audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 主要 API（モジュールと関数抜粋）

- kabusys.config
  - settings — 環境変数ベースの設定オブジェクト
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動 .env 読み込みを無効化可能

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
  - run_news_collection(conn, sources=None, known_codes=None)

- kabusys.data.pipeline
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(...)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - is_sq_day(conn, d)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## 注意点 / 実運用上の考慮

- 自動環境変数読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml の存在場所）を探索し、.env / .env.local を自動で読み込みます。テスト等で無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 認証トークン
  - J-Quants の id_token はモジュール内でキャッシュされ、自動リフレッシュが行われます。get_id_token は refresh token を使って取得します。

- リトライとレート制御
  - J-Quants へのリクエストはレート制御（120 req/min）およびリトライロジック（指数バックオフ、特定ステータスでの再試行）を備えています。

- DuckDB のタイムゾーン
  - 監査テーブルでは UTC を明示的に使用するため init_audit_schema は "SET TimeZone='UTC'" を実行します。タイムスタンプの取り扱いに注意してください。

- セキュリティ
  - ニュース取得では SSRF 防止、XML パースの安全化、受信サイズの上限などを実装しています。

---

## ディレクトリ構成

（抜粋 & 主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存）
    - news_collector.py               — RSS ニュース収集・保存・銘柄抽出
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - schema.py                       — DuckDB スキーマ定義・初期化
    - calendar_management.py          — マーケットカレンダー管理
    - quality.py                      — データ品質チェック
    - audit.py                        — 監査ログスキーマ（signal / order / execution）
  - strategy/
    - __init__.py                     — 戦略関連（将来的に拡張）
  - execution/
    - __init__.py                     — 発注/ブローカー連携（将来的に拡張）
  - monitoring/
    - __init__.py                     — 監視用モジュール（未実装 / 拡張部）

---

## 貢献 / 拡張

- 戦略や実際の発注ブリッジ（kabuステーション連携）部分は拡張ポイントです。strategy/、execution/ ディレクトリに機能を追加してください。
- テストでは環境変数の自動ロードを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）し、DuckDB を ":memory:" で利用すると良いでしょう。
- ESLint / linters や CI を導入して静的解析・型チェック (mypy) を行うと保守性が向上します。

---

README は以上です。必要であれば、導入用の例スクリプトや .env.example のテンプレート、依存パッケージ一覧（requirements.txt）を追加した README の拡張版を作成します。どの部分を詳しく出力しますか？