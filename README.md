# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）・ニュース収集・LLM によるニュース評価・市場レジーム判定・ファクター計算・監査ログ管理など、運用に必要なユーティリティを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 動作要件・依存関係
- セットアップ手順
- 環境変数（.env）と設定
- 使い方（主要な呼び出し例）
- ディレクトリ構成（主要ファイルの説明）
- 設計上の注意点

---

## プロジェクト概要

KabuSys は日本市場向けのデータプラットフォーム兼リサーチ／自動売買基盤のライブラリ群です。主に以下の役割を持ちます。

- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に格納する ETL（データ取得）パイプライン
- RSS ベースのニュース収集と前処理、記事の銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント評価（銘柄別）と、マクロニュースを用いた市場レジーム判定
- ファクター（モメンタム・バリュー・ボラティリティ等）計算、特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 発注・約定の監査（audit）テーブル作成ユーティリティ

設計上、ルックアヘッドバイアス防止・冪等性・フェイルセーフ（API 失敗時の安全なフォールバック）を重視しています。

---

## 主な機能一覧

- data
  - ETL：run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（fetch / save 関数）
  - 市場カレンダー管理（is_trading_day / next_trading_day / get_trading_days）
  - ニュース収集（fetch_rss）、前処理、news_symbols との紐付け想定
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄別ニュースセンチメント → ai_scores テーブルへ保存）
  - レジーム判定（score_regime: ETF 1321 の MA と LLM マクロセンチメントの重み合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数管理（Settings クラス）と .env 自動ロード

---

## 動作要件・依存関係

- Python 3.10 以上（型ヒントの Union 演算子 `X | Y` を使用）
- 主要依存（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリ（urllib, datetime, json, logging, 等）

実際のプロジェクトでは pyproject.toml / requirements.txt に依存を明記してください。

---

## セットアップ手順（開発環境）

1. リポジトリをクローン（例）
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows PowerShell)

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （実際は requirements.txt / pyproject.toml を参照してインストールしてください）

4. 開発パッケージとしてインストール（任意）
   - pip install -e .

---

## 環境変数（.env）と設定

パッケージ起動時、プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して自動で `.env` → `.env.local` を読み込みます。自動ロードを無効化するには環境変数を設定します:

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須となる主な環境変数（Settings 経由で参照）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY (AI モジュールで使用)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)  (デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) (デフォルト: INFO)

簡単な .env.example:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: Settings は必須値未設定時に ValueError を投げます（安全設計）。

---

## 使い方（主要な呼び出し例）

以下は簡単な Python スクリプト例です。実行前に必要な環境変数をセットしてください。

- DuckDB 接続の作成:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー / 株価 / 財務 / 品質チェック）:

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリング（OpenAI API キーは env の OPENAI_API_KEY を利用）:

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", written)
```

- 市場レジーム判定（ETF 1321 を用いる）:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（例: momentum）:

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

moms = calc_momentum(conn, date(2026, 3, 20))
# m: list[dict] each contains keys: date, code, mom_1m, mom_3m, mom_6m, ma200_dev
```

- 監査ログ DB 初期化（監査専用 DB を作る）:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査ログを操作できます
```

- RSS フィード取得（ニュース収集ヘルパ）:

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

- J-Quants 直接呼び出し（デバッグ等）:

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使う
records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
```

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/__init__.py
  - パッケージメタ（__version__）とサブパッケージ公開設定

- src/kabusys/config.py
  - 環境変数のロード・Settings クラス（アプリ設定）

- src/kabusys/ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリング（score_news）
  - regime_detector.py — MA とマクロニュースを合成した市場レジーム判定（score_regime）

- src/kabusys/data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save 関数）
  - pipeline.py — ETL のメインロジック（run_daily_etl 等）と ETLResult
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理と calendar_update_job
  - news_collector.py — RSS 収集・前処理・SSRF 対策
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付整合性）
  - stats.py — zscore_normalize など統計ユーティリティ
  - audit.py — 監査ログテーブル定義・初期化ユーティリティ

- src/kabusys/research/
  - __init__.py
  - factor_research.py — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

---

## 設計上の注意点・運用上のポイント

- ルックアヘッドバイアス対策
  - 多くのモジュール（news_nlp, regime_detector, pipeline 等）は内部で datetime.today() を直接参照せず、target_date 引数を必須または明示的に受け取る設計です。バックテストや再現性のある運用に適しています。
- 冪等性
  - J-Quants の保存関数は ON CONFLICT DO UPDATE を利用しているため、繰り返し実行しても重複データを上書きします。
- フェイルセーフ
  - LLM API の失敗時や一部 API エラーはフェイルセーフでスコアを 0 にする、またはそのチャンクをスキップする実装です（処理全体が停止しない設計）。
- 自動 .env 読み込み
  - パッケージ import 時にプロジェクトルートの .env / .env.local を自動で読み込みます。テストなどで自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- API レート制御
  - jquants_client は内部で固定間隔スロットリングとリトライを実装しています（120 req/min を想定）。
- OpenAI 呼び出し
  - AI モジュールは OpenAI の Chat Completions（JSON mode）を前提としています。API キーは OPENAI_API_KEY または関数引数で渡してください。

---

以上が README の概要です。  
この README をベースに、実際の運用向けには pyproject.toml / requirements.txt、CI 設定、詳細な運用手順（cron / scheduler での ETL 実行、監視・Slack 通知など）を追記してください。必要であればサンプル .env.example や実行スクリプトのテンプレートも作成します。どの箇所をより詳しく説明しますか？