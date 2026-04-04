# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants からのデータ取得・ETL、ニュース収集・NLP スコアリング、ファクター計算、監査ログ（オーダー追跡）など、売買システムや研究環境で必要となる主要機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 簡単な使い方（例）
- 環境変数（.env）
- ディレクトリ構成（主要ファイルと主要 API）

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインと研究・実行コンポーネント群を備えたライブラリ群です。主な目的は次のとおりです。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントの取得（銘柄別 ai_score、マクロセンチメント）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究ツール（IC・統計サマリ）
- 監査用のデータベーススキーマ（シグナル → 発注 → 約定 のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴：
- DuckDB を主要な永続ストレージとして使用
- Look-ahead バイアス対策（ターゲット日ベースのウィンドウ設計）
- API 呼び出しはリトライ・バックオフ・レート制御を実装
- 冪等（idempotent）保存（ON CONFLICT / DELETE→INSERT のパターン）

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）
  - news_collector: RSS 収集、前処理、記事ID生成（SSRF 対策あり）
  - calendar_management: 営業日判定、next/prev trading day、calendar_update_job
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp: 銘柄別ニュースセンチメント取得（score_news）
  - regime_detector: マクロセンチメントと ETF MA を合成して市場レジーム判定（score_regime）
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config.py
  - Settings: 環境変数管理（.env 自動ロード機能、必須設定チェック）

---

## セットアップ手順

前提:
- Python 3.10+（typing の一部に union | 記法が使われています）
- システムに DuckDB をインストールできる環境（pip パッケージで OK）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - このコードベースで想定される主要依存:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 実プロジェクトでは requirements.txt / pyproject.toml を参照してください。

4. 環境変数の設定
   - プロジェクトルートに `.env` と `.env.local` を置くと自動でロードされます（設定は後述）。
   - 自動ロードを無効化するには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 簡単な使い方（例）

※ 下記はライブラリを直接インポートして使う例です。実運用では各種エラーハンドリングやログ設定を行ってください。

- ETL（日次）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別 ai_scores への書き込み）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("written codes:", written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（例: momentum）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  print(len(records))
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/monitoring.db")
  ```

- RSS フェッチ（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

---

## 環境変数（.env）

config.Settings により .env ファイル（プロジェクトルート）を自動読み込みします。主な環境変数:

必須（アプリで使う機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 実行時に必要）
- KABU_API_PASSWORD: kabu ステーション API を使う場合

任意:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知設定
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH: 実行監視用ファイルパス
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

.env 自動ロードに関する挙動:
- 読み込み優先度: OS 環境変数 > .env.local > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 主な設計上の注意点

- Look-ahead バイアス対策: 各処理は target_date を明示的に受け、内部で datetime.today() や date.today() を使わないよう設計されています（バックテストでの利用を想定）。
- 冪等性: ETL 保存関数は既存データを上書きして整合性を保ちます（ON CONFLICT など）。
- API 呼び出し: J-Quants / OpenAI の呼び出しにはリトライ・バックオフ・レートリミットが実装されています。OpenAI 呼び出しは JSON Mode を利用する想定。
- テスト容易性: 一部の内部 API 呼び出しはモック交換可能（例: _call_openai_api を unittest.mock.patch で置き換え可能）。

---

## ディレクトリ構成（抜粋）

以下はソースの主要構成（src/kabusys 配下）です。ファイル名と主要な公開 API を示します。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py  (score_news を re-export)
    - news_nlp.py  (score_news)
    - regime_detector.py  (score_regime)
  - data/
    - __init__.py
    - jquants_client.py
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
      - save_daily_quotes, save_financial_statements, save_market_calendar
      - get_id_token
    - pipeline.py
      - ETLResult, run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
    - etl.py (ETLResult をエクスポート)
    - news_collector.py
      - fetch_rss, preprocess_text, _normalize_url 等
    - calendar_management.py
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
    - quality.py
      - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
    - stats.py
      - zscore_normalize
    - audit.py
      - init_audit_schema, init_audit_db
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_value, calc_volatility
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank
  - monitoring/ (存在する場合は監視/実行モジュール)

各モジュールのドキュメントはソース内の docstring に設計方針・処理フローが記載されています。実装を拡張する際は既存の docstring を参照してください。

---

## 追加情報・運用上の注意

- OpenAI API を使う機能は API コストとレート制限に注意して運用してください。score_news/regime_detector はバッチでの利用を想定しています。
- J-Quants の API レート制限を遵守するために _RateLimiter を実装しています。大量データを取得する際は間隔やページネーションを考慮してください。
- DuckDB に対する executemany の挙動（空リスト渡しの制約など）をコード内で考慮しています。DuckDB のバージョン互換性に注意してください。
- 監査ログ（audit schema）は削除しない前提で設計されています。スキーマ初期化は冪等です。

---

何か README の追加項目（詳細な API リファレンス、例スクリプト、環境ごとの設定例など）が必要であれば教えてください。必要に応じてサンプル .env.example も作成します。