# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ（KabuSys）。  
データ収集・ETL、ファクター計算（リサーチ）、特徴量生成、ニュース収集、監査ログ、発注管理などをモジュール化して提供します。

主な設計方針は「DuckDB を中心としたローカルデータレイク」「J-Quants API によるデータ収集」「本番口座へ直接触れないリサーチコード」「ETL の冪等性・品質チェック」です。

---

## 主要機能（抜粋）

- J-Quants API クライアント
  - 日足（OHLCV）、財務データ、マーケットカレンダーの取得
  - レート制限管理、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ（ON CONFLICT 用）
- ETL パイプライン
  - 差分取得（backfill 対応）、保存、品質チェックの統合実行（run_daily_etl）
- データスキーマ管理
  - DuckDB 用スキーマ定義と初期化（init_schema）
  - 監査ログ（audit）用スキーマ初期化（init_audit_schema / init_audit_db）
- ニュース収集
  - RSS 取得・前処理（URL 正規化、トラッキング除去）、記事保存（冪等）
  - SSRF 対策、gzip/サイズ制限、記事→銘柄抽出
- データ品質チェック
  - 欠損 / スパイク / 重複 / 日付不整合の検出
- リサーチ（factor / feature）モジュール
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン（forward returns）や IC（Spearman）計算
  - Z スコア正規化ユーティリティ
- マーケットカレンダー管理（営業日判定、次/前営業日取得など）
- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート探索、上書きルール、無効化フラグあり）

---

## 必要条件

- Python 3.10+
- 外部パッケージ（例）
  - duckdb
  - defusedxml

（実行環境によっては他のライブラリも必要になる可能性があります。setup 用の requirements ファイルがあればそちらを参照してください。）

例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## 環境変数 / .env

以下の環境変数を設定してください（必須は README 内で明示）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注関連を使う場合）
- SLACK_BOT_TOKEN — Slack 通知用トークン（通知を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネルID

任意 / デフォルト:
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)。デフォルト: development
- LOG_LEVEL — ログレベル (DEBUG/INFO/...)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

自動ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に自動で `.env` → `.env.local` を読み込みます。  
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンし仮想環境を作成
2. 依存ライブラリをインストール（duckdb, defusedxml など）
3. プロジェクトルートに `.env` を作成し必要な環境変数を設定
4. DuckDB スキーマを初期化

例（Python スニペット）:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

監査ログ専用 DB を分ける場合:
```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 基本的な使い方

- 設定アクセス:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
print(settings.env, settings.is_live)
```

- 日次 ETL 実行（市場カレンダー・株価・財務データの取得と品質チェック）:
```python
from datetime import date
import duckdb
from kabusys.data import schema, pipeline

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ実行:
```python
from kabusys.data import news_collector
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")  # 既存接続
res = news_collector.run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(res)  # {source_name: saved_count}
```

- リサーチ（ファクター）例:
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2024, 1, 31)

momentum = calc_momentum(conn, d)
forwards = calc_forward_returns(conn, d, horizons=[1,5,21])

# 例: mom_1m と fwd_1d の IC
ic = calc_ic(momentum, forwards, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(momentum, ["mom_1m","ma200_dev"])
```

- Z-score 正規化:
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(momentum, ["mom_1m","mom_3m","ma200_dev"])
```

- J-Quants の生データ取得（例）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes
# id_token を指定しなければモジュールキャッシュで自動取得・リフレッシュされる
quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## よく使う API / モジュール概要

- kabusys.config
  - settings: 環境変数ラッパー（必須変数チェック、env 判定など）
- kabusys.data.schema
  - init_schema(db_path) / get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl 他（run_prices_etl / run_financials_etl / run_calendar_etl）
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, ...
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize

---

## ディレクトリ構成（主要ファイル）

（ここに示したのは本リポジトリ内で提供される主要モジュールの一覧です）

- src/kabusys/
  - __init__.py
  - config.py                             — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py                    — J-Quants API クライアント & 保存
    - news_collector.py                    — RSS 取得・記事保存・銘柄紐付け
    - schema.py                            — DuckDB スキーマ定義と init_schema
    - stats.py                             — zscore_normalize 等の統計ユーティリティ
    - pipeline.py                          — ETL パイプラインの実装（run_daily_etl 等）
    - quality.py                           — データ品質チェック
    - calendar_management.py               — market_calendar の管理ユーティリティ
    - audit.py                             — 監査ログ用スキーマ初期化
    - etl.py                               — ETL 結果型の公開インターフェース
    - features.py                          — 特徴量ユーティリティの再エクスポート
  - research/
    - __init__.py
    - feature_exploration.py               — 将来リターン計算、IC、統計サマリー
    - factor_research.py                   — Momentum/Volatility/Value ファクター実装
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

---

## 運用上の注意 / ベストプラクティス

- 秘密情報（API トークン等）は .env に保存してリポジトリに含めないでください。`.env.example` を用意して雛形を管理することを推奨します。
- J-Quants のレート制限（120 req/min）はクライアント側で制御されていますが、API 利用状況に応じてさらに調整する場合は RateLimiter の設定を見直してください。
- ETL は冪等性を考慮して設計されていますが、外部から直接 DB を編集すると整合性が損なわれる可能性があります。可能な限り API 経由でデータ操作してください。
- テスト目的で DuckDB をメモリモード(":memory:")で使用できます。
- 自動環境変数ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテストなどで便利です）。
- 本コードベースのリサーチ関数は本番口座への発注を行わない設計です（安全）。

---

## サポート / 貢献

バグ報告、機能提案、プルリクエストは歓迎します。リポジトリに ISSUE / PR を作成してください。コーディング規約やテストカバレッジのガイドラインがある場合はそれに従ってください。

---

この README はコードベース内の主要機能を簡潔にまとめたものです。実際の詳細な仕様（StrategyModel.md / DataPlatform.md 等）や API の使い方はプロジェクト内の設計ドキュメントを参照してください。