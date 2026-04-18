KabuSys — 日本株自動売買（ライブラリ/実行スクリプト）README
================================================================================

概要
----
KabuSys は日本株の自動売買／研究／監視を行うための Python コードベースです。  
ポートフォリオ構築、ポジションサイジング、リスク制御、監視（プロセス・データ鮮度・注文ログ）、および AI（ニュースセンチメント・レジーム検出）を含むモジュール群を提供します。  
実行用スクリプト（Monitoring / Execution）や設定ウィザード・検証ツール、ペーパートレード検証レポート生成ツールも同梱しています。

主な特徴
--------
- ポートフォリオ構築（候補選定・重み付け・単元丸め）
- ポジションサイジング（risk-based / equal / score）
- セクター集中制限・レジーム乗数によるリスク調整
- DuckDB（分析用） / SQLite（監視・発注ログ）を使ったデータ基盤
- ExecutionEngine（発注実行）と Monitoring（監視） の起動スクリプト
  - KABUSYS_ENV=paper_trading 時は Mock Broker を使用し本番 DB と分離
- Kill Switch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）
- News NLP（OpenAI）を用いたセンチメント評価と market_regime 判定
- 設定ウィザード（.env 作成）と設定検証 CLI
- ペーパートレード検証レポート出力スクリプト

必要な依存関係（主なもの）
-------------------------
- Python 3.10+（型アノテーション等を利用）
- duckdb
- psutil
- openai (ニュース／レジームの LLM 呼び出し用)
- PyYAML（config/*.yaml の検証を行う場合に任意で必要）
- 標準ライブラリ（sqlite3, threading, logging 等）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （必要に応じて他のパッケージも追加）

4. .env の作成（推奨）
   - 対話式ウィザード: python -m kabusys.config_setup
     - 作成される .env には J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV 等を設定できます。
   - 手動作成の場合は .env.example を参考にしてください（プロジェクトに含める場合）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗として扱います。

重要な環境変数（抜粋）
----------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development / paper_trading / live (デフォルト: development)
  - paper_trading の場合、run_execution は MockBroker を使い data/paper_trading.db を使用します
- DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db） — Monitoring は環境に関係なく本番 sqlite_path を使用します
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL (デフォルト: INFO)
- LOG_DIR (デフォルト: logs/)
- OPENAI_API_KEY: OpenAI を利用するモジュールで必要
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（"1" で有効、デフォルト: "0"）

主要スクリプト／使い方
--------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- Monitoring（監視ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループを終了します
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を常に使用します（環境に依存しない）

- Execution（発注実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します
  - 実行中に data/stop_requested.flag を作成するとエンジンを停止します
  - PID ファイル: data/execution.pid（デフォルト、Settings.pid_file_path）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH が優先されます

- AI 関連（プログラム API）
  - kabusys.ai.score_news(duckdb_conn, target_date, api_key=None)
  - kabusys.ai.score_regime(duckdb_conn, target_date, api_key=None)

ログ
---
- logging は kabusys.utils.logging_setup.setup_logging を通じて統一設定されます
- デフォルトは logs/<app_name>.log（日次ローテート、30日保持）とコンソール出力（stdout）
- LOG_LEVEL / LOG_DIR により調整可能

停止・Kill Switch の仕組み
-------------------------
- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring.py / run_execution.py はこのファイルの存在を監視し、見つかれば手動終了処理を行います（プロセス制御用）。
- kill.flag（data/kill.flag）
  - KillSwitch が条件（ドローダウンやポジション上限など）を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 の場合は自動でクリアされますが、本番では 0 を推奨します。

DB（ファイル）について
---------------------
- DuckDB（分析用）: data/kabusys.duckdb（デフォルト）
- SQLite（監視）: data/monitoring.db（デフォルト）
  - 監視テーブル（system_status / trade_logs / positions / risk_logs / dashboard）を init_monitoring_db() で作成／マイグレーションします
- SQLite（ペーパートレード）: data/paper_trading.db（paper_trading 環境用）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールです（抜粋）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード機能含む）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ルートロギング設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite ベースの永続化層（init / MonitoringDB）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文ログ監視（滞留注文、約定異常等）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag の書き込み・管理
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信管理: LINE 等の統合）
  - execution/
    - execution_engine.py    — ExecutionEngine（発注ロジック実行）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算・スケーリング・単元丸め
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum / Value / Volatility 等の計算 (DuckDB)
    - feature_exploration.py — IC / forward returns / 統計サマリー
  - ai/
    - news_nlp.py            — ニュースを LLM へ送り銘柄別センチメントを生成し ai_scores へ書き込む
    - regime_detector.py     — ma200 と LLM を合成して market_regime を決定
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成スクリプト

補足・運用上の注意
------------------
- Monitoring は sqlite_path（デフォルト data/monitoring.db）を常に使います。環境に関わらず監視ログは本番 DB へ保存される点に注意してください（run_monitoring の仕様）。
- Execution は KABUSYS_ENV によりペーパートレードや本番の挙動を切り替えます。paper_trading では専用 DB（PAPER_TRADING_SQLITE_PATH）を使い、本番 DB と分離します。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）を必要とし、料金・レイテンシに注意してください。失敗時は多くの処理がフェイルセーフ（スコア 0.0 等）で継続しますが、運用方針を必ず検討してください。
- .env ファイルは秘密情報を含むため Git に絶対にコミットしないでください。

トラブルシューティング / よくあるコマンド
-----------------------------------------
- .env を作り直したい: python -m kabusys.config_setup
- 設定の問題を検知したい: python -m kabusys.validate_config
- 監視を手動で一度だけ実行して動作確認したい: Python REPL から MonitoringEngine を組み立て run_once() を呼ぶ（ユニットテスト向け）
- ログ出力先を変更したい: LOG_DIR 環境変数を設定

ライセンス・貢献
----------------
- 本 README はコードベースから抽出した仕様をまとめたものです。実際のライセンスはリポジトリの LICENSE ファイルを参照してください。  
- バグ報告・機能提案は Issue を通じてお願いします。

以上。必要があれば README に追加したいコマンド例や .env のサンプルテンプレートを出力します。どの情報を追記しますか？