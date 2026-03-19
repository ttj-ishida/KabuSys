# KabuSys

日本株自動売買プラットフォームのコアライブラリ（ミニマム実装）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査用スキーマなどを含むモジュール群です。

## 概要
KabuSys は次のような機能層を提供します。
- Data Layer: J-Quants からの株価・財務・カレンダー・ニュース取得と DuckDB への保存（冪等）
- ETL / Pipeline: 差分取得・バックフィル・品質チェックを含む日次 ETL
- Research: ファクター計算・将来リターン・IC・統計サマリ等の研究ユーティリティ
- Strategy: ファクターの正規化・統合と売買シグナル生成（BUY/SELL 判定）
- Execution / Audit: 発注・約定・ポジション・監査ログのスキーマ（発注処理の骨組み）
- News: RSS フィードからのニュース収集と銘柄紐付け

設計方針の例:
- ルックアヘッドバイアスを防ぐ（target_date 時点のデータのみを使用）
- DuckDB を中心としたローカル DB に冪等に保存する
- 外部依存は最小限（標準ライブラリ + duckdb + defusedxml 等）
- エラー耐性・リトライ・レートリミット・SSRF 対策を考慮

## 主な機能一覧
- J-Quants API クライアント（トークン自動リフレッシュ、リトライ、レート制御）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB 保存）
- DuckDB スキーマ定義・初期化（init_schema）
- ETL パイプライン（run_daily_etl、個別 run_prices_etl/run_financials_etl/run_calendar_etl）
- News RSS 収集（fetch_rss, save_raw_news, run_news_collection）
- マーケットカレンダー管理（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
- 研究用ユーティリティ（calc_momentum/calc_volatility/calc_value、calc_forward_returns、calc_ic、factor_summary）
- 特徴量作成（build_features） — features テーブルへ保存
- シグナル生成（generate_signals） — features と ai_scores を統合して signals テーブルへ保存
- 汎用統計ユーティリティ（zscore_normalize）

## 必要要件
- Python 3.10 以上（typing の `|` 等を使用）
- pip install で入れる主要依存:
  - duckdb
  - defusedxml
（プロジェクトの実際の requirements.txt / pyproject.toml を参照してください）

## 環境変数 / 設定
設定は .env ファイル（プロジェクトルート）または OS 環境変数から読み込まれます。プロジェクトルートの自動検出は `.git` または `pyproject.toml` を基準に行われます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数:
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（data.jquants_client で使用）
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（Slack 通知機能を使う場合）
  - SLACK_CHANNEL_ID: Slack チャンネル ID
  - KABU_API_PASSWORD: kabuステーション API パスワード（execution 層を使う場合）
- 任意 / デフォルトあり
  - KABUSYS_ENV: `development` / `paper_trading` / `live` （デフォルト `development`）
  - LOG_LEVEL: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト `INFO`）
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

注意: Settings クラスは `kabusys.config.settings` として利用可能です。必須変数未設定時は例外を投げます。

例（.env）の最小例:
```
JQUANTS_REFRESH_TOKEN=xxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
2. 仮想環境を作成・有効化（例: python -m venv .venv && source .venv/bin/activate）
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - 実プロジェクトでは requirements.txt / pyproject.toml に従ってください
4. .env を作成して必要な環境変数を設定
5. データベーススキーマの初期化（DuckDB）
   - Python REPL かスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     ```
   - またはインメモリ DB でテスト:
     ```python
     conn = init_schema(":memory:")
     ```
6. ログレベルの設定やその他パラメータは環境変数で制御

## 使い方（代表的な操作例）
以下はモジュールを直接呼ぶ簡単な例です。実運用では CLI やジョブスケジューラ（cron/airflow）から呼ぶ想定です。

- DuckDB の初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行（J-Quants から取得して DB に保存）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日
print(result.to_dict())
```

- 特徴量の作成（target_date の features を作成して features テーブルへ保存）
```python
from datetime import date
from kabusys.strategy import build_features
n = build_features(conn, date(2025, 1, 10))
print(f"upserted features: {n}")
```

- シグナルの生成（features / ai_scores / positions を参照して signals を作成）
```python
from datetime import date
from kabusys.strategy import generate_signals
count = generate_signals(conn, date(2025, 1, 10))
print(f"generated signals: {count}")
```

- ニュース収集（RSS 取得・保存・銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は有効な銘柄コードのセット（抽出に使用）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

- J-Quants API を直接叩いてデータを取得・保存する例
```python
from kabusys.data import jquants_client as jq
data = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,2))
jq.save_daily_quotes(conn, data)
```

## 注意点 / 運用メモ
- DuckDB の初期化は init_schema を一度実行するだけで OK（冪等）。
- ETL は差分更新ロジックを持ち、バックフィル期間を指定できます（デフォルト 3 日）。
- J-Quants API のレートリミット（120 req/min）はクライアントで遵守します。
- NewsCollector は SSRF 対策・XML インジェクション対策（defusedxml）・受信サイズ上限を実装。
- Strategy 層は発注 API（kabu）に依存せず signals テーブルへ出力します。発注処理は別途 execution 層に実装して接続してください。
- tests 等で自動的に .env を読み込ませたくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## ディレクトリ構成（概要）
リポジトリの主要なファイル構成（src 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント + 保存関数
    - news_collector.py        — RSS ニュース収集・保存・銘柄抽出
    - schema.py                — DuckDB スキーマ定義・初期化
    - stats.py                 — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — マーケットカレンダー管理
    - audit.py                 — 監査ログ用スキーマ
    - features.py              — features インターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py       — mom/volatility/value 等のファクター計算
    - feature_exploration.py   — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py   — features 作成（正規化・ユニバースフィルタ等）
    - signal_generator.py      — final_score 計算と BUY/SELL 判定
  - execution/                  — 発注・取引管理（スケルトン）
  - monitoring/                 — 監視・メトリクス（将来的に利用）
  - その他 README 等

（上記は本コードベースに含まれる主要モジュールの抜粋です。詳細はソースコードを参照してください。）

## 貢献 / 拡張ポイント
- execution 層: kabu ステーションやブローカー API との接続／発注実装
- AI スコア生成: ai_scores テーブル用のモデルスコアリングパイプライン
- 品質チェックモジュールの充実（quality モジュールを拡張）
- テストカバレッジの追加（ETL、news_collector のネットワーク部分はモック化）
- CLI やジョブスケジューラ（Airflow / Prefect）用のラッパー実装

---

問題や改善提案があれば、どの機能を拡張したいか教えてください。README の追加項目（例: 実行時ログ設定や CI 設定テンプレート）も作成できます。