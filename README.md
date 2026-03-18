# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。DuckDB をデータレイヤーに用い、J-Quants API や RSS ニュースからデータを取得して ETL → 品質チェック → 特徴量計算 → 研究／戦略モジュールへ渡すためのユーティリティ群を提供します。

主な設計方針：
- DuckDB を中心とした 3 層データモデル（Raw / Processed / Feature）と発注・監査テーブルを備える
- J-Quants API からのデータ取得はレート制御・リトライ・トークン自動更新を実装
- RSS ニュースは正規化・SSRF 等の安全対策付きで収集し、銘柄抽出・DB 保存を行う
- 研究（research）モジュールは外部ライブラリに依存せず純粋 Python 実装を目指す（DuckDB 接続を受け取り SQL と組み合わせて計算）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の明示的取得（settings オブジェクト）

- データ取得 / 保存（J-Quants API クライアント）
  - 日足株価（fetch_daily_quotes / save_daily_quotes）
  - 財務諸表（fetch_financial_statements / save_financial_statements）
  - JPX マーケットカレンダー（fetch_market_calendar / save_market_calendar）
  - API レート制御、リトライ、トークン自動リフレッシュ

- ETL パイプライン
  - 差分取得（backfill 対応）と IDempotent な保存
  - 市場カレンダー／株価／財務の統合日次 ETL（run_daily_etl）
  - 品質チェック（欠損、スパイク、重複、日付整合性）

- ニュース収集
  - RSS 収集（gzip 対応、最大受信サイズ制限、SSRF/プライベート IP 検知）
  - 記事正規化・ID 生成（URL 正規化 -> SHA256）
  - raw_news / news_symbols への冪等保存

- スキーマ管理
  - DuckDB 用スキーマ初期化（init_schema）
  - 監査ログ専用スキーマ（init_audit_schema / init_audit_db）

- 研究用ユーティリティ
  - Momentum / Value / Volatility 等のファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算（calc_forward_returns）
  - IC（Spearman ρ）計算（calc_ic）
  - ファクター統計サマリー（factor_summary）
  - Zスコア正規化（zscore_normalize）

---

## 動作環境 / 前提

- Python 3.10+
- 必要なライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS）

インストールはプロジェクトの配布形態に依存しますが、開発環境であれば pip で requirements をインストールします：
```
pip install duckdb defusedxml
```

---

## 環境変数（必須 / 任意）

設定は環境変数、またはプロジェクトルートの `.env` / `.env.local` に記載して自動読み込みできます（自動読み込みはプロジェクトルートに `.git` または `pyproject.toml` が存在することを前提に行われます）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
2. 必要ライブラリをインストール
   - 例: pip install -r requirements.txt（requirements.txt がある場合）
   - 最低限：duckdb, defusedxml
3. プロジェクトルートに `.env` を配置し、必要な環境変数を設定
4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで実行:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # :memory: も可
```

5. 監査ログ専用 DB を初期化する場合:

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主な例）

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）:

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 個別 ETL ジョブの実行例:

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

conn = init_schema("data/kabusys.duckdb")
run_calendar_etl(conn, target_date=date.today())
run_prices_etl(conn, target_date=date.today())
run_financials_etl(conn, target_date=date.today())
```

- ニュース収集（RSS）と銘柄紐付け:

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄コードセットを用意
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- J-Quants データを直接取得（クライアント利用）:

```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
from kabusys.config import settings
from datetime import date

# settings.jquants_refresh_token を利用して内部で id_token を取得します
quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
financials = fetch_financial_statements(date_from=date(2023,1,1), date_to=date(2023,12,31))
```

- 研究用ファクター計算（DuckDB 接続を渡す）:

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic

conn = init_schema("data/kabusys.duckdb")
t = date(2025, 1, 31)
mom = calc_momentum(conn, t)
val = calc_value(conn, t)
vol = calc_volatility(conn, t)
fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
# calc_ic は factor_records と forward_records を code で結合して Spearman ρ を出す
```

---

## 主要モジュール（API サマリ）

- kabusys.config
  - settings: Settings オブジェクト（環境変数の取得 / バリデーション）
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult クラス
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.research
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
- kabusys.data.audit
  - init_audit_schema, init_audit_db

---

## ディレクトリ構成

（プロジェクトのルートが `src/` を想定した場合の主要ファイル/ディレクトリ）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント
    - news_collector.py            — RSS ニュース収集
    - schema.py                    — DuckDB スキーマ定義・初期化
    - pipeline.py                  — ETL パイプライン
    - etl.py                       — ETL インターフェース（ETLResult）
    - features.py                  — 特徴量ユーティリティ公開
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py       — マーケットカレンダー管理／バッチジョブ
    - audit.py                      — 監査ログスキーマと初期化
    - quality.py                    — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py       — 将来リターン / IC / サマリー
    - factor_research.py           — momentum/value/volatility 等の計算
  - strategy/                       — 戦略実装（空のパッケージ）
  - execution/                      — 発注実装（空のパッケージ）
  - monitoring/                     — 監視関連（空のパッケージ）

---

## 運用上の注意 / セキュリティ

- .env にシークレットを平文で置く場合はアクセス権限を適切に管理してください。
- RSS 取得は外部 URL を扱うため SSRF 対策や受信サイズ制限が組み込まれていますが、運用環境ではプロキシやファイアウォール等で更なる制御を推奨します。
- 本番口座での自動発注を行う際は、paper_trading / live など KABUSYS_ENV による環境分離と安全な許可フローを確立してください。
- DuckDB における TIMESTAMP/タイムゾーン取り扱いに注意してください（監査ログは UTC に固定する設計が一部にあります）。

---

## 今後の拡張案（参考）

- strategy / execution の実装（発注ロジック・リスク管理）
- Slack 通知やモニタリングダッシュボード連携
- 機械学習モデルのスコアリングパイプライン追加（ai_scores テーブル利用）
- CLI ツール化（ETL の cron 実行や calendar_update_job のスケジューリング）

---

この README はコードベースの公開 API と設計方針をまとめたものです。実際の運用や拡張時は各モジュールの docstring / 関数コメントを参照してください。必要であれば、README に実行スクリプト例や Docker 化手順、CI 設定のテンプレートを追加します。