# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
このリポジトリはデータ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、及び監査ログ（オーダー/約定トレーサビリティ）を含むユーティリティセットを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の運用・リサーチ基盤を構築するための内部ライブラリ群です。主な目的は：

- J-Quants API を用いた株価・財務・カレンダーの差分取得（ETL）
- ニュース収集と OpenAI による銘柄/マクロのセンチメント評価（JSON Mode を用いた堅牢な呼び出し）
- 市場レジーム（bull/neutral/bear）の判定（ETF + マクロセンチメントの合成）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- DuckDB を利用したオンディスクデータ管理

設計上の留意点：
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を直接参照しない関数設計）
- API 呼び出しはリトライ／バックオフ／フェイルセーフで堅牢に実装
- DuckDB への保存は冪等（ON CONFLICT）で運用を意識

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API からの取得と DuckDB への保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline: 日次 ETL 実行（run_daily_etl）と個別 ETL ヘルパー
  - news_collector: RSS 収集 -> raw_news 保存（SSRF 対策・gzip/サイズ制限）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 営業日判定・前後営業日の取得、calendar_update_job
  - audit: 監査ログテーブルの初期化 / audit DB ユーティリティ
  - stats: zscore_normalize などの統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores へ書き込み
  - regime_detector.score_regime: ETF(1321)のMA乖離とマクロセンチメントを合成して market_regime を更新
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

1. リポジトリをクローン / 作業ディレクトリを用意

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 代表的な依存:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込む（優先度: OS env > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 必要なディレクトリを作成（例）
   - data/ フォルダ（デフォルトの DuckDB ファイルパスが data/kabusys.duckdb）

---

### 推奨 / 必須環境変数

（.env ファイル例は下に示します）

必須：
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client で使用）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用、関数引数でも渡せる）
- SLACK_BOT_TOKEN: （Slack 通知を使う場合）
- SLACK_CHANNEL_ID: （Slack 通知を使う場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（必要な機能で使用）

任意（デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL （デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると .env 自動ロードを無効化
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi

例 (.env.example)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要ユースケース・サンプル）

以降の例は Python REPL / スクリプト内で実行します。

基本的な前提：
- settings を通して環境変数にアクセスできます（kabusys.config.settings）

1) DuckDB 接続を開いて ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

2) ニュースセンチメント（銘柄単位）をスコア付けして ai_scores に保存
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None だと OPENAI_API_KEY 環境変数を使用
print(f"written {written} codes")
conn.close()
```

3) 市場レジーム判定（ETF 1321 + マクロセンチメント）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
conn.close()
```

4) 監査ログ（audit）スキーマの初期化 / 専用 DB を作る
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 既存の main DuckDB を使う場合:
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
conn.close()

# 監査専用 DB を作成する場合:
audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルにアクセスできます
audit_conn.close()
```

5) RSS フィードを取得して raw_news にインサートする（簡易）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

items = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
# items は NewsArticle のリスト（id, datetime, source, title, content, url）
```

---

## よく使う API / 関数一覧

- ETL / data
  - kabusys.data.pipeline.run_daily_etl(...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
  - kabusys.data.quality.run_all_checks(...)
  - kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days
- AI
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- Research
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
- Audit
  - kabusys.data.audit.init_audit_schema(conn, transactional=False)
  - kabusys.data.audit.init_audit_db(path)

---

## ログ・環境設定

- KABUSYS_ENV: 開発・ペーパートレード・本番を切り替えるフラグ（development / paper_trading / live）
- LOG_LEVEL: ログレベル（デフォルト INFO）
- .env の自動ロードは kabusys.config モジュールがプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を検出した場合に行います。テストなどで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

リポジトリの主なファイル/ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント / 保存ロジック
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult 再エクスポート
    - news_collector.py            — RSS 収集・前処理
    - quality.py                   — データ品質チェック
    - calendar_management.py       — マーケットカレンダー管理
    - stats.py                     — 統計ユーティリティ
    - audit.py                     — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum/value/volatility）
    - feature_exploration.py       — 将来リターン / IC / summary 等
  - monitoring/ (存在するなら監視用コード)
  - execution/  (発注実行層：kabuステーション等の橋渡しモジュール想定)
  - strategy/   (戦略実装用のユーティリティ想定)

---

## 注意事項 / 運用上の留意点

- OpenAI API 呼び出しは gpt-4o-mini を使用する想定で JSON Mode を利用した厳格なパースを行っています。API 失敗時はフェイルセーフ（0.0 フォールバック等）を取り入れていますが、利用量に応じたレート制御やコスト管理を行ってください。
- J-Quants API はレート制限とトークン管理（リフレッシュ）が組み込まれています。JQUANTS_REFRESH_TOKEN を正しく設定してください。
- ETL は差分取得とバックフィル（既存の最終取得日から数日前を再取得）を行い API の後出し修正に耐性を持たせています。
- DuckDB への executemany 空リストバインド制約等に配慮した実装が含まれています。DuckDB バージョン互換性に注意してください。
- 監査ログは削除しない前提で設計されています（ON DELETE RESTRICT）。監査テーブルは冪等に初期化できます。

---

## 開発・貢献

- コードの改善やテスト追加は歓迎します。プロジェクトルートに pyproject.toml / .git を配置しておくと config の自動 .env 読み込みに便利です。
- 単体テストでは外部 API 呼び出し（OpenAI / J-Quants / HTTP）をモックしてください。ライブラリ内にモック差替えを想定した抽象化ポイント（_call_openai_api 等）があります。

---

必要であれば README に以下を追加できます：
- 具体的な .env.example ファイル
- CI / テスト実行手順
- 詳細な API リファレンス（関数一覧 + 引数・戻り値の説明）
- デプロイ / 運用ガイド（cron / Airflow による ETL スケジューリング例）

ご希望があれば上記の追記を作成します。