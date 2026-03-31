KabuSys — 日本株自動売買 / データプラットフォーム
====================================

概要
----
KabuSys は日本株向けのデータパイプライン、リサーチ、AI/ニュース解析、監査ログ、および市場レジーム判定を含む自動売買／データプラットフォームのライブラリ群です。DuckDB を内部データベースとして使用し、J-Quants API や RSS、OpenAI（LLM）など外部サービスと連携してデータ取得・品質管理・特徴量計算・シグナル生成に必要な基盤処理を提供します。

主な機能
-------
- データ収集（ETL）
  - J-Quants から株価（OHLCV）、財務、上場情報、マーケットカレンダーを差分取得・保存
  - RSS からニュース記事を収集して raw_news に保存（SSRF 対策・トラッキング除去）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などの検出・報告
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを集約し LLM（gpt-4o-mini）でセンチメントを算出して ai_scores に保存
  - マクロ記事から市場センチメントを評価し市場レジーム（bull/neutral/bear）判定
- リサーチ / ファクター処理
  - モメンタム、ボラティリティ、バリューなどの定量ファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 監査（Audit）
  - signal → order_request → execution までのトレーサビリティ用テーブル定義と初期化ユーティリティ
- コンフィグ管理
  - .env / .env.local / 環境変数の自動読み込み（プロジェクトルート検出・優先順位あり）

セットアップ
-----------

1. Python バージョン
   - Python 3.10+ を推奨（型注釈に union 型等を使用）。

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージインストール（最低限）
   - pip install duckdb openai defusedxml

   （実際のプロジェクトでは requirements.txt / pyproject.toml を用意して管理することを推奨します）

4. パッケージを開発モードでインストール（オプション）
   - pip install -e .

5. 環境変数 / .env の設定
   - 必須（アプリで参照される主要な環境変数）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（news / regime モジュールで使用）
   - 任意 / デフォルト値あり:
     - KABUSYS_ENV — development | paper_trading | live（デフォルト development）
     - LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

   自動 .env ロード:
   - パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を探索し、
     OS 環境変数 > .env.local > .env の順で読み込みます。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（簡単な例）
-----------------

※ 以下は主要ユーティリティの呼び出し例です。実運用ではロギング設定・例外処理・ジョブスケジューラ等を組み合わせてください。

1) DuckDB 接続を作って日次 ETL を実行する
- 目的: 市場カレンダー・株価・財務データを差分取得して保存し、品質チェックを実行する。

Python 例:
- import duckdb
- from datetime import date
- from kabusys.data.pipeline import run_daily_etl
- conn = duckdb.connect(str(Path("data/kabusys.duckdb")))
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

2) ニュースを LLM でスコアリングして ai_scores に保存
- from kabusys.ai.news_nlp import score_news
- conn = duckdb.connect(str(Path("data/kabusys.duckdb")))
- n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
- print("scored", n_written, "codes")

3) 市場レジームを判定して market_regime テーブルに保存
- from kabusys.ai.regime_detector import score_regime
- conn = duckdb.connect(str(Path("data/kabusys.duckdb")))
- score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")

4) 監査用 DB 初期化
- from kabusys.data.audit import init_audit_db
- conn = init_audit_db("data/audit.duckdb")
- # これにより監査テーブル（signal_events, order_requests, executions）とインデックスが作成される

主要 API（モジュール）
--------------------
- kabusys.config.settings
  - 環境変数から設定値を取得するためのオブジェクト（例: settings.jquants_refresh_token）
- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult 型
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（自動リフレッシュ対応）
- kabusys.data.news_collector
  - fetch_rss / RSS 前処理・保存に関するユーティリティ
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.audit
  - init_audit_schema / init_audit_db
- kabusys.ai.news_nlp
  - score_news（銘柄ごとのニュースセンチメント算出）
- kabusys.ai.regime_detector
  - score_regime（ETF とマクロニュースを組み合わせて市場レジーム判定）
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.stats
  - zscore_normalize（ファクターのクロスセクション正規化）

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / .env 読み込みロジック
- ai/
  - __init__.py
  - news_nlp.py            — ニュース集約と LLM スコアリング（ai_scores へ書込）
  - regime_detector.py     — 市場レジーム判定（ma200 とマクロセンチメントの合成）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得/保存/認証/レート制限）
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - news_collector.py      — RSS 収集、前処理、SSRF 対策
  - calendar_management.py — 市場カレンダー関連ユーティリティ（is_trading_day など）
  - quality.py             — データ品質チェック
  - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py               — 監査ログスキーマ初期化
  - etl.py                 — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py     — モメンタム/ボラティリティ/バリュー等の計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

注意点 / 実運用上のヒント
-----------------------
- Look-ahead バイアス対策:
  - 多くの関数は内部で datetime.today() を直接参照せず、必ず target_date を引数で受けます。バックテスト時は対象日を明示してください。
- OpenAI / ネットワーク呼び出し:
  - API エラー時のフェイルセーフを組み込んでおり、LLM 呼び出し失敗時はスコア 0 にフォールバックする等の仕様がありますが、実運用ではエラーハンドリングや監視を追加してください。
- .env 自動読み込み:
  - プロジェクトルート検出により自動的に .env / .env.local を読み込みます。CI 等でこれを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使ってください。
- DuckDB バージョン特性:
  - 一部の executemany 空リスト処理やリストバインドは DuckDB バージョンにより挙動が異なるため、コード内で空チェックが行われています。運用環境の DuckDB バージョンに注意してください。

ライセンス / 貢献
-----------------
- このリポジトリにはライセンスファイルが同梱されていない場合があるため、利用・配布前にプロジェクト所有者の許諾を確認してください。
- バグ修正や機能追加は Issue/PR ベースの運用を想定しています。テスト（ユニット/統合）を追加してからの PR を推奨します。

問い合わせ / 追加情報
---------------------
- 具体的な実行手順や本番デプロイ（kabuステーション連携、注文実行ロジック等）はこの README の範囲外です。運用前に監査ログ・冪等性・リスク管理・レート制御を十分に検討してください。

--- 
この README はコードベースのソースコメントを基に作成しています。必要であれば、各モジュールの詳細な利用例や設定 .env.example を追加で作成します。