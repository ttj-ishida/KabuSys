KabuSys — 日本株自動売買 / データパイプライン用ライブラリ
================================================================================

プロジェクト概要
--------------------------------------------------------------------------------
KabuSys は日本株向けの自動売買・データプラットフォームを想定した Python ライブラリ群です。
主に次を目的としています。

- J-Quants からのマーケットデータ取得（株価・財務・市場カレンダー）
- ETL（差分取得・保存・品質チェック）パイプライン
- ニュース収集・NLP による銘柄センチメント評価（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 各種ユーティリティ（カレンダー管理、統計、品質チェックなど）

このリポジトリは主にデータ基盤・リサーチ・戦略の各レイヤーを分離して提供します。

機能一覧
--------------------------------------------------------------------------------
主な機能（モジュール単位）

- kabusys.config
  - .env / 環境変数読み込み、自動ロード（プロジェクトルート検出）
  - アプリ設定 accessor（J-Quants トークン、Kabu API、Slack、DB パス、環境種別等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（認証、ページング、保存関数）
  - pipeline: 日次 ETL（run_daily_etl、run_prices_etl など）
  - news_collector: RSS 取得・前処理・raw_news 保存ロジック（SSRF対策等）
  - calendar_management: JPX カレンダー管理／営業日判定ユーティリティ
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - audit: 監査ログスキーマ初期化・監査用 DB ユーティリティ
  - stats: Zスコア正規化等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM でスコアリングして ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースを合成して market_regime に書き込み
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

設計上の特徴（抜粋）
- ルックアヘッドバイアスを避ける設計（datetime.today() を直接参照しない等）
- DuckDB を主に使用する想定（ETL・保存・クエリは DuckDB 接続で実行）
- OpenAI（gpt-4o-mini）を JSON mode で利用、リトライ・フォールバック実装
- J-Quants API はレート制御・リトライ・トークン自動リフレッシュ対応
- ニュース収集は SSRF・XML Bomb・レスポンスサイズ制限など安全性に配慮

セットアップ手順
--------------------------------------------------------------------------------
前提
- Python 3.10 以上（型ヒントの構文や | Union を用いているため）
- DuckDB を利用可能（pip install duckdb）
- OpenAI API を利用する場合は openai パッケージ
- XML の安全パースに defusedxml

推奨インストール（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

※ プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください。

環境変数
以下は必須／任意の主な環境変数です（kabusys.config.Settings 参照）。

必須（実行する機能により変わる）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 実行時）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack チャンネル ID
- KABU_API_PASSWORD — kabu ステーション API を使う場合

任意（デフォルトあり）
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用データベース。デフォルト: data/monitoring.db)
- KABUSYS_ENV (development|paper_trading|live、デフォルト development)
- LOG_LEVEL (DEBUG|INFO|...、デフォルト INFO)
- OPENAI_API_KEY — OpenAI 呼び出し時に使用（score_news / score_regime で未指定なら環境変数参照）

.env 自動ロード
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、
  .env（優先度低）→ .env.local（優先度高）を自動読み込みします。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須変数が不足した場合は Settings のプロパティが ValueError を発生させます。
- .env.example を参考に .env を作成してください（リポジトリに含まれる場合）。

データベース初期化
- 監査ログ用 DB 初期化:
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")

使い方（簡易例）
--------------------------------------------------------------------------------
共通準備: DuckDB 接続を用意する
- import duckdb
- conn = duckdb.connect(str_path_or_colon_memory)

1) 日次 ETL 実行（J-Quants からの差分取得・保存・品質チェック）
- from kabusys.data.pipeline import run_daily_etl
- from datetime import date
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

ポイント:
- J-Quants の認証は settings.jquants_refresh_token を使用（環境変数で設定）。
- ETL は失敗箇所があっても他ステップは可能な限り継続し、ETLResult にエラー/品質問題を記録します。

2) ニュース NLP スコアリング（前日15:00〜当日08:30 JST の記事を対象）
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")  # api_key 指定可
- print(f"書き込んだ銘柄数: {count}")

注意:
- OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は省略可。
- LLM 呼び出しは失敗時にスキップするフェイルセーフあり。

3) 市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- from datetime import date
- score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

4) ファクター計算 / 研究用ユーティリティ
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- mom = calc_momentum(conn, target_date=date(2026,3,20))
- vol = calc_volatility(conn, target_date=date(2026,3,20))
- val = calc_value(conn, target_date=date(2026,3,20))

5) 監査テーブル初期化
- from kabusys.data.audit import init_audit_db, init_audit_schema
- conn_audit = init_audit_db("data/audit.duckdb")  # ファイル作成・スキーマ初期化（トランザクションあり）

運用上の注意 / ヒント
- OpenAI 呼び出しはレート・コストに注意してください（バッチやリトライ実装あり）。
- J-Quants API はレート制御（120 req/min）を厳守していますが、実行頻度に応じて調整してください。
- 本ライブラリの多くの関数は DuckDB 接続を引数に取り、データ永続化の責任は呼び出し側にあります。
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効にできます。

ディレクトリ構成（主要ファイル）
--------------------------------------------------------------------------------
以下は src/kabusys 配下の主要モジュール／ファイル構成の要約です（抜粋）。

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
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（ファクター計算・探索用）
  - (その他: strategy/, execution/, monitoring/ は __all__ に列挙される想定)

（注）上記は実装済みファイルを抜粋したもので、実際のリポジトリにはさらにテスト・ドキュメント等が存在する可能性があります。

ライセンス・貢献
--------------------------------------------------------------------------------
- この README ではライセンス表記を含めていません。リポジトリの LICENSE ファイルを参照してください。
- バグ報告・機能要望は issue をご利用ください。プルリクエスト歓迎。

最後に
--------------------------------------------------------------------------------
本 README はコードベースから読み取れる設計・使い方をまとめたものです。実際に運用・開発する際は、pyproject.toml や requirements.txt、.env.example、ドキュメント（DataPlatform.md、StrategyModel.md 等）を合わせて参照してください。質問や補足が必要であれば具体的なユースケース（ETL 実行例、DB スキーマ、OpenAI の使い方等）を教えてください。