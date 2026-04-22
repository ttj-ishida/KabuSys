KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うための小規模なシステム群です。本リポジトリには以下の主要機能を持つモジュールが含まれます。

- 実際の注文発行とペーパートレードを切り替え可能な ExecutionEngine
- システム稼働状況・発注ログ・リスク監視を行う Monitoring（Kill Switch を含む）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算）
- 研究用ファクター計算・特徴量探索モジュール（DuckDB を利用）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（ニュースセンチメント、レジーム判定）
- ペーパートレード検証レポート作成ツール等のユーティリティ

特徴一覧
---------
- ExecutionEngine は KABUSYS_ENV により paper_trading / live / development を切替可能。paper_trading 時は MockBroker を用いて data/paper_trading.db へ記録し、本番 DB と分離。
- Monitoring は system_status / trade_logs / positions / risk_logs / dashboard を SQLite に永続化。ポーリングループで定期チェック・アラート・Kill Switch 評価を実施。
- Portfolio モジュールは純粋関数群（DB を参照しない）で、候補選定、等配分・スコア配分、リスク調整、ポジションサイズ決定などを提供。
- Research モジュールは DuckDB 接続を受け取り、価格・財務テーブルからファクターや将来リターン、IC などを計算。
- AI モジュールは OpenAI API（gpt-4o-mini 想定）でニュースをスコアリングし ai_scores / market_regime に書き込む。API 失敗時はフェイルセーフ動作。
- ロギングは統一された setup_logging を通してコンソール（stdout）と logs/*.log（日次ローテーション）へ出力。
- 設定ウィザード（config_setup.py）と事前検証 CLI（validate_config.py）を同梱。

セットアップ手順
----------------

1. 前提
   - Python 3.9+（typing の構文や一部ライブラリを想定）
   - システムに以下のパッケージをインストール:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
   - 例（pip）:
     pip install duckdb psutil openai

   ※requirements.txt がある場合はそれを使用してください（本サンプルでは同梱されていません）。

2. プロジェクトルートの確認
   - 本 README と同じ階層に src/ があり、パッケージは src/kabusys 以下に配置されています。
   - .git または pyproject.toml を基準に自動でプロジェクトルート判定を行います。

3. .env の作成（推奨）
   - 対話式ウィザードで .env を初期作成:
     python -m kabusys.config_setup
   - ウィザードで J-Quants トークン、kabu API パスワード、KABUSYS_ENV（development/paper_trading/live）などを入力します。
   - 作成後、以下コマンドで設定の簡易検証を行います:
     python -m kabusys.validate_config

   注意:
   - .env は絶対にリポジトリにコミットしないでください（API キー等を含むため）。

4. 環境変数の注意点
   - .env は自動読み込みされます（config.py）。自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV (development|paper_trading|live)（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db） — Monitoring が使用する DB（Monitoring は環境にかかわらず本番 sqlite_path を使用します）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（DEBUG/INFO/...）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒, デフォルト: 60）

使い方
------

主な実行スクリプト（パッケージ化されたモジュールとして実行します）:

- 設定ウィザード:
  python -m kabusys.config_setup

- 設定検証（起動前チェック）:
  python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いになります。

- ExecutionEngine 起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 実行中は data/execution.pid に PID を書きます。
  - 停止は data/stop_requested.flag の作成（空ファイル）で行えます（スクリプトは起動時に stop flag をチェックします）。

- Monitoring 起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60）。
  - Monitoring は sqlite_path（.env の SQLITE_PATH）の DB に対して動作します（環境にかかわらず本番 sqlite_path を使う点に注意）。
  - 停止は data/stop_requested.flag の作成で行えます。
  - Monitoring は system/process/trade/risk を定期チェックし、必要に応じて kill.flag を書きます。

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルトの DB パスは 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

- AI 関連（プログラムから呼び出す API）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、結果をテーブルへ書き込みます。API キーは OPENAI_API_KEY または引数で指定。

停止・Kill Switch
-----------------
- 手動停止フラグ:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検出して正常終了します。
- Kill Switch:
  - モニタがリスク閾値を超えた場合（ドローダウンやポジション上限）、kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）を作成することで ExecutionEngine 側に停止シグナルを送ります。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアする動作になります（本番では 0 を推奨）。

ログ
---
- ロギングは kabusys.utils.logging_setup.setup_logging を経由して統一されます。
- デフォルトのログディレクトリは logs/、ファイル名は <app_name>.log（例: logs/execution.log, logs/monitoring.log）で日次ローテーション（30日分保持）。

ディレクトリ構成
----------------

src/kabusys/
- __init__.py
- config.py
  - .env 自動読み込み、Settings クラス（環境変数のラッパ）
- config_setup.py
  - 対話式 .env 作成ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 切替、PID 管理、stop flag 処理）
- run_monitoring.py
  - Monitoring のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py — ETF + マクロニュースで市場レジーム判定
- portfolio/
  - portfolio_builder.py — 候補選定・重み算出
  - position_sizing.py — 株数決定・資金配分・丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー等
- monitoring/
  - monitoring_db.py — SQLite スキーマと永続化 API
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 発注ログ監視（存在）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の書き込みロジック
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - alert_manager.py — （アラート送信のインターフェース。LINE 等の送信実装が想定されます）
- execution/
  - broker_factory.py — ブローカークライアント生成（本番 / Mock 切替）
  - execution_engine.py — 発注実行ロジック（セッション管理）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 注文管理周りの実装
- data/ (実行時に作成されることが多い)
  - monitoring.db（デフォルト SQLite）
  - paper_trading.db（ペーパートレード用）
  - kill.flag / stop_requested.flag / execution.pid
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- research, portfolio, monitoring ほかの補助モジュール

追加メモ / ベストプラクティス
-----------------------------
- 本番運用時は必ず KABUSYS_ENV=live とし、.env の内容を慎重に管理してください。
- validate_config を用いて起動前チェックを行ってください（--strict 推奨）。
- OpenAI を利用する機能は API コストとレート制限に注意してください。テスト時はモック化推奨。
- ログや DB ファイル（data/、logs/）は適切にローテーション・バックアップしてください。
- 開発時に .env を直接編集する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を理解してから行ってください。

ライセンス・貢献
----------------
- （ここにライセンス表記を入れてください。例: MIT License 等）
- バグ報告・機能改善の提案は issue / PR にてお願いします。

以上がこのコードベースの概略 README です。必要であれば、各モジュールの API 使用例（サンプルコード）やデプロイ手順（systemd / cron / コンテナ化）についても追記できます。どの部分を詳細化しますか？