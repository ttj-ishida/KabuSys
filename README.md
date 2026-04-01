KabuSys
======

日本株向けのデータプラットフォームと自動売買支援ライブラリ。  
J-Quants / DuckDB を中心としたデータ ETL、ニュース収集・NLP（OpenAI）によるセンチメント評価、マーケットレジーム判定、ファクター計算、品質チェック、監査ログ（発注 → 約定のトレーサビリティ）などを提供します。

主な目的
- 日本株のデータ取得・保存・品質管理（J-Quants API 経由）
- ニュース収集と LLM による銘柄別／マクロセンチメント評価
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- リサーチ用ファクター計算・特徴量評価ユーティリティ
- 監査ログ（signal → order_request → execution）のスキーマと初期化機能

機能一覧
- データ収集 / 保存
  - J-Quants API クライアント（daily quotes / financials / market calendar / listed info）
  - 差分 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - レート制御（120 req/min）・リトライ・トークン自動リフレッシュ
- ニュース関連
  - RSS 収集器（SSRF 対策・トラッキングパラメータ除去・前処理）
  - ニュース NLP：銘柄別センチメントスコア算出（score_news）
  - マクロセンチメント＋ETF MA200 を用いた市場レジーム判定（score_regime）
- リサーチ / ファクター
  - momentum / volatility / value ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算（calc_forward_returns）
  - IC（Spearman）計算、ランク化、統計サマリ（calc_ic, rank, factor_summary）
  - Zスコア正規化ユーティリティ (zscore_normalize)
- データ品質
  - 欠損・スパイク・重複・日付整合性チェック（quality.run_all_checks）
- カレンダー管理
  - JPX カレンダー取得・営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - 夜間更新ジョブ（calendar_update_job）
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義・インデックス
  - スキーマ初期化（init_audit_schema / init_audit_db）
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出、.env, .env.local の順でロード）
  - settings オブジェクトで必要な環境変数を取得（settings.jquants_refresh_token など）
  - 自動ロード無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）

セットアップ手順（開発環境）
1. リポジトリをクローン
   - git clone <repo>

2. Python 環境（推奨: venv / pyenv）を用意
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   （実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください）

4. 環境変数を用意
   - プロジェクトルートに .env を作成するか、OS 環境変数を設定します。
   - 必須例（.env.example を参考に作成してください）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...  （score_news / score_regime で使用）
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO
   - 自動 .env ロードを無効にするには:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリを作成（必要なら）
   - mkdir -p data

基本的な使い方（コード例）
- DuckDB 接続の作成（ファイル DB）
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))  # settings.duckdb_path は Path

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメント（特定日）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")  # api_key を省略すると環境変数 OPENAI_API_KEY を使用

- マーケットレジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査 DB 初期化（監査専用の DuckDB を使う場合）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit_duckdb.duckdb")

- ファクター計算（リサーチ）
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - records = calc_momentum(conn, target_date=date(2026,3,20))

注意点・設計上の要点
- Look-ahead bias 回避
  - 多くのモジュール（news_nlp, regime_detector, pipeline 等）は内部で date.today() を不必要に参照しない設計で、target_date に依存して過去データのみを参照します。
- OpenAI / J-Quants の呼び出しにはリトライ・バックオフ・タイムアウト・レート制御が組み込まれています。API キーは適切に管理してください。
- news_collector では SSRF 対策、レスポンスサイズ制限、XML パースの安全化（defusedxml）などを実装しています。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を基準に行われます。テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- DuckDB バージョンや executemany の挙動に依存する箇所があるため、実運用時は推奨バージョンでの動作確認を行ってください。

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite パス
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                   -- 環境変数 / .env 管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py               -- ニュースの LLM スコアリング（score_news）
    - regime_detector.py       -- ETF MA200 + マクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント（fetch / save）
    - pipeline.py              -- ETL パイプライン（run_daily_etl 等）
    - etl.py                   -- ETLResult の公開（再エクスポート）
    - news_collector.py        -- RSS 収集器
    - calendar_management.py   -- market_calendar 管理・営業日判定
    - quality.py               -- データ品質チェック（check_missing_data, check_spike, ...）
    - stats.py                 -- 共通統計ユーティリティ（zscore_normalize）
    - audit.py                 -- 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py       -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py   -- calc_forward_returns / calc_ic / factor_summary / rank
  - monitoring/                 -- （監視・実行モジュール用のプレースホルダ）
  - strategy/                   -- （戦略層用のプレースホルダ）
  - execution/                  -- （約定層用のプレースホルダ）

開発・貢献
- コードの挙動や API レスポンスに依存する部分が多いため、ユニットテストでは外部呼び出し（OpenAI / J-Quants / ネットワーク）をモックすることを推奨します。
- .env.example を作成し、機密情報は共有しないでください。

ライセンス / 著作権
- （リポジトリ側で指定されたライセンスをここに記載してください）

最後に
- README に書かれている利用例はライブラリの公開 API を示す最小限のサンプルです。実運用ではログ設定・例外処理・監視・リソース管理（DB 接続の適切な開放等）を十分に行ってください。

必要であれば、インストールコマンド、.env.example のテンプレート、さらに具体的な実行スクリプト（systemd / cron 用）や運用手順書を追記します。どの情報を優先して追加しますか？