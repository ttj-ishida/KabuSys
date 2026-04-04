# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants）→ データ品質チェック → ファクター計算 → ニュースNLP / レジーム判定 → 監査ログの一連処理を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ取得・前処理・研究・AI 情報合成・監査トレースを一貫して扱うための内部ライブラリです。主な目的は以下です。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- DuckDB をデータレイヤーとして利用した高速処理
- ニュース記事の収集と LLM によるセンチメント評価（gpt-4o-mini を想定）
- ETF とマクロニュースを組み合わせた市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）と探索ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（signal -> order_request -> executions）のテーブル初期化ユーティリティ

設計上、バックテストでのルックアヘッドバイアスを避けるために「target_date を明示的に与える」形で日時依存を最小化しています。

---

## 機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（取得 + 保存の冪等処理、レートリミット・リトライ対応）
  - マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS フィード収集、SSRF 対策、正規化）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai/
  - ニュース解析（score_news: ニュースを銘柄ごとに LLM でスコア化して ai_scores テーブルへ保存）
  - レジーム判定（score_regime: ETF(1321)のMA乖離 + マクロセンチメントで日次レジーム判定）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - .env の自動読み込み（プロジェクトルート検出）と環境変数ラッパ
  - settings オブジェクト経由で設定にアクセス（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY は外部提供）

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈で | を使用しているため）
- システムにネットワーク接続（J-Quants / OpenAI 等）

1. リポジトリをクローン／チェックアウト
   - 例: git clone <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   - 基本的に以下をインストールしてください（setup.py / pyproject があればそちらに従ってください）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     pip install duckdb openai defusedxml

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な主要環境変数:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY (必要に応じて) — OpenAI API キー（score_news / score_regime で使用）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必要時）
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 sqlite（デフォルト: data/monitoring.db）
     - その他: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, KABUSYS_ENV, LOG_LEVEL など
   - 例 .env（最小）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb

5. データディレクトリ作成（必要に応じて）
   mkdir -p data

---

## 使い方（基本例）

以下はライブラリの主な利用例です。実行前に DuckDB のスキーマ（raw_prices 等）を用意してください（ETL が自動で作ることもできますが、schema の初期化はプロジェクトポリシーに依存します）。

- DuckDB に接続して日次 ETL を実行する
  - 例:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメントをスコアリングして ai_scores に保存する
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    # OPENAI_API_KEY は環境変数か api_key 引数で渡す
    written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
    print(f"scored {written} codes")

- 市場レジームを判定して market_regime テーブルに保存する
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ用の DuckDB を初期化する
  - 例:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/monitoring_audit.duckdb")
    # これで signal_events / order_requests / executions 等が作成される

- マーケットカレンダーのユーティリティ
  - is_trading_day(conn, d), next_trading_day(conn, d), get_trading_days(conn, s, e) など

注意点:
- score_news / score_regime は OpenAI API を呼び出します。api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL / J-Quants 関連は J-Quants のトークン（JQUANTS_REFRESH_TOKEN）が必要です。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。settings.jquants_refresh_token で取得されます。
- OPENAI_API_KEY
  - OpenAI API キー（score_news / score_regime 用）。
- KABU_API_PASSWORD
  - kabuステーション API のパスワード。
- KABU_API_BASE_URL
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）。
- DUCKDB_PATH
  - デフォルト DuckDB ファイルパス（data/kabusys.duckdb）。
- SQLITE_PATH
  - 監視 DB（data/monitoring.db など）。
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
  - 実行監視・プロセスマネジメント用の設定。
- KABUSYS_ENV
  - environment: "development" | "paper_trading" | "live"
- LOG_LEVEL
  - ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml）を検出し、`.env` → `.env.local` の順で読み込みます。
- 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成

主要ファイルと役割を簡潔に示します（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / settings
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースを LLM でスコア化（score_news）
    - regime_detector.py    — ETF + マクロで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py— マーケットカレンダー管理
    - news_collector.py     — RSS 収集・前処理
    - quality.py            — データ品質チェック
    - stats.py              — zscore_normalize 等
    - audit.py              — 監査ログテーブル作成 / init_audit_db
    - etl.py                — ETL 用型再エクスポート
  - research/
    - __init__.py
    - factor_research.py    — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py— calc_forward_returns / calc_ic / factor_summary / rank

---

## 実運用上の注意

- API キーとトークンは適切に管理してください（環境変数利用・シークレット管理を推奨）。
- OpenAI 呼び出しはコストとレート制限に注意。score_news はバッチ化（最大 _BATCH_SIZE）して呼び出しますが、API 利用料がかかります。
- DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, ai_scores, market_regime, 等）は ETL 実行前に整備してください。ETL/保存ロジックは ON CONFLICT DO UPDATE を使用して冪等性を保つよう設計されています。
- ニュース取得は外部 RSS を扱うため SSRF 対策や取得サイズ上限を入れていますが、外部データの扱いには常に注意してください。
- テスト時は環境自動ロードを無効化する（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）か、settings をモックしてください。

---

## 追加情報 / 開発者向け

- ロギングはモジュール毎に logger.getLogger(__name__) を使っています。アプリケーション側でハンドラ・フォーマットを設定してください。
- テストを行う際は外部 API 呼び出し点（OpenAI / urllib / J-Quants）をモックすることを推奨します。コード中にテスト差し替えが想定された内部関数（例: _call_openai_api, _urlopen 等）があります。
- 型注釈が広範なので static type check（mypy 等）による検証が有効です。

---

必要であれば、この README を元に:
- .env.example のテンプレート
- docker / docker-compose によるローカル実行手順
- サンプルスクリプト（daily_run.py など）の追加
を作成します。どれを優先したいか教えてください。