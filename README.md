KabuSys — 日本株自動売買システム
================================

本ドキュメントは、このリポジトリ（src/kabusys）に含まれる主要スクリプトやモジュールの概要、セットアップ手順、基本的な使い方、ディレクトリ構成を説明します。実装は軽量で自己完結したコンポーネント群（監視、実行、ポートフォリオ構築、リサーチ、AI 補助など）で構成されています。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買システムのコアライブラリです。主な提供機能は次のとおりです。

- ExecutionEngine（発注エンジン）起動スクリプト（run_execution.py）
  - 本番 / ペーパートレード（分離された SQLite DB）に対応
  - BrokerClientFactory による実マーケット / MockBroker の切替
  - RiskManager, OrderManager, Reconciler 等の組み立て
- Monitoring（監視）コンポーネント（run_monitoring.py と monitoring パッケージ）
  - システム状態、注文ログ、リスク指標の定期ポーリングと永続化
  - Kill Switch による外部停止（data/kill.flag）
  - アラート送出（LINE 等の設定に基づく）
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等重／スコア加重、ポジションサイズ計算、セクター上限、レジーム乗数
- リサーチ機能（research パッケージ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索、IC 計算、将来リターン計算
- AI 補助（ai パッケージ）
  - ニュース NLP による銘柄センチメント算出（OpenAI API 使用）
  - 市場レジーム判定（ma200 + マクロニュース LLM 評価）
- ユーティリティ
  - .env ウィザード（config_setup.py）、設定検証 CLI（validate_config.py）
  - ログ設定ユーティリティ、プロセス優先度設定ユーティリティ
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

主な機能一覧
-------------
- 実行エンジン起動 / 停止制御（実行用 PID / stop フラグ / kill フラグ）
- 監視ポーリングと永続化（SQLite：monitoring.db）
- DuckDB ベースのリサーチ用テーブル操作（prices_daily, raw_financials, raw_news 等）
- OpenAI を用いたニュースセンチメント評価（バッチ処理、リトライ・バリデーション実装）
- ポートフォリオ構築ロジック（候補選定、重み計算、単元株丸め、リスク制限）
- 設定管理（.env 自動読み込み、設定ウィザード、検証 CLI）
- ログ管理（コンソール + 日次ローテートファイル）

必要条件（推奨）
----------------
- Python 3.10 以上
- 推奨パッケージ（主要なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証を行う場合）
- SQLite（標準ライブラリに含まれます）
- ネットワークアクセス（OpenAI 呼び出し時）

セットアップ手順
----------------
1. リポジトリをクローン / 取得
   - 例: git clone <repo_url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 必要ライブラリをインストール
   - pip install duckdb psutil openai
   - 設定検証で PyYAML を使う場合: pip install pyyaml

   （実際の運用では requirements.txt を用意して pip install -r requirements.txt を推奨）

4. .env の作成
   - 対話式ウィザードで初期 .env を作成:
     - python -m kabusys.config_setup
   - ウィザード後、必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を設定してください。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリとログディレクトリの確認 / 作成
   - デフォルトのパス:
     - SQLite (monitoring): data/monitoring.db
     - DuckDB: data/kabusys.duckdb
     - Paper trading DB: data/paper_trading.db
     - ログ: logs/
   - 必要に応じて環境変数で上書き:
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR, etc.

基本的な使い方
-------------

.env による設定
- 主要な環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録
  - OPENAI_API_KEY: OpenAI 利用時に必須
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB。デフォルト data/paper_trading.db）
  - LOG_LEVEL（例: INFO）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）、run_monitoring で上書き可能）
  - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）

起動 / 停止
- ExecutionEngine（発注エンジン）起動:
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、専用の paper_trading DB を使用します
    - 起動前に data/kill.flag が存在する場合は起動を行いません
    - 起動中に data/stop_requested.flag を作成すると実行エンジンを停止します
    - エンジンは内部で PID ファイル（data/execution.pid）を作成します

- Monitoring 起動（定期監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト: 60）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存しない）
  - 停止: data/stop_requested.flag を作成すると監視ループは次回検出時に終了します

- Kill Switch（外部からの停止シグナル）
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine 停止を要求します
  - run_monitoring / monitoring_engine が条件（ドローダウン等）を満たした場合に書き込まれます
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると kill.flag を自動でクリアできます（本番では推奨しません）

ツール類
- Paper Trading 検証レポート：
  - python -m kabusys.tools.paper_verification_report
  - 期間指定や DB ファイル指定が可能:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db で SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

AI / レジーム判定
- kabusys.ai.score_news(conn, target_date, api_key=None) — raw_news をスコアリングして ai_scores に書き込み
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジーム判定と market_regime への書き込み
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定

ログ
- logging は共通ユーティリティ kabusys.utils.logging_setup.setup_logging() を通じて設定されます
- デフォルトで stdout と logs/<app_name>.log（日次ローテート）へ出力します
- ログレベルは環境変数 LOG_LEVEL か setup_logging の引数で指定可能

データベースマイグレーション
- monitoring_db.init_monitoring_db() は起動時に呼ばれ、テーブル作成や軽微なマイグレーション（カラム追加）を行います（冪等）

停止フラグ / PID / ファイル位置
- stop フラグ（プロセス起動監視停止用）: data/stop_requested.flag
- kill フラグ（ExecutionEngine 停止指令）: data/kill.flag
- エンジン PID ファイル: data/execution.pid
- これらのパスは Settings 経由で変更可能（環境変数 PID_FILE_PATH, KILL_FLAG_PATH）

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 下の主要モジュール・パッケージ構成（抜粋）です。

- src/kabusys/
  - __init__.py                 -- パッケージ定義
  - config.py                   -- 環境変数 / 設定読み込みロジック（.env 自動読み込み含む）
  - config_setup.py             -- 対話式 .env ウィザード CLI
  - validate_config.py          -- 設定検証 CLI
  - run_execution.py            -- ExecutionEngine 起動スクリプト
  - run_monitoring.py           -- SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py          -- ログ設定ユーティリティ
    - process_priority.py       -- プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py          -- SQLite 永続化層
    - system_monitor.py         -- システム状態 / データ鮮度チェック
    - trade_monitor.py          -- 注文ログ監視（存在）
    - risk_monitor.py           -- ドローダウン / ポジション上限チェック
    - kill_switch.py            -- kill.flag 書き込みロジック
    - monitoring_engine.py      -- 監視コンポーネント統合ループ
    - alert_manager.py          -- アラート送出ロジック（存在）
  - execution/
    - execution_engine.py       -- ExecutionEngine（存在）
    - broker_factory.py         -- Broker クライアント生成（Mock / 実装）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py      -- 候補選定・重み計算
    - position_sizing.py        -- 単元株計算・利用金額調整
    - risk_adjustment.py        -- セクター上限・レジーム乗数
  - research/
    - factor_research.py        -- モメンタム / ボラティリティ / バリュー計算（DuckDB）
    - feature_exploration.py    -- IC / 将来リターン / 統計サマリー
  - ai/
    - news_nlp.py               -- ニュース NLP スコアリング（OpenAI）
    - regime_detector.py        -- レジーム判定（ma200 + マクロ LLM）
  - tools/
    - paper_verification_report.py -- ペーパートレード検証レポート生成

補足 / 運用ノート
-----------------
- 環境変数の自動ロード:
  - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基準に .env, .env.local を自動読み込みします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト等で利用）
- Paper Trading:
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い、記録は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ行われ、production DB と完全分離されます
- OpenAI 呼び出し:
  - ネットワーク / レート制限 / JSON パースの失敗などに対してリトライやフォールバック（0.0）を用意しています。API キーが無い場合は例外を投げる関数がありますので注意してください。

よくあるコマンドまとめ
--------------------
- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

ライセンス / 貢献
-----------------
この README はコードベースの概要ドキュメントです。実際のライセンスや貢献ガイドラインはリポジトリの LICENSE / CONTRIBUTING ファイルに従ってください。

お問い合わせ
------------
実装や運用に関する質問はコード内のログやコメント、該当モジュール（特に config.py / monitoring_db.py / run_*.py）を参照してください。必要であれば README を更新して欲しい点を教えてください。