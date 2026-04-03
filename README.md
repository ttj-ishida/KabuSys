# KabuSys

日本株向けの自動売買およびデータプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得・保存）、ニュースの NLP スコアリング、銘柄ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）などの機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を不用意に参照しない）
- DuckDB をデータストアとして利用し SQL + Python で処理
- OpenAI（gpt-4o-mini）や J-Quants API と連携（リトライ・バックオフ等の堅牢化）
- ETL / 品質チェック / 監査ログを冪等かつ追跡可能に実行

---

## 特徴（機能一覧）

- 設定管理
  - .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - 各種環境変数をラップした `kabusys.config.settings`

- データ取得・ETL
  - J-Quants API クライアント（差分取得・ページネーション・トークン自動更新・レート制御）
  - ETL パイプライン（株価 / 財務 / カレンダーの差分取得・保存・品質チェック）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）

- ニュース収集・NLP
  - RSS フィード取得（SSRF 対策、トラッキングパラメータ削除、サイズ制限）
  - OpenAI を使ったニュースセンチメントスコアリング（銘柄別 ai_scores 生成）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA と LLM の組合せ）

- 研究用ユーティリティ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、Zスコア正規化、統計サマリー

- 監査ログ（オーダー／シグナルトレーサビリティ）
  - signal_events, order_requests, executions テーブルの初期化ユーティリティ
  - 監査 DB 初期化（UTC タイムゾーン固定、冪等的 DDL）

---

## セットアップ

前提
- Python 3.9+（コードは型注釈に union などを使っているため 3.9+ を想定）
- DuckDB、OpenAI SDK 等の依存パッケージが必要

例（仮想環境推奨）:

1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ プロジェクトで setuptools/poetry などが用意されている場合はそれを使ってインストールしてください。

3. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（優先度: OS 環境変数 > .env.local > .env）。
   - 必須（最低限）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
   - OpenAI を使う機能を使う場合:
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で利用）
   - 設定可能な変数（一部）:
     - KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - KABUSYS_ENV（development, paper_trading, live）
     - LOG_LEVEL（DEBUG, INFO, ...）
   - 自動ロードを無効化したい場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要な利用パターン）

以下はライブラリを Python スクリプトから利用する例です。

1) DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 監査ログ（audit）テーブルの初期化
```python
from kabusys.data.audit import init_audit_schema

# 既存 conn に監査スキーマを追加（transactional=True で BEGIN/COMMIT）
init_audit_schema(conn, transactional=True)
```
または専用 DB を作る:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

3) 日次 ETL 実行（J-Quants からの差分取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は本日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
# ETLResult オブジェクトで結果を参照
print(result.to_dict())
```

4) ニュースのセンチメントスコアを生成（OpenAI 必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# API キーは env OPENAI_API_KEY、引数 api_key でも指定可
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

5) 市場レジーム（マクロ + ETF MA）を判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

6) 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, date(2026, 3, 20))
volatility = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

7) RSS フィード取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
# raw_news への保存処理はプロジェクト側の実装に沿って行ってください
```

注意点:
- OpenAI 呼び出しはコストとレート制限に注意してください。score_news/score_regime は自動リトライやフォールバックを備えていますが、APIキーの設定が必要です。
- ETL 実行は DB スキーマ（raw_prices, raw_financials, market_calendar など）が前提となります。初回はスキーマ作成ユーティリティを用意しているケース（プロジェクト側）を参照してください。
- DuckDB の executemany に空リストを渡すと問題となるバージョンがあるため、内部実装で空チェックを行っています。

---

## 主要モジュールとディレクトリ構成

リポジトリ内の主要なモジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動ロード / settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの NLP スコアリング（score_news）
    - regime_detector.py — マクロ + ETF MA による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch_* / save_*）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py— マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py     — RSS 収集・前処理（fetch_rss 等）
    - quality.py            — データ品質チェック（check_missing_data 等）
    - stats.py              — 共通統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログテーブル定義・初期化（init_audit_schema / init_audit_db）
    - etl.py                — ETL 結果型の再エクスポート（ETLResult）
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum, value, volatility）
    - feature_exploration.py— 将来リターン、IC、統計サマリー

---

## 設定一覧（主要環境変数）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- OPENAI_API_KEY (OpenAI を使う場合)
- KABU_API_PASSWORD, KABU_API_BASE_URL (kabu API を使う場合)
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視情報などに使用）
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（INFO 等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 （自動 .env ロードを無効化）

設定は `from kabusys.config import settings` で取得できます。

---

## テスト・開発時の補助

- 自動環境読み込みを無効にする:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出し / ネットワーク呼び出しはユニットテストでモックする設計（内部の _call_openai_api や _urlopen をパッチ可能）
- DuckDB は ":memory:" を渡すことでインメモリ DB をテストに利用可能（init_audit_db 等も対応）

---

この README はコードの主要な使い方と設計方針をまとめたものです。実際の運用では DB スキーマ定義（raw_prices / raw_financials / raw_news / ai_scores / market_regime など）や初期化手順、監視／運用スクリプト（プロセス管理、PID ファイル、キルフラグ）をプロジェクト固有に整備してください。必要であればサンプルの run script や docker-compose などの運用手順も追記できます。