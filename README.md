# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（パッケージ）です。  
データ取得・ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ定義など、戦略実行に必要な基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群から成ります。

- J-Quants API からの市場データ・財務データ・カレンダー取得（rate limiting / retry / token refresh 対応）
- DuckDB を用いたデータスキーマ定義および冪等保存
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究（research）用のファクター計算・特徴量探索ユーティリティ
- 戦略用の特徴量構築（feature engineering）とシグナル生成（signal generation）
- RSS ベースのニュース収集と記事→銘柄の紐付け
- マーケットカレンダーの管理（JPX）
- 監査ログ / 発注・約定管理用スキーマ

設計方針として、ルックアヘッドバイアス対策、冪等性、網羅的なエラーハンドリング、外部依存の最小化（できる限り標準ライブラリ）を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - レート制御（120 req/min）、リトライ、トークン自動リフレッシュ
- data/schema.py
  - DuckDB 用のスキーマ定義と init_schema(db_path)
- data/pipeline.py
  - run_daily_etl: 市場カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl（差分取得ロジック含む）
- data/news_collector.py
  - RSS フィード取得、記事ノーマライズ、raw_news 保存、銘柄抽出と紐付け
  - SSRF 対策、XML の安全パース、サイズ制限
- data/calendar_management.py
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- research/* (factor_research.py, feature_exploration.py)
  - モメンタム・ボラティリティ・バリュー計算、将来リターン・IC・統計サマリー
- strategy/*
  - feature_engineering.build_features(conn, target_date)
  - signal_generator.generate_signals(conn, target_date, threshold, weights)
- 共通ユーティリティ
  - data/stats.zscore_normalize, config.Settings（環境変数管理、自動 .env ロード機能）

---

## セットアップ手順

1. Python 環境（3.9+ 推奨）を準備します。

2. 必要パッケージをインストールします（最小例）:

   - duckdb
   - defusedxml

   例:
   pip install duckdb defusedxml

   （プロジェクト配布時は requirements.txt / pyproject.toml を参照してください）

3. リポジトリをインストール（開発モード）:
   pip install -e .

4. 環境変数の設定 (.env)
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動的にロードされます。
   - OS 環境変数が優先され、.env.local は .env を上書きします。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

   必須/代表的な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN  （J-Quants リフレッシュトークン） ← 必須
   - KABU_API_PASSWORD       （kabuステーション API パスワード） ← 必須（execution 層用）
   - SLACK_BOT_TOKEN         （通知用 Slack トークン） ← 必須（Slack 通知を使う場合）
   - SLACK_CHANNEL_ID        （通知先 Slack チャンネルID） ← 必須（Slack 通知を使う場合）
   - DUCKDB_PATH             （デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH             （デフォルト: data/monitoring.db）
   - KABUSYS_ENV             （development / paper_trading / live、デフォルト development）
   - LOG_LEVEL               （DEBUG/INFO/...、デフォルト INFO）

   .env の簡易例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡易例）

以下は基本的な利用フロー例です。すべて Python スクリプトから呼び出して利用します。

1. DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

- ":memory:" を渡せばインメモリ DB。

2. 日次 ETL の実行（市場カレンダー・株価・財務の差分取得）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3. 特徴量のビルド（strategy.feature_engineering.build_features）

```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4. シグナル生成（strategy.signal_generator.generate_signals）

```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {count}")
```

5. RSS ニュース収集と保存

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に用いる有効コードセット（例: 全上場コードセット）
results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(results)
```

6. カレンダー更新ジョブ（夜間バッチ）

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar records saved: {saved}")
```

---

## 環境設定の注意点

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を読み込みます。
  - OS 環境変数 > .env.local > .env の優先順位です。
  - テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます。

- J-Quants API
  - レート制限（120 req/min）に従う実装です。大量バックフィルを行う場合は注意してください。
  - トークンが 401 を返した場合は自動的にリフレッシュを試みます（1 回のみ）。

- セキュリティ
  - news_collector は SSRF 対策、XML 安全パース、レスポンスサイズ上限などを備えています。
  - 実運用では API トークン・パスワードは安全に管理してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + 保存関数
    - schema.py              — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - news_collector.py      — RSS 収集・保存・銘柄抽出
    - calendar_management.py — カレンダー管理（is_trading_day 等）
    - features.py            — zscore_normalize の公開ラッパ
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - audit.py               — 監査ログ用スキーマ
    - pipeline.py            — ETL 管理
  - research/
    - __init__.py
    - factor_research.py     — momentum / volatility / value 計算
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features
    - signal_generator.py    — generate_signals
  - execution/               — （発注・ブローカー連携のためのプレースホルダ）
  - monitoring/              — （監視・通知用コードを想定）

---

## 開発・デバッグのヒント

- DuckDB を使うため、SQL の一部は DuckDB の挙動に依存します。ローカルでのデバッグには get_connection(":memory:") を使うと便利です。
- 設定ミスで環境変数が見つからない場合、config.Settings のプロパティが ValueError を投げます。エラーメッセージで未設定のキー名が分かります。
- ニュース収集や API 呼び出しはネットワーク依存です。ユニットテストでは jquants_client._request や news_collector._urlopen をモックしてオフラインでテストしてください。
- ETL は差分更新ロジックを持ちます。バックフィル日数パラメータを調整して再取得・修正吸収を行えます。

---

この README はコードベースの主要機能と利用方法の概観を示しています。詳細な設計仕様はソース内の docstring（各モジュール冒頭コメント）や関連仕様ファイル（StrategyModel.md / DataPlatform.md 等）を参照してください。必要であれば README に追加するサンプルや運用手順（cron/CI 設定、Slack 通知例、監査ログ参照方法など）も作成します。