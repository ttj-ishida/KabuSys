KabuSys — 日本株自動売買プラットフォーム
======================================

概要
----
KabuSys は日本株向けのデータプラットフォーム兼リサーチ / 自動売買基盤のライブラリ群です。
主に以下を目的としています。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL
- ニュースの収集・NLP による銘柄センチメント算出（OpenAI を利用）
- 市場レジーム判定（MA200 とマクロニュースの組合せ）
- ファクター計算・特徴量探索・IC 計算（研究用途）
- 発注・約定の監査ログスキーマ（DuckDB）と監査テーブル初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）

主な機能一覧
-------------
- データ取得 / ETL
  - J-Quants からの daily_quotes / financial_statements / trading_calendar の差分取得
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）する save_* 関数
  - 日次 ETL エントリ run_daily_etl（calendar → prices → financials → 品質チェック）
- ニュース収集・処理
  - RSS 取得（SSRF 対策・トラッキング除去・前処理）と raw_news 保存
  - ニュース前処理（URL 除去・空白正規化）と記事 ID 生成
- NLP（OpenAI）
  - score_news: 指定日のニュースウィンドウで銘柄ごとのセンチメントを計算し ai_scores に書込
  - score_regime: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書込
  - それぞれ API のリトライやフェイルセーフあり（失敗時は 0 にフォールバックする等）
- Research（因子計算・探索）
  - calc_momentum / calc_volatility / calc_value：各種ファクターを DuckDB 上で SQL + Python で計算
  - calc_forward_returns / calc_ic / factor_summary / rank：将来リターン・IC・統計サマリー
  - zscore_normalize（クロスセクション Z スコア正規化）
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- 監査ログ（Audit）
  - 監査用テーブル定義（signal_events / order_requests / executions）を DuckDB に初期化する init_audit_schema / init_audit_db
- 設定管理
  - .env / .env.local / OS 環境変数から設定をロードする config.Settings（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）

セットアップ手順
----------------

1. Python 環境の準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 代表的な依存例:
     - duckdb
     - openai
     - defusedxml
     - （requests 等を利用する場合は追加）
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）

3. リポジトリのインストール（開発モード）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に .env / .env.local を置くと自動でロードされます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須の主な環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に必要）
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注実装時等）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV: development / paper_trading / live（default: development）
     - LOG_LEVEL: DEBUG/INFO/...（default: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   - .env の書式：
     - KEY=VALUE、' または " で囲める、export PREFIX=VALUE 形式も許容。
     - コメント行と空行をサポート。

使い方（主要な API 例）
----------------------

前提: duckdb 接続作成
- 例:
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

ETL 実行（日次）
- 日次 ETL（カレンダー・株価・財務・品質チェックの一括実行）:
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

ニューススコアリング（OpenAI 必須）
- 銘柄ごとのニュースセンチメントを計算して ai_scores に書き込む:
  from kabusys.ai.news_nlp import score_news
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} codes")

市場レジーム判定（OpenAI 必須）
- ETF(1321) の MA200 とマクロニュースを合成して market_regime に書込:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

監査 DB 初期化（発注監査用）
- 監査用 DuckDB を初期化して接続を得る:
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーンが適用される

ファクター計算 / リサーチ
- モメンタムやボラティリティ等を計算:
  from kabusys.research.factor_research import calc_momentum
  factors = calc_momentum(conn, target_date=date(2026,3,20))
  # zscore 正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(factors, ["mom_1m", "mom_3m", "ma200_dev"])

データ品質チェック
- run_all_checks でまとめて品質検査:
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)

設定・デバッグ
- 環境判定: settings.is_live / is_paper / is_dev
  from kabusys.config import settings
  print(settings.env, settings.log_level)

注意点 / 設計上の特徴
--------------------
- Look-ahead バイアス防止:
  - モジュール内の多くの処理は datetime.today() や date.today() を直接参照せず、明示的な target_date を引数として受け取る設計です。
  - ETL や NLP、レジーム判定は過去データのみを参照するようになっています。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE（あるいは INSERT … ON CONFLICT）で再実行しても安全。
- フェイルセーフ:
  - OpenAI 呼び出しや API 失敗時は例外で全体を停止させず、部分的にフォールバックして進行する設計（例: macro_sentiment=0.0）。
- 自動環境変数読み込み:
  - パッケージインポート時にプロジェクトルートで .env / .env.local を自動ロードします（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- セキュリティ対策:
  - News collector は SSRF 対策（プライベートアドレス拒否・リダイレクトチェック）と XML の安全パーシングを行っています（defusedxml を使用）。
- API レート / リトライ:
  - J-Quants クライアントはレート制御（120 req/min）とリトライ（指数バックオフ、401 のトークンリフレッシュ対応）を実装しています。
  - OpenAI 呼び出しもリトライや 5xx 対処を行います。

ディレクトリ構成（主要ファイル）
------------------------------
以下は主要モジュールとファイルの一覧（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         — ニュース NLP（score_news, calc_news_window 等）
    - regime_detector.py  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch_*/save_*）
    - pipeline.py         — ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - etl.py              — ETLResult を再エクスポート
    - news_collector.py   — RSS 取得・前処理・保存
    - calendar_management.py — 市場カレンダー・営業日判定
    - stats.py            — zscore_normalize 等
    - quality.py          — データ品質チェック
    - audit.py            — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py  — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - ai/ (上記)
  - research/ (上記)

ライセンス・貢献
----------------
- 本 README はコードベースの説明を目的としており、実際の利用時はプロジェクトの LICENSE を確認してください。
- バグ報告・機能提案は Issue を立ててください。

補足（よくある質問）
-------------------
- Q: OpenAI の API キーはどの環境変数ですか？
  - A: OPENAI_API_KEY。関数呼び出し時に api_key 引数で上書き可能です。

- Q: 自動で .env を読み込まないようにしたい
  - A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Q: DuckDB のデフォルトパスは？
  - A: DUCKDB_PATH 環境変数で指定できます。デフォルトは data/kabusys.duckdb。

---

必要があれば、README にサンプル .env.example、requirements.txt、または具体的な CLI スクリプト（ETL 実行用、ニューススコア実行用）を追加する案も作成します。どの項目を優先して補足しますか？