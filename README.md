# KabuSys

日本株自動売買システム（ライブラリ / 起動スクリプト群）

注意: この README は src/kabusys 以下のコードベースに基づく概要・使い方を日本語でまとめたものです。

## プロジェクト概要
KabuSys は日本株向けの自動売買／リサーチ基盤です。  
主な機能は以下のとおりです。

- 発注・執行エンジン（ExecutionEngine）と発注管理（OrderManager, RiskManager 等）
- 監視コンポーネント（SystemMonitor, TradeMonitor, RiskMonitor）と監視ループ起動スクリプト
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- ファクター計算・特徴量探索（research パッケージ）
- AI を用いたニュースセンチメント集計・レジーム判定（OpenAI API）
- Paper Trading 用の分離された DB と検証レポート生成スクリプト
- 環境設定ウィザード、設定検証 CLI、統一的ロギング設定ユーティリティ

## 機能一覧（主なモジュール）
- kabusys.run_execution: ExecutionEngine 起動スクリプト（本番 / ペーパートレード判定あり）
- kabusys.run_monitoring: SystemMonitor ポーリングループ起動スクリプト
- kabusys.config_setup: .env 対話式ウィザード（.env の生成/更新）
- kabusys.validate_config: .env および config/*.yaml の事前検証 CLI
- kabusys.tools.paper_verification_report: Paper Trading の検証レポート生成
- kabusys.monitoring: 監視用 DB 層および各種モニタ（system, trade, risk）、Kill Switch、アラート連携
- kabusys.portfolio: 候補選定、重み付け、リスク調整、ポジションサイズ計算
- kabusys.research: ファクター計算（momentum/value/volatility）・IC/統計ユーティリティ
- kabusys.ai: OpenAI を用いたニュース NLP（score_news）とレジーム判定（score_regime）
- kabusys.utils: ロギング設定、プロセス優先度/CPU affinity 設定等
- kabusys.monitoring.monitoring_db: 監視ログ用 SQLite スキーマと読み書きユーティリティ

## 必要条件（推奨）
- Python 3.9+
- 主要依存パッケージ（コード中で import されているもの）
  - duckdb
  - psutil
  - openai（AI 機能を利用する場合）
  - PyYAML（config/*.yaml の中身検証を行う場合に必要）
- SQLite（Python 標準ライブラリの sqlite3 を使用）
- ネットワークアクセス（kabuステーション API / OpenAI API 等を利用する場合）

簡易的な requirements.txt（例）
- duckdb
- psutil
- openai
- PyYAML

## セットアップ手順（概要）
1. リポジトリルートに移動（.git または pyproject.toml が存在するディレクトリがプロジェクトルートとして自動検出されます）。
2. 仮想環境を作成して有効化（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール（プロジェクトに requirements.txt がある場合はそれを使用）。
   - pip install duckdb psutil openai PyYAML
4. 環境変数設定
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
     - これによりプロジェクトルートに .env が生成／更新されます。
   - もしくは .env を直接作成して環境変数を設定
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 任意: KABUSYS_ENV（development / paper_trading / live）、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、OPENAI_API_KEY など
5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる（exit 1）

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: execution の動作モード（development / paper_trading / live）
  - paper_trading の場合、MockBrokerClient が使用され、data/paper_trading.db に記録される（本番 DB と分離）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（ログ出力先、デフォルト: logs/）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）; デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番で誤設定が危険。説明は validate_config を参照）

自動 .env ロード:
- プロジェクトルートに .env / .env.local がある場合、自動で読み込まれます（OS 環境変数を優先）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（主にテスト用）。

## 使い方（起動・CLI）
基本的にパッケージモードで Python を実行します（python -m ...）。

1. 環境設定ウィザード
   - python -m kabusys.config_setup
   - .env の作成 / 更新を対話的に行います。

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告があると exit 1 になります。

3. ExecutionEngine 起動（発注エンジン）
   - python -m kabusys.run_execution
   - 本番 / ペーパートレードは KABUSYS_ENV で制御（paper_trading の場合、専用 DB に記録）

4. Monitoring 起動（SystemMonitor ポーリング）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
   - 監視は設定にかかわらず本番 sqlite_path を使用して監視テーブルを初期化します。

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

6. AI / レジーム・ニュース処理（ライブラリ API）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - これらは DuckDB 接続と OpenAI API キーを受け取りテーブルに書き込みます。

7. ログ
   - setup_logging(app_name="execution" 等) を呼ぶことで logs/<app_name>.log に日次ローテートで出力されます。
   - LOG_DIR / LOG_LEVEL 環境変数で挙動を制御可能。

## Kill Switch / 停止フラグ
- 監視側（KillSwitch）は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。
- run_execution/run_monitoring は data/stop_requested.flag 等の存在をチェックして安全にループを終了します。
- KILL_FLAG_CLEAR_ON_START を利用して起動時に kill.flag を自動削除する設定もありますが、本番では 0 を推奨します（安全策）。

## ディレクトリ構成（抜粋）
プロジェクトの主要ファイル／フォルダ（src/kabusys 以下を中心に記載）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py           — .env 対話式ウィザード CLI
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py        — ルートロガー設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ / MonitoringDB
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — （trade 監視ロジック）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （アラート送信ロジック）
  - execution/
    - execution_engine.py     — ExecutionEngine（エンジン制御）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 呼び出し + ai_scores 書込）
    - regime_detector.py      — レジーム判定（MA + マクロセンチメント合成）
  - tools/
    - paper_verification_report.py
  - data/                     — 実行時に使用するファイル（DB, pid, flag など。実行環境で作成）
  - logs/                     — ログ保存先（デフォルト）

（注）一部ファイルは上記抜粋に含めていないサブモジュールがあります。コードベース全体は src/kabusys 配下を参照してください。

## 注意事項 / 運用上のポイント
- Paper Trading は本番 DB と完全分離される設計（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 機能（news_nlp, regime_detector）は OpenAI API を利用します。API キー管理およびコストに注意してください。API エラーはフェイルセーフ（0 戻し等）で扱われる設計です。
- 監視（Monitoring）と Execution はプロセス優先度を "high" に設定して起動します。OS 権限により設定できない場合は警告を出して続行します。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- .env は絶対に Git にコミットしないでください（config_setup.py にも注意書きあり）。

---

この README はコードベースの主要機能・起動手順をまとめた概略です。詳細な設定や実際の運用手順は config/*.yaml（存在する場合）や各モジュールの docstring / ソースコードを参照してください。質問や起動で不明点があれば該当するファイル名を指定して質問いただければ、より具体的にお答えします。