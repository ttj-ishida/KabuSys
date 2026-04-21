README
======

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした軽量フレームワークです。本リポジトリは以下の主要機能を提供します。

- ExecutionEngine：発注・リスク管理・約定の処理（本番/ペーパートレード対応）
- Monitoring：システム状態・注文状況・リスク指標のポーリング監視、Kill Switch の発動
- Portfolio モジュール：銘柄選定、重み計算、ポジションサイズ計算、セクター制限など
- Research / AI：DuckDB を使ったファクター計算・特徴量解析、ニュースの LLM ベース評価（OpenAI）
- ユーティリティ：環境設定ウィザード、設定検証、ログ設定、プロセス優先度設定 等
- ツール：ペーパートレード検証レポート生成スクリプト など

機能一覧
--------
主な機能（抜粋）：

- 環境管理
  - .env 自動ロード（.env / .env.local、OS 環境変数優先）
  - 対話式ウィザードで .env を生成・更新（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 実行エンジン
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - OrderManager / RiskManager / Reconciler 組み合わせで発注を実行
  - 停止制御：data/stop_requested.flag を監視して優雅に停止

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス生存チェック
  - TradeMonitor: 注文滞留／約定異常の検出（trade_logs を参照）
  - RiskMonitor: ドローダウン・保有数上限チェック、ダッシュボード更新
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：各 Monitor の統合ポーリング、Alert 通知フック

- ポートフォリオ構築
  - 候補選定（スコア順）: select_candidates
  - 重み算出: 等分配 / スコア加重
  - ポジションサイズ計算: risk_based / equal / score（lot 単位丸め、aggregate cap）
  - セクターキャップ / レジーム乗数の適用

- 研究・分析
  - DuckDB を用いたファクター（Momentum / Volatility / Value）計算
  - 将来リターン計算、IC（Spearman）などの統計ユーティリティ
  - paper_verification_report：ペーパートレード DB から検証レポート生成

- AI（OpenAI）
  - news_nlp.score_news：ニュース記事を LLM で評価し ai_scores に書き込み
  - regime_detector.score_regime：ETF MA とマクロニュースを組み合わせた市場レジーム判定
  - 再試行・フェイルセーフを組み込んだ API 呼び出し実装

セットアップ手順
----------------

前提
- Python 3.10 以上（型ヒントに | を使用）
- SQLite は標準ライブラリで利用可能
- 必要な Python パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config 検証で YAML 検査を行いたい場合、任意）

例: 仮想環境の作成とパッケージインストール
1. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install duckdb psutil openai pyyaml

環境変数設定
- 対話式ウィザードで .env を生成するのが簡単です:
  - python -m kabusys.config_setup
- 重要な環境変数（主なもの）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY（AI 機能を使う場合）
  - LOG_LEVEL（任意、例: INFO / DEBUG）
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml 基準）から行われます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ファイル・ディレクトリ (data/logs)
- data/: DB ファイル、PID/flag ファイルを配置する想定です（実行時に自動作成されます）。
  - data/execution.pid, data/stop_requested.flag, data/kill.flag など
- logs/: アプリケーションログ（setup_logging）を出力します。

使い方
------

設定検証
- .env を作成したらまず検証:
  - python -m kabusys.validate_config
  - 警告も厳格に扱う場合: python -m kabusys.validate_config --strict

実行エンジン（Execution）
- ExecutionEngine を起動:
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存:
    - paper_trading: MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録。実際の発注は行わない。
    - live: 本番ブローカーを使用（設定を十分に確認してください）。
- 停止:
  - プロセスは data/stop_requested.flag の存在をポーリングして停止します。手動で停止させる場合は stop フラグを作成します（例: touch data/stop_requested.flag）。
  - また kill.flag（data/kill.flag）は KillSwitch によって書き込まれ、ExecutionEngine が反応して停止するトリガーとして使われます。

監視（Monitoring）
- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は Settings.env にかかわらず本番の sqlite_path（SQLITE_PATH）を使用して監視テーブルを初期化します。
  - 停止: run_monitoring は data/stop_requested.flag を検知すると終了します。

ペーパートレード検証レポート
- ペーパートレード結果の要約レポートを生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（未指定時は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

AI 機能
- ニュース評価（ai/news_nlp.py）やレジーム判定（ai/regime_detector.py）は OpenAI API キーを必要とします。環境変数 OPENAI_API_KEY を設定するか、関数に api_key 引数を渡してください。
- これらは LLM 呼び出しで外部通信を行うため、API 利用料とレイテンシに注意してください。実行は冪等性やフェイルセーフ（失敗時はスキップ・デフォルト値採用）を考慮して実装されています。

ログとプロセス優先度
- 共通ログ設定: kabusys.utils.logging_setup.setup_logging を各起動スクリプトが呼び出します。logs/<app_name>.log に日次ローテートで出力されます（デフォルト logs/）。
- 起動スクリプトは起動時に set_process_priority("high") を呼び出してプロセス優先度を調整します（権限不足等で失敗しても安全にスキップされます）。

停止/フラグ周りの運用メモ
- stop_requested.flag（data/stop_requested.flag）
  - run_execution / run_monitoring がポーリングし、存在を検知すると優雅にシャットダウンします。手動で停止したい場合に利用します。
- kill.flag（data/kill.flag）
  - KillSwitch がリスク条件を満たすと書き込み、ExecutionEngine に停止を促します。
- PID ファイル: data/execution.pid（ExecutionEngine 用）

ディレクトリ構成
----------------

以下は主要ファイル・モジュールの一覧（src/kabusys 以下）。実際のツリーは差分がある場合がありますが、主要な役割を併せて記載します。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"

  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト
    - KABUSYS_ENV により paper_trading モードを切替

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL で間隔を設定可能

  - config.py
    - 環境変数 / .env の読み込みと Settings クラス（各種パス・閾値・フラグの取得）

  - config_setup.py
    - 対話式 .env 生成ウィザード（python -m kabusys.config_setup）

  - validate_config.py
    - 設定検証 CLI（python -m kabusys.validate_config）

  - utils/
    - logging_setup.py：統一的なログ設定（stdout + 日次ローテーション）
    - process_priority.py：プロセス優先度・CPU affinity 設定ユーティリティ
    - __init__.py

  - portfolio/
    - portfolio_builder.py：候補選定・等分/スコア重み
    - position_sizing.py：株数決定・aggregate cap・lot 丸め
    - risk_adjustment.py：セクターキャップ・レジーム乗数
    - __init__.py

  - monitoring/
    - monitoring_db.py：SQLite ベースの監視ログ永続化層（テーブル初期化・CRUD）
    - system_monitor.py：システム状態・データ鮮度のチェック
    - trade_monitor.py：trade_logs 監視（滞留・異常等）  ←（ファイル内に実装あり）
    - risk_monitor.py：ドローダウン・ポジション上限の監視
    - kill_switch.py：kill.flag 書き込みロジック
    - monitoring_engine.py：各 Monitor の統合ポーリング
    - alert_manager.py：アラート通知管理（LINE 等のプラグインを想定）

  - execution/
    - execution_engine.py：エンジン本体（セッション管理・ワークフロー）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py / broker_factory.py
      - 発注・再確認・リスク管理・ブローカー抽象化（実ブローカーと MockBroker の切替想定）

  - research/
    - factor_research.py：Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py：将来リターン計算・IC・統計サマリー
    - __init__.py

  - ai/
    - news_nlp.py：ニュースの LLM スコアリング（ai_scores への永続化）
    - regime_detector.py：ETF MA とマクロニュースを用いた市場レジーム判定
    - __init__.py

  - data/ （実行時に利用するディレクトリ、README としての説明）
    - monitoring.db（SQLITE_PATH）
    - kabusys.duckdb（DUCKDB_PATH）
    - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
    - execution.pid
    - stop_requested.flag
    - kill.flag

  - tools/
    - paper_verification_report.py：ペーパートレード検証レポート生成 CLI
    - __init__.py

運用上の注意点
--------------
- 本番（KABUSYS_ENV=live）では設定ミスが重大な問題（実際の発注）を招くため、validate_config による事前チェックを必ず実行してください。
- .env は秘密情報を含むため絶対にコミットしないでください（config_setup.py のヘッダにも注意喚起あり）。
- OpenAI 等の外部 API を使う機能は API コストが発生します。テストではモックや環境変数を調整して実行してください。
- DuckDB / SQLite のデータファイルは実行環境でバックアップやローテーションを検討してください。
- process priority / cpu affinity の変更は権限によって失敗する場合があります（ログで警告が出ます）。

ライセンス・貢献
----------------
（ライセンスファイルをプロジェクトルートに置いてください。README ではライセンスの種類と貢献方法を明示してください。）

補足
----
この README はコードベースの主要機能と運用方法の概要を記載しています。個別モジュールの詳細な API やパラメータは該当モジュール（src/kabusys 以下の各ファイル）の docstring と型注釈を参照してください。必要であれば各モジュールごとの使用例・デザインドキュメントを追加できます。