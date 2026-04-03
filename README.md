KabuSys
=======

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。
DuckDB をデータ層に使い、J-Quants / OpenAI / kabuステーション 等と連携して
ETL、ニュースNLP（LLM を用いたセンチメント）、市場レジーム判定、
研究用ファクター計算、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）
などの機能を提供します。

プロジェクト概要
----------------
- 目的: 日本株の自動売買システム構築に必要なデータ取得・前処理・スコアリング・監査基盤を提供する。
- データソース:
  - J-Quants API（株価日足、財務、上場銘柄情報、JPX カレンダー）
  - RSS（ニュース収集）
  - OpenAI（gpt-4o-mini を利用したニュースセンチメント / マクロセンチメント）
  - kabuステーション（発注等、設定は一部準備あり）
- データストア: DuckDB（ローカルファイル / in-memory）
- 設計思想:
  - ルックアヘッドバイアスを避ける（内部で date.today() を直接参照しない箇所が多い）
  - 冪等性（DB 保存は ON CONFLICT / idempotent）を重視
  - API 呼び出しは再試行・レート制御を組み込み（J-Quants 等）
  - 品質チェック（欠損・スパイク・重複・日付不整合）を実装

主な機能一覧
-------------
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl: 市場カレンダー・株価日足・財務データの差分取得・保存・品質チェック
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch / save のラッパー（ページネーション・再試行・レート制御）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、raw_news への冪等保存（SSRF 対策・サイズ制限あり）
- ニュース NLP（kabusys.ai.news_nlp）
  - gpt-4o-mini を用いた銘柄ごとのニュースセンチメント生成（ai_scores へ保存）
  - タイムウィンドウは前日 15:00 JST ～ 当日 08:30 JST
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の 200 日 MA 乖離 (70%) とマクロニュース LLM 評価 (30%) を合成して
    'bull' / 'neutral' / 'bear' を算出し market_regime テーブルへ保存
- 研究用モジュール（kabusys.research）
  - ファクター計算: momentum / volatility / value
  - 特徴量探索: forward returns, IC（Spearman）、統計サマリ、rank
  - 共通統計ユーティリティ（zscore_normalize）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合チェック
  - QualityIssue を返す設計で、ETL はチェック結果を受けて呼び出し側で対応
- 監査ログ / トレーサビリティ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化関数
  - init_audit_db / init_audit_schema による冪等初期化

セットアップ手順
----------------
前提
- Python 3.10 以上（typing の | 合成を使用しているため）
- インターネット接続（J-Quants / OpenAI などを利用する場合）
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
  - （その他 urllib, typing 等は標準ライブラリ）

例: 開発環境の最低手順
1. リポジトリをクローン
   - git clone <repo>
   - cd <repo>

2. 仮想環境作成と有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール
   - pip install -U pip
   - pip install -e .    # setup.py / pyproject.toml がある場合
   - もしくは必要パッケージを個別に: pip install duckdb openai defusedxml

4. 環境変数 / .env の準備
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local を上書きとして読み込み）。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 等で使用）
     - KABU_API_PASSWORD: kabu API 用パスワード（必要に応じて）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH 等の監視設定
     - KABUSYS_ENV（development | paper_trading | live）
     - LOG_LEVEL（DEBUG|INFO|...）
   - .env 記法の特徴:
     - export KEY=val 形式に対応
     - シングル/ダブルクォートをサポート（エスケープ処理あり）
     - コメントは #（直前にスペースまたはタブがある場合はコメントと見做す）

使い方（主要な呼び出し例）
-------------------------

1) DuckDB 接続を開く
- デフォルトパスを使う例:
    from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- メモリ内 DB:
    conn = duckdb.connect(":memory:")

2) 日次 ETL を実行する
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

3) ニュースセンチメント（AI）スコアを作る
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    # OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"書き込み銘柄数: {n_written}")

4) 市場レジーム判定
    from kabusys.ai.regime_detector import score_regime
    cnt = score_regime(conn, target_date=date(2026, 3, 20))
    # market_regime テーブルへ結果が保存される

5) 監査ログ DB を初期化する（発注監査用）
    from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")
    # init_audit_schema は既存接続へ追加可能:
    # from kabusys.data.audit import init_audit_schema
    # init_audit_schema(conn, transactional=True)

6) 研究用モジュールの利用例
    from kabusys.research import calc_momentum, calc_volatility
    momentum = calc_momentum(conn, target_date=date(2026,3,20))
    volatility = calc_volatility(conn, target_date=date(2026,3,20))

注意点 / 運用上の留意事項
-----------------------
- OpenAI / J-Quants といった外部 API のキーは必ず安全に管理してください。
- 自動 .env 読み込みはプロジェクトルート（.git か pyproject.toml を探索）を基準に行います。
- J-Quants API はレート制限 (120 req/min) を前提に実装されています。大量リクエスト時は注意してください。
- ニュースの RSS 収集では SSRF や XML 攻撃対策（defusedxml、リダイレクト先検査、サイズ制限）を実装していますが、
  運用環境ではさらに監視・制限を行ってください。
- DuckDB の executemany はバージョンによって挙動が異なる場合があるため、空パラメータの送信を避ける等の保護ロジックがあります。
- 本コードベースの設計方針として、バックテストや研究でルックアヘッドバイアスを防止するため
  date の取り扱いに細心の注意を払っています。内部関数は多くの場合 target_date を明示的に受け取ります。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py                # package 初期化（version 等）
- config.py                  # 環境変数・設定管理（.env 自動読み込み・Settings）
- ai/
  - __init__.py
  - news_nlp.py              # ニュースセンチメント（OpenAI 呼び出し・バッチ処理）
  - regime_detector.py       # マクロ + MA200 を合成した市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py        # J-Quants API client + DuckDB 保存関数
  - pipeline.py              # ETL パイプライン（run_daily_etl 等）
  - etl.py                   # ETLResult の再エクスポート
  - news_collector.py        # RSS 収集（SSRF 対策・正規化・保存）
  - calendar_management.py   # 市場カレンダー管理・営業日判定
  - quality.py               # データ品質チェック群
  - stats.py                 # zscore_normalize など統計ユーティリティ
  - audit.py                 # 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py       # momentum/value/volatility 等
  - feature_exploration.py   # forward returns, ic, rank, summary
- monitoring/                  # （実行監視・PID・killflag関連コードが想定される場所）
- execution/                   # （発注実行周りの実装が想定される場所）
- strategy/                    # （戦略生成ロジックが想定される場所）

ライセンス・貢献
----------------
- ライセンスや貢献ガイドはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

最後に
------
この README はコードベースの主要な機能と使い方をまとめた簡易ガイドです。各モジュール内に詳細な docstring / 注釈が多く含まれているため、実装や挙動の詳細は該当ファイルを参照してください。必要であれば、利用シナリオ（ETL のスケジュール化、発注フロー統合、テスト方法等）に応じた具体的な利用手順も作成します。