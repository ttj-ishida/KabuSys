KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買およびそれに付随する研究／監視ツール群です。本リポジトリは以下の主要機能を持つ Python パッケージ構成になっています。

- 注文実行エンジン（ExecutionEngine）
- 監視（Monitoring）コンポーネント（システム状態・注文ログ・リスク監視・Kill Switch）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- 研究用モジュール（ファクター計算・特徴量探索）
- AI 補助モジュール（ニュース NLP / レジーム判定）
- 運用支援ツール（設定ウィザード・設定検証、Paper Trading 検証レポート）

主な設計方針
- .env による環境変数管理（自動ロード機能あり）
- Paper Trading（KABUSYS_ENV=paper_trading）時は本番 DB とは分離された SQLite を使用
- OpenAI API を利用する機能は API キーを環境変数で指定
- ログは stdout と日次ローテートファイル（logs/*.log）に出力

機能一覧
--------
- 実行（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - Broker クライアントファクトリ経由で実際／モックのブローカーを利用
  - ExecutionEngine をバックグラウンドスレッドで実行。stop フラグファイルによる停止制御
- 監視（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行
  - kill.flag による ExecutionEngine 強制停止（Kill Switch）
  - MONITOR_POLL_INTERVAL でポーリング間隔変更可（デフォルト 60 秒）
- 設定ウィザード（config_setup.py）
  - 対話式に .env の初期作成・更新を支援
- 設定検証 CLI（validate_config.py）
  - 必須環境変数や config/*.yaml、DB パス等のチェック
  - --strict で警告も失敗（exit 1）扱いに可能
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB（data/paper_trading.db）から各種指標を集計・判定
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等金額／スコア加重、リスクベースの株数算出
  - セクターキャップ、レジーム乗数などの調整
- 研究（research パッケージ）
  - ファクター（Momentum/Value/Volatility）計算、将来リターン・IC・統計サマリー
- AI（ai パッケージ）
  - ニュースのセンチメントを OpenAI でスコア化（ai_scores へ保存）
  - 市場レジーム判定（ma200 + マクロニュースセンチメント）

セットアップ手順
----------------

1. Python バージョン
   - Python 3.10+ を推奨（ソース内の型注釈で | 演算子を使用）

2. 必要パッケージ（例）
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で YAML をパースする場合）
   - その他プロジェクト固有の依存がある場合は requirements.txt を用意している想定
   インストール例:
   - pip install duckdb psutil openai PyYAML

3. プロジェクトの初期化
   - リポジトリルートに data/ と logs/ ディレクトリを作成（多くのコードは自動作成するが権限問題を避けるため事前作成を推奨）
     - mkdir -p data logs

4. 環境変数の設定（.env）
   - 対話式ウィザードで .env を作る:
     - python -m kabusys.config_setup
   - 最低限必要な環境変数（validate_config でチェックされる）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 代表的な環境変数（デフォルト値があるもの）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO（DEBUG, INFO, WARNING, ERROR, CRITICAL）
     - OPENAI_API_KEY: OpenAI API を使う機能が必要な場合に設定

5. 設定検証
   - python -m kabusys.validate_config
   - 開発中に厳密モードでチェックする場合:
     - python -m kabusys.validate_config --strict

使い方
------

起動・停止関連
- ExecutionEngine 起動（本番 / ペーパーは KABUSYS_ENV に依存）:
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と完全分離）。
    - 起動前に data/kill.flag が存在すると起動をスキップします（kill flag は停止のための意図的なスイッチ）。
    - 実行中はデフォルトで data/execution.pid に PID を書きます。
    - 停止させる場合は data/stop_requested.flag を作成するか、ExecutionEngine の停止 API を使います（ファイルベースのインタロック）。

- Monitoring 起動:
  - python -m kabusys.run_monitoring
  - 特記事項:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - 監視プロセスは本番 sqlite_path を常に参照して監視データを保存します（KABUSYS_ENV にかかわらず）。
    - 停止は data/stop_requested.flag を作成することで行います。

ログ
- setup_logging により stdout と logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリ）。
- LOG_LEVEL で出力レベルを制御。

Paper Trading 検証レポート
- ペーパートレード DB からレポートを生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを直接指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

AI 機能
- OpenAI API を使うためには OPENAI_API_KEY を .env に設定するか関数呼び出し時に api_key を渡す必要があります。
- ai.news_nlp.score_news や ai.regime_detector.score_regime は API failures に対してフェイルセーフ（スコアを 0 にフォールバックなど）を実装しています。

停止フラグ / Kill Switch
- kill.flag（デフォルト: data/kill.flag）:
  - KillSwitch により書き込まれるファイル。存在すると ExecutionEngine に停止シグナルを送ります（Execution 起動時の安全対策）。
  - KillSwitch は一度書き込むと上書きせず冪等性を担保します。
- stop_requested.flag（data/stop_requested.flag）:
  - run_execution / run_monitoring が監視している「即時停止」フラグ。存在を検知するとループを抜け安全終了します。

注意点 / 運用上のヒント
- KABUSYS_ENV=live の場合は本番運用になります。validate_config の live ガードを必ず確認してください（LINE 設定や Kill Flag 設定など）。
- データ鮮度やプロセス異常は Monitoring が検知して alert_manager 経由で通知する想定です（LINE や他チャネルの設定は .env で行います）。
- DuckDB は分析用 DB、SQLite は監視・注文履歴用（軽量）の役割分担です。
- OpenAI の呼び出しはレート制限や 5xx を考慮したリトライロジックを含みますが、APIキー管理は慎重に行ってください。

ディレクトリ構成
----------------
（src/kabusys 配下の主要ファイルと概略）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数/設定読み込みロジック（.env 自動ロード含む）
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 起動前設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading の検証レポート生成
    - ai/
      - news_nlp.py            — ニュース NLP（OpenAI）で ai_scores 書込み
      - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）
    - monitoring/
      - monitoring_db.py       — SQLite を使った永続化層（テーブル作成・アクセス）
      - system_monitor.py      — システム状態・データ鮮度監視
      - trade_monitor.py       — （存在）取引ログ監視（ファイル内参照）
      - risk_monitor.py        — ドローダウン・ポジション上限監視
      - kill_switch.py         — Kill Switch 実装（flag ファイル書込）
      - monitoring_engine.py   — 各モニタを束ねるエンジン
      - alert_manager.py       — （存在）アラート送信処理（LINE 等）
    - execution/
      - execution_engine.py    — ExecutionEngine の本体（起動・注文処理）
      - order_manager.py       — 発注管理
      - order_repository.py    — 注文履歴保存
      - broker_factory.py      — BrokerClient の生成（本番 / モック）
      - reconciler.py          — 注文状態整合
      - risk_manager.py        — 実行時リスク管理
    - portfolio/
      - portfolio_builder.py   — 銘柄選定・スコアソート
      - risk_adjustment.py     — セクターキャップ・レジーム乗数
      - position_sizing.py     — 株数算出・上限チェック
    - research/
      - factor_research.py     — Momentum/Value/Volatility 等のファクター計算
      - feature_exploration.py — 将来リターン・IC・統計サマリ
    - utils/
      - logging_setup.py       — ログ設定ユーティリティ（stdout + 日次ファイル）
      - process_priority.py    — プロセス優先度 / CPU affinity 設定
    - data/                    — 実行時生成データ（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db 等）
    - logs/                    — ログ保存ディレクトリ（logs/<app_name>.log）

付録：よく使うコマンド例
-----------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動:
  - python -m kabusys.run_execution

- Monitoring 起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
-----
この README はコードベースから抽出できる情報を基に作成しています。運用・デプロイ時は validate_config によるチェックと .env の適切な管理、ログの監視を必ず行ってください。必要なら systemd / Supervisor / Docker 等でプロセス管理を行うことを推奨します。問題や不明点があれば該当するモジュール（例: monitoring/*.py, execution/*.py）を参照してください。