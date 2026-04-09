# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。本リポジトリは以下を目的としたモジュール群を提供します：J-Quants からのデータ取得（ETL）、データ品質チェック、ニュース収集と LLM によるセンチメント評価、研究・ファクター計算、監査ログ（発注→約定のトレーサビリティ）、および市場レジーム判定等。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要なユースケース例）
- 環境変数一覧（主なもの）
- ディレクトリ構成
- トラブルシューティング（簡易）

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／データプラットフォーム向けに設計された Python モジュール群です。主に以下の要素を含みます。

- J-Quants API クライアント（差分取得・ページネーション・リトライ・レート制御）
- ETL パイプライン（日次差分取得、バックフィル、品質チェック）
- ニュース収集（RSS）とニュース NLP（OpenAI を用いた銘柄ごとのセンチメント）
- 市場レジーム判定（ETF の MA200 とマクロニュースを合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → executions の監査テーブル初期化）
- 市場カレンダー管理（JPX カレンダーの取得・営業日判定）
- Paper Trading / 実行監視向け設定

設計方針として「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API 失敗時はスキップして継続）」等を重視しています。

---

## 機能一覧

主な機能（抜粋）：

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
- data.pipeline
  - run_daily_etl：市場カレンダー → 株価 → 財務 → 品質チェック の日次 ETL
  - run_prices_etl / run_financials_etl / run_calendar_etl
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- data.news_collector
  - RSS 取得・前処理・記事ID生成（SSRF 対策、XML 安全化、トラッキングパラメータ削除）
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- data.audit
  - init_audit_schema / init_audit_db（監査テーブル群とインデックスを初期化）
- ai.news_nlp
  - score_news：銘柄ごとのニュースセンチメントを OpenAI に投げて ai_scores に書き込み
- ai.regime_detector
  - score_regime：ETF(1321) の MA200 乖離とマクロニュース LLM センチメントから市場レジームを判定
- research
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank
- data.stats
  - zscore_normalize（クロスセクションの Z スコア正規化）

---

## セットアップ手順

1. 前提
   - Python 3.10 以上（ソース内で `X | Y` など Python 3.10 構文を使用）
   - Git（開発時）、ネットワーク接続（API 呼び出し用）

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml
   - 他に必要な依存があれば pyproject.toml / requirements.txt を参照してインストールしてください。

4. パッケージのインストール（開発モード）
   - プロジェクトルート（pyproject.toml がある場所）で:
     - pip install -e .

5. 環境変数 / .env 準備
   - プロジェクトはプロジェクトルートの .env および .env.local を自動で読み込みます（OS 環境変数 > .env.local > .env の優先順）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須の主要環境変数例（最低限）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...（kabu ステーション連携が必要な場合）
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

---

## 使い方（主要ユースケース）

以下は Python REPL またはスクリプトからの利用例です。事前に duckdb と必要な環境変数を設定しておいてください。

- 共通の準備（接続・設定読み込み）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は環境変数で設定している前提
  written_count = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", written_count)
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/monitoring_audit.duckdb")
  # audit_conn は初期化済みの DuckDB 接続
  ```

- RSS フィード取得（ニュース収集の単体テスト等）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

- 研究用ユーティリティ（ファクター計算・正規化）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  from kabusys.data.stats import zscore_normalize

  records = calc_momentum(conn, target_date=date(2026,3,20))
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
  ```

---

## 環境変数（主なもの）

- 認証 / API
  - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
  - OPENAI_API_KEY: OpenAI の API Key（score_news, score_regime で使用）
  - KABU_API_PASSWORD: kabu ステーション API パスワード
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)

- データベース / ファイルパス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)

- Paper trading / 実行
  - PAPER_FILL_MODE (default: "instant"): instant | partial | never | reject

- 監視 / 実行制御
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1)

- システム設定
  - KABUSYS_ENV (development | paper_trading | live)（default: development）
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)（default: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化

注意: 必須変数が未設定のままアクセスした場合、Settings が ValueError を送出します（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイルと役割の一覧です（抜粋）。

- src/kabusys/
  - __init__.py                — パッケージ初期化（__version__ 等）
  - config.py                  — 環境設定読み込み・Settings クラス（.env 自動ロード）
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py                — ニュースから銘柄別 AI スコアを算出し ai_scores に保存
  - regime_detector.py         — 市場レジーム判定（ETF MA200 + マクロNEWS）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py          — J-Quants API クライアント（fetch/save）
  - pipeline.py                — ETL パイプライン＆run_daily_etl
  - quality.py                 — データ品質チェック
  - news_collector.py          — RSS 収集・前処理（SSRF / XML 対策）
  - calendar_management.py     — 市場カレンダー管理・営業日判定
  - audit.py                   — 監査（監査テーブル定義・初期化）
  - etl.py                     — ETLResult の再エクスポート
  - stats.py                   — 汎用統計ユーティリティ（zscore_normalize）
- src/kabusys/research/
  - __init__.py
  - factor_research.py         — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py     — forward_returns / IC / factor_summary / rank

（上記以外にも strategy / execution / monitoring のサブパッケージ等が想定されていますが、コードベースに応じて展開されます。）

---

## トラブルシューティング（簡易）

- OPENAI_API_KEY がない／未設定
  - score_news や regime_detector の呼び出しで ValueError が出ます。環境変数か引数でキーを渡してください。

- JQUANTS_REFRESH_TOKEN が未設定
  - jquants_client.get_id_token() または ETL 実行で ValueError が出ます。.env に設定してください。

- .env が読み込まれない
  - settings モジュールはプロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動ロードします。自動ロードを無効にしたい／テストしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DuckDB 関連
  - コネクションを作成する際、settings.duckdb_path の親ディレクトリがなければ自動で作られる箇所と、手動で作成が必要な箇所があります（init_audit_db は親ディレクトリを作成します）。パス権限等に注意してください。

---

この README はコードベースに含まれるモジュール・設計コメントに基づいて作成しています。詳細な API（関数引数や戻り値）はソースコードの docstring を参照してください。必要であれば、各モジュールのより詳細な使い方やサンプルを追記します。