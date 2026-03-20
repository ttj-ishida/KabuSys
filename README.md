# KabuSys

日本株向けの自動売買プラットフォーム（データプラットフォーム、リサーチ、特徴量生成、シグナル生成、発注トレーサビリティを含む）です。  
このリポジトリは主に以下のレイヤーで構成されています。

- Data: J-Quants からのデータ取得 / DuckDB による永続化 / ETL / ニュース収集
- Research: ファクター計算・特徴量探索
- Strategy: 特徴量の正規化・合成、売買シグナル生成
- Execution / Audit: 発注・約定・監査ログ（スキーマ・テーブル定義）
- Monitoring: 監視系（ディレクトリ構成に含まれるが、個別実装は省略）

README では概要、主な機能、セットアップ、基本的な使い方、そしてディレクトリ構成をまとめます。

## プロジェクト概要

KabuSys は日本株のクオンツ運用を想定したモジュール群を提供します。  
主な目的は次の通りです。

- J-Quants API から株価・財務・カレンダーなどを取得し DuckDB に保存する ETL（差分更新／バックフィル対応）
- 研究（research）で計算した生ファクターを戦略用の特徴量に変換・正規化して保存
- 正規化済み特徴量と AI スコアを統合し、BUY / SELL シグナルを生成
- RSS ベースのニュース収集と銘柄紐付け
- 発注 → 約定 → ポジション の監査ログを保持するスキーマ設計

設計上のポイント:
- ルックアヘッドバイアスを防ぐ設計（target_date 時点のデータのみを使用）
- DuckDB を中心とした軽量なオンプレ/ローカル実装
- 冪等性（DB 保存は ON CONFLICT DO UPDATE / DO NOTHING 等で設計）
- 外部依存を最小限に（標準ライブラリ主体。ネットワーク処理・XML で外部 lib を利用）

## 主な機能一覧

- データ取得・保存
  - J-Quants クライアント（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - DuckDB へ冪等保存（save_daily_quotes, save_financial_statements, save_market_calendar）
  - ETL パイプライン（run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl）
  - スキーマ初期化（init_schema）
- ニュース収集
  - RSS フィード取得（fetch_rss）・前処理・記事保存（save_raw_news）
  - 記事と銘柄コードの紐付け（extract_stock_codes, save_news_symbols）
  - SSRF / XML 攻撃 / Gzip bomb 等に配慮した堅牢実装
- Research（研究用）
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー
  - Z スコア正規化ユーティリティ
- Strategy（戦略）
  - 特徴量構築（build_features）: raw ファクターをマージ・ユニバースフィルタ・標準化して `features` テーブルへ保存
  - シグナル生成（generate_signals）: final_score 計算、BUY/SELL の判定、`signals` テーブルへ保存
- スキーマ・監査
  - DuckDB のスキーマ定義（raw / processed / feature / execution レイヤー）
  - 監査テーブル（signal_events, order_requests, executions 等）

## 要件（Prerequisites）

- Python >= 3.10（型注釈で PEP 604 (X | Y) を利用）
- パッケージ（最低限）
  - duckdb
  - defusedxml
- ネットワーク経由で J-Quants を利用する場合は J-Quants のリフレッシュトークン等が必要

インストール例（仮に requirements.txt がない場合）:
```bash
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
# 開発用にローカルパッケージとしてインストールする場合
pip install -e .
```

※ 実行環境では追加で logging 設定や監視・スケジューリング（cron / Airflow 等）を行って運用してください。

## 環境変数 / .env

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込みます（自動読み込みはデフォルトで有効）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB 等の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

簡易 .env.example:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## セットアップ手順（簡単な手順）

1. リポジトリをクローン / コピー
2. 仮想環境作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # またはプロジェクトを editable install
   pip install -e .
   ```
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
5. DuckDB スキーマを初期化
   - Python REPL / スクリプトで:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```
   これにより必要なテーブルがすべて作成されます（冪等）。

## 使い方（基本的なワークフロー例）

以下は最小限の利用例です。実運用ではエラーハンドリング・ログ出力・スケジューリングを追加してください。

- 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回のみ）
conn = init_schema(settings.duckdb_path)

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn)
print(result.to_dict())
```

- 特徴量構築（feature layer への保存）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema(settings.duckdb_path)
cnt = build_features(conn, target_date=date(2025, 1, 31))
print(f"features upserted: {cnt}")
```

- シグナル生成（features + ai_scores を使い signals テーブルへ保存）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema(settings.duckdb_path)
total = generate_signals(conn, target_date=date(2025, 1, 31))
print(f"signals written: {total}")
```

- ニュース収集ジョブ（RSS -> raw_news, news_symbols）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema(settings.duckdb_path)
# known_codes は銘柄抽出に使用する有効コードのセット（省略可）
res = run_news_collection(conn, known_codes=set(["7203","6758"]))
print(res)
```

- J-Quants API を直接使う（テストや個別取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.config import settings

token = get_id_token()  # settings.jquants_refresh_token を利用
records = fetch_daily_quotes(id_token=token, date_from=None, date_to=None)
```

注意事項:
- generate_signals / build_features 等は target_date 時点のデータのみを用いるため、ETL → build_features → generate_signals の順で実行すること。
- 発注（execution）層は本 README の示すコードベースにスキーマやユーティリティが含まれますが、実際のブローカー API 連携は別途実装が必要です。
- 自動ロードされる `.env` はプロジェクトルート（.git/pyproject.toml を探索）を基準にします。CI/テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます。

## ディレクトリ構成

主要ファイル・モジュールを抜粋して示します（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント + 保存ユーティリティ
    - schema.py                  — DuckDB スキーマ定義 / init_schema / get_connection
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - news_collector.py          — RSS 収集・前処理・保存・銘柄抽出
    - stats.py                   — 共通統計ユーティリティ（zscore_normalize）
    - features.py                — zscore_normalize の公開ラッパ
    - calendar_management.py     — JPX カレンダー管理ユーティリティ
    - audit.py                   — 監査ログ系 DDL（signal_events 等）
    - quality.py?                — 品質チェック（pipeline から呼ばれる想定。実装が別ファイルにある想定）
  - research/
    - __init__.py
    - factor_research.py         — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py     — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py     — build_features
    - signal_generator.py        — generate_signals
  - execution/
    - __init__.py                — 発注層のエントリ（実装は発展的）
  - monitoring/                  — 監視関連（別ディレクトリに設置する想定）

（注）上記は抜粋です。実際のファイルは src/kabusys 以下で確認してください。

## 開発／テストに関するヒント

- 自動環境変数読み込みはプロジェクトルートを .git / pyproject.toml で探索するため、テスト時にワーキングディレクトリを変更しても安定して動作します。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用してください。
- DuckDB は軽量 & ファイルベースです。テストでは `:memory:` を渡してインメモリ DB を使うことができます。
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  ```
- ニュース RSS の HTTP 周りや XML パースは外部の不正値に対して堅牢化されていますが、テスト時はネットワーク依存を排除するために各種ネットワーク関数をモックしてください（例: kabusys.data.news_collector._urlopen の差し替え）。

---

この README はリポジトリに含まれるモジュールから抽出した設計意図・使用方法をまとめたものです。実際に運用する際はログ設定、例外監視、アクセス制御、バックテスト・リスク管理の仕組みを十分に整備してください。必要であれば、サンプルスクリプトや運用手順（cron / systemd / Airflow）を別途追加できます。