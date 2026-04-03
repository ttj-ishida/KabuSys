# KabuSys

日本株のデータ取り込み・研究・自動売買を支援するライブラリ群です。  
ETL（J-Quants）→ データ品質チェック → ファクター計算 → ニュースNLP（OpenAI） → 市場レジーム判定 → 監査ログ（約定トレース）までのワークフローを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けのデータパイプライン・リサーチ・監視・監査機能をまとめたPythonパッケージです。主な用途は：

- J-Quants API からの株価・財務・カレンダーの差分ETL（DuckDB保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター（モメンタム／バリュー／ボラティリティ等）の計算と探索ツール
- ニュースを用いた銘柄単位のセンチメントスコアリング（OpenAI）
- ETFベース + マクロニュースによる市場レジーム判定（bull/neutral/bear）
- 発注／約定の監査ログ用スキーマ（DuckDB）と初期化ユーティリティ
- ニュースRSS収集（SSRF対策・トラッキングパラメータ除去）

設計上の特徴として、ルックアヘッドバイアス対策（内部で date.today()/datetime.today() を直接参照しない等）、冪等性（DB書き込みは ON CONFLICT / DELETE→INSERT を利用）および堅牢な外部API呼び出し（レート制御・リトライ・フェイルセーフ）を備えます。

---

## 機能一覧

- data (J-Quants クライアント・ETL・カレンダー・ニュース収集・品質チェック・監査ログ)
  - fetch / save: daily_quotes, financial_statements, market_calendar, listed_info
  - ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - データ品質チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
  - カレンダー管理: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
  - ニュース収集: fetch_rss, preprocess_text（SSRF対策・トラッキング除去）
  - 監査ログスキーマ初期化: init_audit_schema, init_audit_db
- ai (ニュースNLP・レジーム判定)
  - score_news: raw_news → ai_scores（OpenAI を使用）
  - score_regime: ETF(1321) の MA とマクロニュースを合成して market_regime へ書込
- research (ファクター計算・特徴量探索)
  - calc_momentum, calc_value, calc_volatility
  - calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
- config
  - 環境変数読み込みと settings オブジェクト（.env 自動ロード機能あり）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に `X | Y` 構文を使用）
- ネットワークアクセス（J-Quants / OpenAI を利用する場合）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに packaging/requirements ファイルがあればそれを使用してください）

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（config.py の自動ロード）。
   - 自動ロードを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定

必須環境変数（主に ETL / API 呼び出しで必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime を実行する場合）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注系を利用する場合）

任意／デフォルトを持つ環境変数（例）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1, default: 0)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live, default: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, default: INFO)

例: .env の最小例
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=xxx
KABU_API_PASSWORD=your_kabu_password

---

## 使い方（主要なユースケース）

以下は Python REPL やスクリプトからの呼び出し例です。

- DuckDB 接続を作成して ETL を実行する（run_daily_etl）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメントスコアを計算して ai_scores テーブルに書き込む
  - 必要: OPENAI_API_KEY を環境変数に設定する（または api_key 引数を使用）
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print("書き込み銘柄数:", n_written)

- 市場レジーム（ETF 1321 + マクロニュース）を判定する
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用 DuckDB の初期化（監査専用DBを作る場合）
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # 必要に応じて同接続を使って order_requests / executions 等を記録

- カレンダー関連ユーティリティ
    from datetime import date
    import duckdb
    from kabusys.data.calendar_management import is_trading_day, next_trading_day
    conn = duckdb.connect("data/kabusys.duckdb")
    d = date(2026, 3, 20)
    print(is_trading_day(conn, d))
    print(next_trading_day(conn, d))

- 研究用途（ファクター・forward returns）
    from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    mom = calc_momentum(conn, date(2026, 3, 20))
    # 結果は dict のリスト

注意点
- OpenAI を呼ぶ関数（score_news, score_regime）は API キーが必須です。
- ETL/保存系は DuckDB のテーブルスキーマが前提になっているため、最初にスキーマの用意・初期化を行ってください（プロジェクトに schema 初期化ユーティリティがあればそれを利用）。
- 外部API呼び出しはレート制御やリトライを備えていますが、実行時のネットワーク状況・API制限に注意してください。

---

## 自動環境変数読み込みの挙動

`kabusys.config` モジュールは、以下の順で自動的に `.env` を読み込みます（プロジェクトルートが見つかった場合）:

1. OS 環境変数（優先）
2. .env.local （override=True、既存OS環境変数を保護）
3. .env （override=False）

プロジェクトルートは、`__file__` から親ディレクトリをさかのぼり `.git` または `pyproject.toml` を検出して決定します。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

環境値にアクセスするには：
from kabusys.config import settings
token = settings.jquants_refresh_token

未設定の必須値を参照すると ValueError が発生します。

---

## ディレクトリ構成

（パッケージルート: src/kabusys/ 以下）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI）/ score_news
    - regime_detector.py     — 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py            — ETL パイプライン run_daily_etl 等
    - etl.py                 — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py      — RSS 収集 / 前処理 / SSRF 対策
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / バリュー / ボラティリティ 等
    - feature_exploration.py — forward returns / IC / summary / rank
  - ai, data, research の公開 API はそれぞれの __init__.py で整理されています

---

## 開発・テスト時のヒント

- 自動 .env ロードをテストで制御したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してから明示的に環境を設定してください。
- OpenAI 呼び出しをユニットテストで差し替えるため、モジュール内の `_call_openai_api` をモックする設計になっています（news_nlp._call_openai_api, regime_detector._call_openai_api）。
- J-Quants クライアントは内部でトークンキャッシュと RateLimiter を使用しています。get_id_token は refresh token を必要とします。

---

## ライセンス / コントリビューション

（このリポジトリのライセンス／貢献ルールをここに追記してください）

---

必要であれば README に実際に使える .env.example、DB スキーマ初期化手順、さらに詳細な API リファレンス（各関数の引数例と戻り値）を追加します。どの部分を詳しく書くか指定してください。