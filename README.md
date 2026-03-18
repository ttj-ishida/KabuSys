# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリです。データ収集（J‑Quants）、DuckDB によるデータ格納・スキーマ管理、ETL パイプライン、ニュース収集、品質チェック、ファクター計算（リサーチ）や監査ログ管理などの基盤機能を提供します。

---

## 主要機能

- J‑Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レート制限（120 req/min）遵守、リトライ・トークン自動リフレッシュ、ページネーション対応
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution 層のテーブルとインデックスを定義
  - 監査ログ（audit）テーブルの初期化
- ETL パイプライン
  - 差分更新（backfill 対応）、市場カレンダー先読み、品質チェックを含む日次 ETL
  - 個別ジョブ（prices / financials / calendar）を分離して実行可能
- ニュース収集
  - RSS フィードの取得、前処理、DuckDB への冪等保存、銘柄抽出（4桁コード）
  - SSRF・XML Bomb 等のセキュリティ対策を実装
- データ品質チェック
  - 欠損、重複、スパイク（急騰/急落）、日付整合性チェック
- リサーチ（特徴量・ファクター計算）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー
  - Z スコア正規化ユーティリティ
- マーケットカレンダー管理
  - 営業日判定、前後営業日の取得、夜間バッチ更新ジョブ
- 設定管理
  - .env / .env.local / 環境変数からの設定読み込み（プロジェクトルート自動検出）
  - 自動ロード無効化オプションあり（テスト用）

---

## セットアップ

前提: Python と pip がインストールされているものとします。

1. リポジトリをクローンまたはソースを配置
2. パッケージをインストール（開発モード例）
   ```
   python -m pip install -e .
   ```
3. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成するか、OS 環境変数で設定してください。
   - 自動ロードはデフォルトで有効です。無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

必須の環境変数（Settings より）
- JQUANTS_REFRESH_TOKEN : J‑Quants リフレッシュトークン
- KABU_API_PASSWORD     : kabu ステーション API パスワード
- SLACK_BOT_TOKEN       : Slack ボットトークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意／デフォルト
- KABU_API_BASE_URL     : kabuapi の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 開発環境 (development | paper_trading | live)、デフォルト development
- LOG_LEVEL             : ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

.env の読み込み順序
- OS 環境変数 > .env.local > .env
- プロジェクトルートは .git または pyproject.toml を起点に自動検出

簡単な .env.example:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は簡単な Python スニペット例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（市場カレンダー取得 → 株価・財務取得 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3) ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄コードセット（例: 予め用意した一覧）
saved_counts = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
print(saved_counts)
```

4) ファクター計算（リサーチ）
```python
from datetime import date
from kabusys.research import calc_momentum, zscore_normalize

records = calc_momentum(conn, target_date=date(2025,1,31))
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

5) カレンダー操作
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2025, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

6) 監査ログ（audit）初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 主要モジュールと API（概要）

- kabusys.config
  - settings: 設定オブジェクト（プロパティ経由で環境変数取得）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動 .env ロードを無効化可能
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token: トークン取得（自動リフレッシュあり）
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
  - ETLResult クラス（実行結果）
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
  - セキュリティ対策（SSRF、DefusedXML、レスポンス上限）
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.stats / kabusys.data.features
  - zscore_normalize
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.audit
  - init_audit_schema, init_audit_db

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - etl.py
    - quality.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（README 作成時点の実装に基づく主要ファイルの一覧）

---

## 運用上の注意と設計方針（抜粋）

- J‑Quants のレート制限とリトライ設計を尊重しています（固定間隔スロットリング、指数バックオフ、401 時の自動リフレッシュ）。
- DuckDB への保存は冪等（ON CONFLICT）を原則としています。
- 外部入力（RSS など）には SSRF 対策や XML の安全パースを適用しています。
- 市場カレンダーが未取得の場合は曜日ベースでフォールバックする設計により堅牢性を保っています。
- ETL は Fail-Fast を避け、各ステップを個別にエラーハンドリングして可能な限り処理を継続します。品質チェックの結果は呼び出し元で判断してください。

---

## サポート / 開発

- バグ報告や機能要望は Issue を利用してください。
- テストや CI の実装はこの README の範囲外です。ユニットテストは各モジュールの公開関数を対象に実装することを推奨します。

---

必要に応じて README に追加したい情報（例: 実行スケジュールのサンプル、Docker 化、CI ワークフロー、詳細な .env.example）を教えてください。