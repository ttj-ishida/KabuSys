# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ）。データ収集（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、発注監査などをモジュール化して提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のレイヤーで構成された投資システムの基盤ライブラリです。

- Data Layer (DuckDB): 生データの永続化（raw）、整形済みデータ、特徴量、実行ログ（orders/trades/positions など）
- Data Ingestion: J-Quants API クライアント（レート制御・リトライ・トークン管理）・ETL パイプライン
- Research: ファクター計算・特徴量探索（IC, forward returns など）
- Strategy: 特徴量の正規化・合成（feature engineering）とシグナル生成（buy/sell の判定）
- News Collector: RSS フィード収集、記事の前処理、銘柄抽出
- Calendar / Utilities: JPX カレンダー管理、営業日の計算、監査ログスキーマ

設計上のポイント:
- DuckDB をデータベースに使用し、冪等性を重視（ON CONFLICT 等）
- ルックアヘッドバイアスに配慮（対象日までのデータのみ参照）
- API 呼び出しはレート制御・リトライ・トークンリフレッシュ対応
- 外部依存を抑えた純粋な Python 実装（ただし一部に duckdb / defusedxml 等を使用）

---

## 機能一覧

主な機能（モジュール単位）

- kabusys.config
  - .env ファイル / 環境変数の自動ロード（プロジェクトルート検出）
  - 設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, KABUSYS_ENV, LOG_LEVEL など）
- kabusys.data.jquants_client
  - J-Quants API クライアント（token refresh、ページネーション、レート制御、リトライ）
  - fetch / save: 日足・財務データ・カレンダー
- kabusys.data.schema
  - DuckDB のテーブル定義と初期化（init_schema）
- kabusys.data.pipeline
  - run_daily_etl: 日次 ETL（calendar, prices, financials）＋品質チェック呼び出し
  - 差分取得・バックフィル対応
- kabusys.data.news_collector
  - RSS 収集、前処理、raw_news 保存、銘柄抽出・紐付け
  - SSRF 対策、gzip/サイズ制限、XML 攻撃対策（defusedxml）
- kabusys.research
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（data.stats）
- kabusys.strategy
  - build_features: 生ファクターを正規化して features テーブルへ保存
  - generate_signals: features + ai_scores を統合して BUY/SELL シグナルを signals テーブルへ保存
- その他
  - calendar management（営業日判定 / next/prev / カレンダー更新ジョブ）
  - audit（監査ログ/発注トレーサビリティ）スキーマ

---

## 必要な環境変数

主要な必須環境変数（設定が無いと例外になります）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知（Bot）のトークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（デフォルト値あり）:

- KABUSYS_ENV — 環境: `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

注意:
- パッケージの起動時、プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動読み込みします。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 環境 (3.10+) を用意します。
2. リポジトリをクローン／配置（src 配下にパッケージがあります）。
3. 必要な依存パッケージをインストールします。最低限の依存例:

   ```
   pip install duckdb defusedxml
   ```

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数を設定（上記を参照）。プロジェクトルートに `.env` を置くと自動ロードされます。

5. DuckDB スキーマ初期化:

   Python REPL やスクリプトで:

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

   ":memory:" を使うとインメモリ DB を使用できます。

---

## 使い方（代表的なワークフローとコード例）

以下は基本的な日次処理の流れの例です。

1) DB 初期化（1回だけ）:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL（J-Quants からデータを取得して保存）:

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量作成（target_date に対して）:

```python
from datetime import date
from kabusys.strategy import build_features

cnt = build_features(conn, date(2025, 1, 15))
print(f"features upserted: {cnt}")
```

4) シグナル生成（BUY/SELL を signals テーブルにアップサート）:

```python
from kabusys.strategy import generate_signals
from datetime import date

total = generate_signals(conn, date(2025, 1, 15), threshold=0.6)
print(f"signals generated: {total}")
```

重みを変えたい場合:

```python
weights = {"momentum": 0.5, "value": 0.2, "volatility": 0.15, "liquidity": 0.15, "news": 0.0}
generate_signals(conn, date(2025,1,15), weights=weights)
```

5) ニュース収集ジョブ:

```python
from kabusys.data.news_collector import run_news_collection
# known_codes は既知の銘柄コードセット（抽出に使用）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

6) カレンダー更新ジョブ（夜間バッチとして想定）:

```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

ログ・監視:
- ログレベルは環境変数 LOG_LEVEL で制御します。
- KABUSYS_ENV によって挙動（is_live / is_paper 等）を判定できます。

---

## ディレクトリ構成（抜粋）

src/kabusys パッケージの主なファイル構成:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（fetch/save）
    - schema.py          — DuckDB スキーマ定義と init_schema
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - stats.py           — zscore_normalize 等の統計ユーティリティ
    - features.py        — zscore_normalize を公開
    - news_collector.py  — RSS 収集・前処理・保存
    - calendar_management.py — カレンダー更新・営業日ロジック
    - audit.py           — 監査ログスキーマ
    - (その他: quality, execution 等が想定)
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features
    - signal_generator.py    — generate_signals
  - execution/            — 発注 / execution 層（実装の拡張ポイント）
  - monitoring/           — 監視・メトリクス保存（SQLite 等を想定）

---

## 注意点 / 運用上の補足

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に実行されます。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。
- DuckDB スキーマは init_schema() で初期化してください（初回のみ）。get_connection() は既存 DB に接続しますが、スキーマ初期化は行いません。
- J-Quants API のレート制御（120 req/min）やリトライ・401 リフレッシュなどはクライアント側で扱っていますが、運用環境では適切な API 利用制限の管理が必要です。
- RSS 収集は外部 HTTP を行うため、network / SSRF に関する対策（コード内で実装済み）に注意してください。大規模運用でのタイムアウトや失敗時のリトライ設計は運用側で追加することを推奨します。
- Strategy 層のロジック（閾値・重みなど）は設計ドキュメント（StrategyModel.md 相当）に基づいています。実運用前には十分なバックテスト・ペーパー取引環境での検証を行ってください。

---

## 今後の拡張・TODO（参考）

- execution 層と証券会社 API の実装（実注文・約定処理）
- Slack 等への通知モジュールの連携（settings での Slack 設定が用意済み）
- more quality checks（data.quality の追加）
- モジュール別の CLI / 管理スクリプト（cron/airflow 用の簡易ジョブラッパー）

---

README に記載の内容で不明点や、実行サンプル（cron での日次実行例や Docker 化、CI 用設定など）を追加で希望される場合は教えてください。必要に応じて .env.example や簡易起動スクリプトも用意します。