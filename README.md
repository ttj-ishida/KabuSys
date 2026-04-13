README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ／監視フレームワークです。本リポジトリには以下の主要機能群が含まれます:

- 発注実行エンジン（ExecutionEngine）と注文管理（OrderManager）
- 監視コンポーネント（System / Trade / Risk / Kill Switch）と監視 DB（SQLite）
- ポートフォリオ構築用の純粋関数群（銘柄選定・重み計算・ポジションサイズ）
- リサーチ（ファクター計算・特徴量探索）
- AI 統合（ニュース NLP によるセンチメント、レジーム判定）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針のポイント:
- DuckDB（時系列・ファクタ計算用）と SQLite（監視 / 発注ログ用）を併用
- 本番と Paper Trading を明確に分離（DB、Mock ブローカーの利用）
- 可能な限りルックアヘッドバイアスを避ける（date.today() を直接参照しない等）
- API 呼び出しは失敗しても安全に継続するフェイルセーフ設計

主な機能一覧
--------------
- Execution:
  - 発注作成・送信、リスク管理、起動時のリコンシリエーション（Reconciler）
  - BrokerClientFactory による本番 / モックの切替（KABUSYS_ENV）
- Monitoring:
  - SystemMonitor: CPU/Memory/Disk、Execution プロセス存在確認、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常検知
  - RiskMonitor: ドローダウン・ポジション上限検出とダッシュボード更新
  - KillSwitch: 条件により flag ファイルを書き ExecutionEngine を停止
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（read-only 接続）
- Portfolio:
  - 候補選定、等金額／スコア重み、セクター制限、レジーム乗数、株数計算（単元丸め・cap）
- Research:
  - Momentum / Volatility / Value ファクター計算（DuckDB SQL を利用）
  - 将来リターン・IC 計算・統計サマリー
- AI:
  - news_nlp.score_news: raw_news -> OpenAI（gpt-4o-mini）で銘柄別センチメント生成、ai_scores に保存
  - regime_detector.score_regime: ETF MA200 とマクロニュースを LLM で合成して日次レジーム判定
- Tools:
  - paper_verification_report: Paper Trading DB（data/paper_trading.db）から検証レポートを生成

セットアップ手順
----------------

1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要パッケージ例:
     pip install duckdb psutil openai requests streamlit
   - （好みに応じて requirements.txt を作成して管理してください）

3. ソースを PYTHONPATH に含めて実行（開発時）
   - export PYTHONPATH=src  （Windows: set PYTHONPATH=src）

4. 環境変数設定
   - 簡易的にはプロジェクトルートに .env または .env.local を作成
   - 自動読み込み: .env / .env.local は Settings モジュールによって自動読み込みされます（OS 環境変数が優先）
   - 自動読み込みを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（代表）
- KABUSYS_ENV: 起動環境 ("development" | "paper_trading" | "live")。デフォルト "development"
- JQUANTS_REFRESH_TOKEN: 必須（Settings.jquants_refresh_token）
- KABU_API_PASSWORD: 必須（kabuステーション API 用）
- OPENAI_API_KEY: AI 機能（news_nlp / regime_detector）に必要
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定振る舞い ("instant" | "partial" | "never" | "reject"), デフォルト "instant"
- PID_FILE_PATH / KILL_FLAG_PATH: 実行中プロセス PID 管理と停止フラグパス
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒, デフォルト 60）

使い方（実行例）
-----------------

- 監視ループを起動（モジュール実行）
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（例: MONITOR_POLL_INTERVAL=30）

- ExecutionEngine（取引実行）を起動
  - PYTHONPATH=src python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し data/paper_trading.db を操作（本番 DB と分離）

- Streamlit 監視ダッシュボード（ローカル閲覧）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB に対して read-only URI で接続します

- Paper Trading 検証レポート生成
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パス指定可能（未指定時は PAPER_TRADING_SQLITE_PATH 環境変数 or data/paper_trading.db）

- AI 機能（例）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date, api_key を受け取る関数として提供されています。
  - 実行には OPENAI_API_KEY が必要です。API 呼び出しはリトライ・バックオフとレスポンス検証を行います。

注意点・運用メモ
- Settings は .env/.env.local を自動でロードします。OS 環境変数が優先されます。
- 監視（Monitoring）は Settings.env に関わらず本番 sqlite_path（デフォルト data/monitoring.db）を使用する設計です。
- Paper Trading は実運用 DB と分離され、PAPER_TRADING_SQLITE_PATH に書き込みます。
- psutil を使ってプロセス優先度・CPU affinity を設定します。権限不足時は警告ログを出して継続します。
- OpenAI API 呼び出しは JSON mode を使用し、レスポンスの頑健性を確保するためにパース／検証を行います。API キーは環境変数か関数引数で与えてください。

ディレクトリ構成（主要ファイル）
--------------------------------
（src/kabusys 以下を想定）

- __init__.py
- config.py                                   — 環境変数 / Settings 管理（.env 自動読み込み）
- run_monitoring.py                            — SystemMonitor のポーリング起動スクリプト
- run_execution.py                             — ExecutionEngine 起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py                                — ニュース NLP（OpenAI 連携・ai_scores 書込）
  - regime_detector.py                         — 市場レジーム判定（MA200 + マクロ NLP）

- monitoring/
  - __init__.py
  - monitoring_db.py                            — SQLite スキーマ定義・読み書き API
  - system_monitor.py                           — システム / データ鮮度監視
  - trade_monitor.py                            — 注文滞留 / 約定異常検知
  - risk_monitor.py                             — ドローダウン / ポジション上限監視
  - kill_switch.py                              — kill.flag 管理
  - monitoring_engine.py                        — 各モニタを束ねるエンジン
  - alert_manager.py                            — LINE 通知
  - streamlit_dashboard.py                      — streamlit ダッシュボード

- portfolio/
  - portfolio_builder.py                        — 候補選定・重み計算
  - risk_adjustment.py                           — セクター上限・レジーム乗数
  - position_sizing.py                           — 株数決定・aggregate cap

- research/
  - __init__.py
  - factor_research.py                           — Momentum/Volatility/Value 計算
  - feature_exploration.py                       — 将来リターン / IC / 統計

- execution/
  - order_manager.py
  - reconciler.py
  - （その他：broker_factory, execution_engine, order_repository 等は発注ロジック関連）

- monitoring/tools/
  - paper_verification_report.py                 — Paper Trading 検証レポート CLI

- utils/
  - process_priority.py                          — プロセス優先度 / CPU affinity ユーティリティ

サンプル .env（最小）
--------------------
例（プロジェクトルートに .env を置く）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=your_line_token
LINE_USER_ID=your_line_user_id

テスト・開発のヒント
- PYTHONPATH=src を忘れずに設定するとローカルソースをパッケージとして実行できます。
- AI 関連のユニットテストでは OpenAI 呼び出し箇所（_call_openai_api 等）をモック化してください。
- DuckDB / SQLite のスキーマは init_monitoring_db で冪等に初期化されます。既存 DB の簡単なマイグレーション処理も含まれています。

ライセンス・貢献
----------------
- 本 README ではライセンスや貢献ルールは明示していません。実プロジェクトでは LICENSE ファイルや CONTRIBUTING を追加してください。

以上が本コードベースの概要と基本的な使い方です。必要であればインストール用 requirements.txt や .env.example を用意する README の拡張を作成します。どの情報を追加したいか教えてください。