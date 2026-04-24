KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の骨組みです。  
主な機能は以下の通りです:

- 実行エンジン (ExecutionEngine): 発注・リスク管理・注文管理を行う実行コンポーネント
- 監視サブシステム (Monitoring): システム状態、注文ログ、リスク監視、Kill Switch を提供
- ポートフォリオ構築ユーティリティ: 候補選定・重み付け・ポジションサイズ計算・セクター上限処理
- リサーチ（ファクター計算 / 特徴量探索）: DuckDB を用いたファクター計算・IC 計算など
- AI モジュール: OpenAI を用いたニュースセンチメント評価 / レジーム判定
- ユーティリティ: ログ設定、プロセス優先度設定、設定ウィザード、設定検証、レポート生成ツール

特徴
----
- 環境に応じた挙動:
  - KABUSYS_ENV=development / paper_trading / live をサポート
  - paper_trading モードは MockBroker を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH を使用）
- DuckDB と SQLite の併用:
  - DuckDB: 価格・財務データなどの分析用途（data/kabusys.duckdb 等）
  - SQLite: 監視・発注ログ（data/monitoring.db、ペーパートレード用は data/paper_trading.db）
- 安全機構:
  - Kill Switch（data/kill.flag）による安全停止
  - stop フラグ（data/stop_requested.flag）によりループ停止
  - リスク監視 (ドローダウン・ポジション上限) とアラート連携
- AI 統合（OpenAI）:
  - ニュースのセンチメントを LLM で評価して ai_scores に保存
  - マクロニュースと ETF MA200 を組み合わせた市場レジーム判定

セットアップ
-----------
前提
- Python 3.9+（型ヒント・モジュール API に合わせて）
- システムでの sqlite3 は標準ライブラリ、外部依存は以下を想定

推奨パッケージ（例）
- duckdb
- psutil
- openai
- PyYAML（config 検証でオプション）
- (必要に応じて) その他依存ライブラリ

インストール例
- 仮想環境作成:
  python -m venv .venv
  source .venv/bin/activate
- 必要パッケージをインストール:
  pip install duckdb psutil openai PyYAML

.env の準備
- プロジェクトルートに .env を用意します。自動ウィザードを利用できます:
  python -m kabusys.config_setup
- 主要な環境変数（例とデフォルト）:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
  - KABUSYS_ENV (development | paper_trading | live)
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
  - OPENAI_API_KEY （AI 機能を使う場合）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意：本番での通知用）
  - KILL_FLAG_CLEAR_ON_START (0 or 1) — 起動時に kill.flag を自動クリアするか

設定検証
- .env や config/*.yaml の検証を実行:
  python -m kabusys.validate_config
- --strict オプションで警告も失敗扱いにできます。

使い方（主要コマンド）
--------------------

起動スクリプト
- 実行エンジン（ExecutionEngine）を起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用して data/paper_trading.db に記録します。
  - 実行中の PID は data/execution.pid に書き込まれます（pid_file を Settings で上書き可）。
  - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
  - 停止は data/stop_requested.flag を作成することで行えます（監視側や管理ツールが作成）。

- 監視ループを起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
  - 監視は Settings.sqlite_path（本番監視 DB）を使用（KABUSYS_ENV に依らず本番 DB を参照）。
  - data/stop_requested.flag の存在でループを終了します。

ツール
- 証跡・検証レポート（Paper Trading レポート）:
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

AI 機能（プログラム内で利用）
- ニュースセンチメントのスコアリング:
  from kabusys.ai import score_news
  # conn は duckdb.connect(...) の接続
  score_news(conn, target_date, api_key="xxx")

- レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key="xxx")

ログ設定
- すべての起動スクリプトは kabusys.utils.logging_setup.setup_logging を使ってログを統一して出力します。
- ログの保存ディレクトリは LOG_DIR 環境変数、もしくはデフォルト logs/。日次ローテーション・30日保持。

停止 / Kill Switch
- ExecutionEngine を止めたい場合:
  - kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は ExecutionEngine に停止命令を出すための手段として KillSwitch から書き込まれます（Monitoring が検出して書き込む）。
  - data/stop_requested.flag を作ると run_* スクリプトのポーリングループが終了します（手動停止やシステム停止時に利用）。
- KillSwitch は閾値（ドローダウン、ポジション数）を満たすと冪等にファイルを書き込みます。

主要モジュール説明
-----------------

- kabusys.config
  - Settings クラスで .env / 環境変数を解決・検証します。
  - 自動的にプロジェクトルートの .env/.env.local を読み込みます（無効化可）。

- kabusys.run_execution
  - ExecutionEngine の起動スクリプト。プロセス優先度設定、DB 接続、エンジン実行を担当。

- kabusys.run_monitoring
  - SystemMonitor を用いたポーリングループを実行します。MONITOR_POLL_INTERVAL により間隔を設定可能。

- kabusys.monitoring.*
  - monitoring_db: 監視ログ用 SQLite のスキーマ初期化・永続化 API
  - system_monitor: CPU/メモリ/ディスク・PID ファイル・データ鮮度の監視
  - trade_monitor: 注文ログや約定の監視（詳細は該当実装を参照）
  - risk_monitor: ドローダウン・ポジション上限の監視とリスクログ記録
  - kill_switch: 条件に基づく kill.flag の書き込み
  - monitoring_engine: 上記 Monitor を束ねてポーリングしアラートや KillSwitch を評価

- kabusys.execution.*
  - ExecutionEngine / OrderManager / Reconciler / RiskManager 等（発注からリスク検査までの実行ロジック）

- kabusys.portfolio.*
  - portfolio_builder: 候補選定、重み計算（等配分・スコア配分）
  - position_sizing: 発注株数計算（risk_based / equal / score 等）
  - risk_adjustment: セクター上限適用、レジーム乗数

- kabusys.research.*
  - factor_research: momentum/volatility/value などのファクター計算（DuckDB を利用）
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリ

- kabusys.ai.*
  - news_nlp: OpenAI を用いたニュースのセンチメント評価（ai_scores へ書き込み）
  - regime_detector: ETF MA200 とマクロニュースを組み合わせたレジーム判定（market_regime へ書き込み）

ユーティリティ
- kabusys.utils.logging_setup: 共通ログ設定（コンソール + 日次ファイルローテーション）
- kabusys.utils.process_priority: psutil を使った優先度 / CPU affinity 設定

ディレクトリ構成（抜粋）
----------------------
以下は主なファイル・ディレクトリの抜粋（src/kabusys 配下）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (参照実装あり)
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - data/ (実行時に作成される想定)
      - monitoring.db (または指定した SQLITE_PATH)
      - paper_trading.db (ペーパートレード用)
      - kabusys.duckdb (DuckDB ファイル)
      - kill.flag / stop_requested.flag / execution.pid

注意事項・ベストプラクティス
-------------------------
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- KABUSYS_ENV=live の場合は本番運用用のパラメータ（LINE 通知、Kill Switch 設定等）を十分に確認してください。
- OpenAI を利用する機能は API キーが必要です。API 呼び出しの失敗やレート制限に対するフォールバック設計がされていますが、料金・レート制限に注意してください。
- monitoring は監視用 DB を使用しますが、run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番監視 DB）を参照します。テスト時は設定を切り替えてください。
- paper_trading モードは本番 DB と完全分離されるよう PAPER_TRADING_SQLITE_PATH を使用するため、誤って本番データを上書きしないよう注意してください。

参考コマンドまとめ
------------------
- 環境ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動:
  python -m kabusys.run_execution

- 監視起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
（ここにプロジェクトのライセンス情報や貢献ルールを記載してください）

最後に
------
この README はコードベース（src/kabusys/*）の主要機能をまとめた概要です。実装の詳細や追加の設定ファイル（config/*.yaml）は各モジュールのドキュメントやソース内コメントを参照してください。質問や追加のドキュメント化が必要であれば教えてください。