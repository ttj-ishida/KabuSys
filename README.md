# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
DuckDB を中心としたデータレイヤー、J-Quants API 取得クライアント、RSS ニュース収集、特徴量計算や ETL パイプライン、監査ログスキーマなどのユーティリティ群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計されています。

- J-Quants API からの株価・財務・カレンダー取得（ページネーション・レート制限・リトライ対応）
- RSS ニュースの安全な収集と DuckDB への冪等保存
- DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）の定義・初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- 監査ログ（シグナル→発注→約定）用テーブルと初期化ユーティリティ

設計方針として、本番発注 API には直接触れない（データ取得・前処理・特徴量計算に注力）こと、標準ライブラリベースでの実装を優先することが挙げられます。

---

## 主な機能一覧

- 環境設定管理
  - .env 自動ロード（プロジェクトルート検出）と必須設定のラッパー（kabusys.config.settings）
- J-Quants API クライアント
  - レート制限、リトライ、トークン自動リフレッシュ、ページネーション対応
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への冪等保存関数（save_daily_quotes 等）
- DuckDB スキーマ管理
  - init_schema(db_path) によるテーブル・インデックス作成（Raw/Processed/Feature/Execution）
- ETL パイプライン
  - run_daily_etl: カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分取得・バックフィル・品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集
  - RSS フィード取得（SSRF対策・gzip制限・XML安全対策）
  - raw_news / news_symbols への冪等保存
- 研究用ユーティリティ
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
- 監査ログ（Audit）
  - signal_events / order_requests / executions の定義と初期化ユーティリティ（init_audit_schema / init_audit_db）

---

## 必要条件（推奨）

- Python 3.10+
- 依存ライブラリ（最低限）
  - duckdb
  - defusedxml

開発・実行環境に応じて追加パッケージが必要になる可能性があります（例: テストフレームワーク等）。

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発パッケージがあれば pip install -e . など
```

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数を設定（またはプロジェクトルートに `.env` を配置）

必須環境変数（少なくともこれらを設定してください）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API 用パスワード（本モジュール参照）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

オプション／デフォルト変数:
- KABUSYS_ENV : development / paper_trading / live （デフォルト: development）
- LOG_LEVEL : DEBUG / INFO / ... （デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動で .env を読み込まない

例 `.env`（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

自動ロード:
- モジュール import 時にプロジェクトルート（.git or pyproject.toml）を起点として .env → .env.local を読み込みます。
- 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（簡単なコード例）

以下に典型的な利用フローを示します。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # デフォルトで今日を対象に実行
print(result.to_dict())
```

3) 研究用ファクター計算（例: モメンタム）
```python
from kabusys.research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2025, 1, 15))
# records は [{"date": ..., "code": "7203", "mom_1m": ..., ...}, ...]
```

4) RSS ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出に使う有効コード集合（任意）
known_codes = {"7203", "6758", "9984", ...}

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # 各ソースごとの新規保存数
```

5) J-Quants から直接データ取得（テスト等）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
financials = fetch_financial_statements(date_from=date(2023,1,1), date_to=date(2024,1,1))
```

6) 監査ログ DB 初期化（監査専用 DB を用いる場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

---

## よく使う API（モジュールと関数）

- kabusys.config
  - settings: 環境変数アクセスラッパー（settings.jquants_refresh_token 等）
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, ...), run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
- kabusys.data.stats
  - zscore_normalize

---

## ディレクトリ構成

主要ファイル・モジュール構成（リポジトリの src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - news_collector.py            — RSS ニュース収集 / 保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - stats.py                     — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                  — ETL パイプライン（差分取得・run_daily_etl 等）
    - features.py                  — 特徴量ユーティリティのエクスポート
    - calendar_management.py       — 市場カレンダー管理ユーティリティ
    - audit.py                     — 監査ログスキーマ / 初期化
    - etl.py                       — ETL の公開インターフェース（ETLResult 再エクスポート）
    - quality.py                   — データ品質チェック
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py       — 将来リターン計算 / IC / サマリー等
  - strategy/                       — 戦略関連（実装ファイルは空の __init__）
  - execution/                      — 発注実行関連（空の __init__）
  - monitoring/                     — 監視関連（空の __init__）

（実装ファイルは上記 README に記載されたモジュールに対応します）

---

## 注意点 / 実運用での留意事項

- J-Quants API の利用規約・レート制限を遵守してください。モジュールは 120 req/min を仮定した実装です。
- DuckDB のバージョン差異により一部の機能（外部キーの ON DELETE 動作や一部制約）が異なる場合があります。DDL コメントを参照して運用ルールを決めてください。
- .env の自動読み込みはプロジェクトルート検出に依存します。配布されたパッケージや CI 環境では意図しない動作になる場合があるため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して明示的に環境を管理することを推奨します。
- ニュース収集では SSRF 対策・XML の安全パーサ（defusedxml）を使用していますが、外部ソースは常に不確実性を伴うため運用上の監視を行ってください。
- 本ライブラリはデータ取得・特徴量計算・ETL を主目的とし、注文送信（証券会社 API を用いた実注文）や資金管理ロジックは別途実装する想定です。実際に売買を行う場合は安全策（ペーパー取引 / 厳格なリスク管理）を徹底してください。

---

## ライセンス / 貢献

（ライセンス表記がリポジトリに含まれている場合はそちらに従ってください）  
バグ報告・機能提案・プルリクエストは歓迎します。ドキュメントやテストの追加も助かります。

---

以上が KabuSys の概要と利用ガイドです。必要であれば、セットアップ手順の詳細（requirements.txt、CI 設定、データ初期ロード例など）や具体的な使用例（ETL の cron 設定、Slack 通知ラッパーの例）を追加で作成します。どの部分を詳しく知りたいか教えてください。