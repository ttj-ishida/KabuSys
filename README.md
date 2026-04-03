# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、データ品質チェック、ニュース収集・NLP（OpenAI 経由）によるセンチメントスコア、マーケットレジーム判定、研究用ファクター計算、監査ログなどを提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0 (src/kabusys/__init__.py)

---

## プロジェクト概要

KabuSys は以下の主要機能を備えたモジュール群です。

- J-Quants API からの差分取得（株価・財務・上場情報・カレンダー）
- DuckDB を用いたデータ保存と冪等保存ロジック
- ETL パイプライン（run_daily_etl 等）と品質チェック
- ニュース収集（RSS）と前処理、NLP による銘柄別センチメントスコア化（OpenAI）
- マーケットレジーム判定（ETF MA + マクロニュース × LLM）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、正規化など）
- 監査ログ（signal / order_request / executions テーブル）の初期化ユーティリティ
- 環境設定の一括管理（.env 自動読み込み、settings）

設計方針の主要点は「Look-ahead bias の排除」「冪等性」「API 呼び出しのリトライとレート制御」「DuckDB を中心としたローカルデータ管理」「外部 API 呼び出しの失敗時のフェイルセーフ」です。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API への厳格なリトライ・レート制御実装
  - fetch / save のペアで差分取得と冪等保存を提供
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
  - save_daily_quotes, save_financial_statements, save_market_calendar

- data.pipeline
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の日次 ETL を実行
  - run_prices_etl, run_financials_etl, run_calendar_etl（個別ジョブ）

- data.quality
  - 欠損・スパイク・重複・日付不整合などの品質チェック（QualityIssue を返す）

- data.news_collector
  - RSS フィード取得（SSRF 対策、トラッキングパラメータ除去、XML 安全パーサ）
  - preprocess_text, fetch_rss（NewsArticle 型）

- ai.news_nlp / ai.regime_detector
  - ニュースをまとめ、OpenAI（gpt-4o-mini, JSON mode）で銘柄別センチメントを取得して ai_scores に書き込み
  - レジーム判定: ETF(1321) の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し market_regime に保存

- research
  - calc_momentum, calc_value, calc_volatility（ファクター）
  - calc_forward_returns, calc_ic, factor_summary, rank（分析ユーティリティ）
  - data.stats.zscore_normalize（Zスコア正規化）

- data.calendar_management
  - market_calendar を用いた営業日判定 / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（J-Quants からの差分更新ジョブ）

- data.audit
  - 監査ログ用 DDL/インデックス定義
  - init_audit_schema / init_audit_db（監査 DB 初期化）

- config
  - .env 自動読み込み（プロジェクトルート .git または pyproject.toml を基準）
  - Settings クラスによる環境変数アクセス（必須値チェックやデフォルト）

---

## セットアップ手順

前提:
- Python 3.10 以上（| 型ヒント、match などの利用を想定）
- DuckDB、OpenAI SDK、defusedxml などが必要

推奨手順（プロジェクトルートに pyproject.toml / setup ありと想定）:

1. リポジトリをクローンして、editable インストール（開発向け）
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate    # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install -e ".[dev]"      # または pip install -e .
   ```

2. 依存パッケージの例（必要に応じて pyproject.toml に従ってください）
   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動でロードされます。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY (for AI モジュール)
     - KABU_API_PASSWORD (kabuステーション API)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知/モニタリング用、任意）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, default: data/monitoring.db)
     - KABUSYS_ENV (development / paper_trading / live, default: development)
     - LOG_LEVEL (DEBUG/INFO/..., default: INFO)

   .env の自動パースは quotes, export 形式, コメントなどを考慮した実装になっています。

---

## 使い方（主な例）

以下はライブラリの代表的な利用例です。各関数は duckdb 接続を受け取る設計です。

1) DuckDB 接続を作成して ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP（ai_scores の書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"wrote {written} scores")
```

3) 市場レジームの評価（market_regime に書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

5) RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意点:
- OpenAI を使う関数（score_news / score_regime）は OPENAI_API_KEY を引数で渡すか環境変数で設定してください。
- 各 ETL / 保存関数は冪等なので、複数回実行しても重複した行を上書きして扱います（ON CONFLICT / executemany を利用）。
- DuckDB の executemany は空リストを受け付けない点に配慮した実装になっています。

---

## 環境変数（主な一覧）

（設定は kabusys.config.Settings 経由で取得されます）

必須:
- JQUANTS_REFRESH_TOKEN

任意 / デフォルトあり:
- OPENAI_API_KEY (LLM 呼び出し用)
- KABU_API_PASSWORD
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- CPU_THRESHOLD_PCT (default: 90.0)
- MEMORY_THRESHOLD_PCT (default: 85.0)
- DISK_THRESHOLD_PCT (default: 90.0)
- KABUSYS_ENV (development / paper_trading / live; default: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL; default: INFO)

詳細は src/kabusys/config.py を参照してください。

---

## ディレクトリ構成（主要ファイル）

（抜粋: src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py (ETLResult 再エクスポート)
    - quality.py
    - news_collector.py
    - calendar_management.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各モジュールの責務はファイル冒頭の docstring（ソースコード）に記載されています。実装は DuckDB を前提にしており、外部 API 呼び出し箇所はリトライ/フェイルセーフが組み込まれています。

---

## 開発・テスト

- 自動読み込みされる .env の挙動を無効化してユニットテストを実行したい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  pytest
  ```

- OpenAI / J-Quants 呼び出し部分は関数単位でモック可能な設計（内部の _call_openai_api や _urlopen を patch）になっています。テストでは外部 API に依存せず検証できます。

---

## ライセンス / 貢献

（リポジトリの LICENSE を参照してください）

バグ報告、機能提案、プルリクエストは歓迎します。まず Issue を立ててください。

---

以上。詳細な API や実装方針はソース（src/kabusys 配下）を参照してください。README に記載のない利用上の疑問や具体的な実装の説明が必要であれば教えてください。