KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買・研究・監視ツール群（KabuSys）の主要コンポーネントを含みます。  
README はコードベースから抽出した使い方・セットアップ手順・機能説明を日本語でまとめたものです。

概要
----
KabuSys は次の主要機能を提供します。

- 注文実行エンジン（ExecutionEngine） — 本番 / ペーパートレード（完全分離）をサポート
- 監視（Monitoring） — システム状態・注文ログ・リスク（ドローダウン・保有数）を定期的に記録・アラート
- ポートフォリオ構築ユーティリティ — 候補選定・重み計算・株数決定・セクター制限など純粋関数群
- リサーチ（Research） — ファクター計算（モメンタム／バリュー／ボラティリティ）と特徴量解析（IC 等）
- AI モジュール — ニュースの NLP スコアリング（OpenAI を利用）、市場レジーム判定
- ユーティリティ群 — ロギング設定、プロセス優先度設定、設定ウィザード、設定検証、レポート生成 など

主な機能一覧
--------------
- Execution
  - run_execution.py: ExecutionEngine 起動スクリプト
  - paper_trading モードでは MockBrokerClient を使用し paper_trading.db に記録
  - stop フラグ（data/stop_requested.flag）や execution.pid を利用した起動/停止制御
  - RiskManager / Reconciler / OrderManager 等の組み立て
- Monitoring
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプト
  - MonitoringEngine: System / Trade / Risk Monitor をまとめて定期実行、KillSwitch による停止シグナル出力
  - MonitoringDB: SQLite ベースで system_status / trade_logs / positions / risk_logs / dashboard を管理
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- Portfolio
  - 候補選定（select_candidates）、重み計算（等重・スコア加重）、ポジションサイズ計算（複数方式）
  - セクターキャップ適用、レジーム乗数計算
- Research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン・IC・統計サマリー（calc_forward_returns, calc_ic, factor_summary）
  - DuckDB を用いたテーブル参照ベースの処理
- AI
  - news_nlp.score_news: OpenAI を使ってニュースを銘柄ごとにセンチメントスコア化し ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースの LLM 評価を合成して market_regime を更新
  - OpenAI API リクエストはリトライ・バックオフやレスポンス検証を含む堅牢な実装
- ツール
  - config_setup.py: .env の対話式作成 / 更新ウィザード
  - validate_config.py: .env / config/*.yaml の起動前チェック CLI
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成（稼働率・成功率・レイテンシ等）
- ユーティリティ
  - utils/logging_setup.py: stdout + 日次ローテートファイルログの統一設定
  - utils/process_priority.py: Windows / POSIX を吸収して優先度 / CPU affinity を設定

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... (省略)

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows PowerShell: .venv\Scripts\Activate.ps1）

3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt  
     主な必要パッケージ（コード参照）:
       - duckdb
       - psutil
       - openai  （AI 機能を使う場合）
       - PyYAML（validate_config.py の YAML 検証を使う場合）

4. 環境変数（.env）を用意
   - 対話式ウィザード:
       python -m kabusys.config_setup
     これにより .env を生成できます（.env を Git にコミットしないでください）。
   - 自動ロード
     - 起動時、リポジトリルートの .env と .env.local が自動読み込みされます（OS 環境変数を上書きしない）。
     - 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - そのほかオプション: KABUSYS_ENV（development / paper_trading / live）、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等

主要デフォルトパス / ファイル
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper trading SQLite: data/paper_trading.db
- ログディレクトリ: logs/
- kill flag: data/kill.flag
- stop flag: data/stop_requested.flag
- execution pid: data/execution.pid

使い方（よく使うコマンド）
-------------------------
- 設定ウィザード（.env 作成 / 更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）
    例: python -m kabusys.validate_config --strict

- 監視プロセスの起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でループ間隔を秒単位で変更可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は設定にかかわらず本番 sqlite_path を使用して監視テーブルを操作します（monitoring 用 DB を共通で使用）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在すると起動しません
  - 停止させるには data/stop_requested.flag を作成するか、KillSwitch（data/kill.flag）経由で停止することもあります

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

- プログラム API（ライブラリとして利用）
  - ポートフォリオ関数:
      from kabusys import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - リサーチ関数（DuckDB 接続を渡す）:
      from kabusys.research import calc_momentum, calc_volatility, calc_value
  - AI スコアリング:
      from kabusys.ai import score_news
      score_news(conn, target_date, api_key=...)
    - score_regime は kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

運用に関する注意
----------------
- .env は決してリポジトリにコミットしないでください（config_setup.py も注意書きを出します）。
- 本番環境では KABUSYS_ENV=live を設定する前に validate_config.py で入念にチェックしてください。
- Monitoring は設定にかかわらず本番 sqlite_path（デフォルト data/monitoring.db）を使います。ペーパートレード DB は run_execution が分離して使用します。
- AI 機能は OPENAI_API_KEY が必須です。API 呼び出しの失敗はフェイルセーフに設計されていますが、APIキー未設定だと例外になります。
- ログは stdout（コンソール）と logs/<app_name>.log（日時ローテート）に出力されます。ログディレクトリ作成に失敗した場合はコンソールのみで継続します。

設定 / 起動時の便利な環境変数
- KABUSYS_ENV: development | paper_trading | live （default: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（default: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（default: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを抑制

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py                          — パッケージ定義（version）
- config.py                            — Settings クラス（環境変数読み込み・.env 自動ロード）
- config_setup.py                      — .env 対話式ウィザード
- validate_config.py                   — 設定検証 CLI
- run_execution.py                     — ExecutionEngine 起動スクリプト
- run_monitoring.py                    — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py                         — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py                  — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py                    — SQLite persistence 層（テーブル作成 / CRUD）
  - system_monitor.py                   — システム状態・データ鮮度監視
  - trade_monitor.py                    — （注文周りの監視）※実装ファイルがある想定
  - risk_monitor.py                     — ドローダウン・ポジション数監視
  - monitoring_engine.py                — 各 Monitor を束ねるエンジン
  - kill_switch.py                       — kill.flag 書き込みユーティリティ
  - alert_manager.py                     — （通知管理）※実装ファイルがある想定
- portfolio/
  - portfolio_builder.py                — 候補選定 / 重み計算
  - position_sizing.py                  — 株数決定・投下資金制限
  - risk_adjustment.py                  — セクターキャップ・レジーム乗数
- research/
  - factor_research.py                  — momentum/volatility/value ファクター計算
  - feature_exploration.py              — forward returns / IC / summary
- utils/
  - logging_setup.py                    — 統一ロギング設定
  - process_priority.py                 — プロセス優先度 / CPU affinity
- tools/
  - paper_verification_report.py        — ペーパートレード検証レポート
- monitoring/monitoring_db.py (上記参照)

バージョン
---------
パッケージバージョンは src/kabusys/__init__.py の __version__ で管理されています（現状 0.1.0）。

最後に
------
この README はソースコードの構成とコメントを基に作成しています。実際の運用時は環境変数・DB パス・ログ設定を環境に合わせて調整し、validate_config.py で起動前チェックを必ず行ってください。質問や追加のドキュメント（API 使用例や設計ドキュメント）の生成を希望する場合は教えてください。