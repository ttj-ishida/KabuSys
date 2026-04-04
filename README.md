KabuSys — 日本株自動売買／データプラットフォーム
================================

概要
----
KabuSys は日本株向けのデータパイプライン、特徴量計算、ニュース NLP（LLM）スコアリング、マーケットレジーム判定、監査ログ（トレーサビリティ）などを備えた自動売買プラットフォームのコードベースです。  
主に以下の用途を想定しています。

- J-Quants API からのデータ ETL（株価日足・財務・マーケットカレンダー）
- RSS ニュース収集と OpenAI を使った銘柄センチメント算出（ai_scores）
- 市場レジーム判定（ETF とマクロニュースの合成）
- ファクター計算・研究用ユーティリティ（モメンタム、ボラティリティ、バリューなど）
- DuckDB を使ったローカル DB 保存と監査ログスキーマ初期化

主要機能
--------
- data
  - ETL パイプライン（差分取得・保存・品質チェック）
  - J-Quants API クライアント（認証、ページネーション、レート制御、リトライ）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - RSS ニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ（signal / order_request / execution のテーブル群）と初期化ユーティリティ
  - 統計ユーティリティ（Zスコア正規化など）
- ai
  - news_nlp.score_news: OpenAI（gpt-4o-mini）による銘柄ごとのニュースセンチメント算出
  - regime_detector.score_regime: ETF（1321）200日 MA 乖離とマクロニュースで市場レジーム判定
  - LLM 呼び出しはリトライ・フェイルセーフ設計（API 失敗時は中立化）
- research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- config
  - .env（または環境変数）読み込み、設定管理（自動読み込みはプロジェクトルートを探索）
  - 環境切替（development / paper_trading / live）とログレベル検証

セットアップ手順
----------------

1. 前提
   - Python 3.10 以上（typing にて X|Y 構文を使用しています）
   - DuckDB, OpenAI クライアント, defusedxml 等を使用します

2. インストール（例）
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - 必要パッケージをインストール（最低限）
     - pip install duckdb openai defusedxml
   - （開発インストールを想定する場合）
     - pip install -e .

   ※ 実際の requirements.txt / setup.cfg はこのリポジトリに応じて用意してください。

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を作成します。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=...                (kabuステーション利用時)
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - KILL_FLAG_CLEAR_ON_START=0
     - CPU_THRESHOLD_PCT=90.0
     - MEMORY_THRESHOLD_PCT=85.0
     - DISK_THRESHOLD_PCT=90.0
     - KABUSYS_ENV=development       (development / paper_trading / live)
     - LOG_LEVEL=INFO                (DEBUG/INFO/WARNING/ERROR/CRITICAL)
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリ
   - デフォルトで DUCKDB_PATH が data/kabusys.duckdb などを指すため、必要に応じてディレクトリを作成してください（多くの初期化関数は親ディレクトリを自動作成しますが、安全のため mkdir -p data）。

使い方（基本例）
----------------

以下は Python REPL / スクリプトでの利用例です。実行前に .env（または環境変数）を正しく設定してください。

- DuckDB 接続を作成して日次 ETL を実行する
  - from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(<your_duckdb_path>))  # 例: "data/kabusys.duckdb"
    res = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(res.to_dict())

- ニュース NLP（銘柄別スコア）を計算して保存する
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026,3,20))
    print("書き込み銘柄数:", n_written)

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの組合せ）
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    result = score_regime(conn, target_date=date(2026,3,20))
    print("result:", result)

- 研究用ファクター計算
  - from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    conn = duckdb.connect("data/kabusys.duckdb")
    mom = calc_momentum(conn, date(2026,3,20))
    vol = calc_volatility(conn, date(2026,3,20))
    val = calc_value(conn, date(2026,3,20))

- 監査ログ DB の初期化
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/kabusys_audit.duckdb")
    # 監査用テーブル群（signal_events, order_requests, executions）が作成されます

重要な挙動と設計上の注意
-----------------------
- Look-ahead バイアス防止の配慮が各モジュールに組み込まれています（target_date を明示的に渡す設計、データ取得ウィンドウの排他条件等）。
- OpenAI 呼び出しは gpt-4o-mini を想定した JSON Mode を利用しています。API キーは OPENAI_API_KEY で供給します。API の失敗時はフェイルセーフ的に中立値（0.0）にフォールバックする設計です。
- J-Quants API の呼び出しはリトライ・レートリミット制御を行います。JQUANTS_REFRESH_TOKEN を設定して get_id_token を利用します。
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml）から .env, .env.local を読み込みます（OS 環境変数 > .env.local > .env の優先順）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 実運用（実際に発注を行う部分）は execution / monitoring パッケージなどで提供される想定ですが、この README ではデータ処理・解析・NLP 部分に焦点を当てています。実口座での運用時は十分な検証・リスク管理を行ってください。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                     - 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py                 - ニュースセンチメント算出（score_news）
  - regime_detector.py          - 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py           - J-Quants API クライアント（fetch / save）
  - pipeline.py                 - ETL パイプライン（run_daily_etl 等）
  - etl.py                      - ETLResult 再エクスポート
  - news_collector.py           - RSS 収集・前処理
  - calendar_management.py      - マーケットカレンダー管理
  - quality.py                  - データ品質チェック
  - stats.py                    - 統計ユーティリティ（zscore_normalize）
  - audit.py                    - 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py          - モメンタム/ボラ/バリュー計算
  - feature_exploration.py      - 将来リターン/IC/統計サマリー
- ai, research, data の各モジュールにはさらに内部ユーティリティや SQL が含まれます。

ライセンス・貢献
----------------
この README にはライセンス情報は含まれていません。リポジトリ内の LICENSE ファイル等を参照してください。バグ報告・改善提案は issue / pull request を通じて行ってください。

最後に
------
この README はコードベースから読み取れる設計意図と使い方の概要を示しています。実際に運用する際は、環境変数の管理、API キーの保護、OpenAI や J-Quants の利用規約・レート制限に注意してください。必要であれば、具体的なユースケース（ETL スケジュール、監視設定、発注フロー）のドキュメント化も支援できます。