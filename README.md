README
======

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
シグナル生成・ポートフォリオ構築・発注（本番/ペーパー）・監視・リスク管理・研究用ツール群を含みます。  
本リポジトリは、実運用を想定したコンポーネント分割（Execution / Monitoring / Research / AI / Portfolio / Utils）で実装されています。

主な特徴
--------
- ExecutionEngine：ブローカクライアント経由で発注を行う実行エンジン（本番/ペーパー切替対応）
- Monitoring：システム状態、注文ログ、リスク（ドローダウン/ポジション上限）を定期監視しアラート・Kill Switch を発動
- Portfolio 構築：候補選定、重み計算、ポジションサイズ計算、セクター制限などの純粋関数実装
- Research：DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）および統計解析
- AI モジュール：OpenAI を使ったニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）
- ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード、構成検証、レポート生成ツール等
- ペーパートレード用の分離 DB（data/paper_trading.db）をサポートし、本番 DB と安全に分離可能

必要条件（例）
--------------
- Python 3.9+
- 必須パッケージ（一部）:
  - duckdb
  - psutil
  - openai
- 任意（機能拡張用）:
  - PyYAML（config/*.yaml の検証に使用）
- SQLite（Python に標準同梱）

セットアップ手順
---------------
1. リポジトリをクローンしてワークディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （YAML 検証を行う場合）pip install PyYAML

4. 初期ディレクトリ作成
   - mkdir -p data logs

5. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - または .env.example を参考に手動で作成

6. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

主要な環境変数
----------------
主な変数（ .env で設定）:
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
  - paper_trading: MockBroker を使用して data/paper_trading.db に記録（本番 DB と分離）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を利用する機能で使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB (monitoring) のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/...）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（起動 / 各コマンド）
-------------------------

- 設定ウィザード（.env の生成・更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録
    - 起動時に data/stop_requested.flag が存在すると起動を中止
    - PID ファイルは data/execution.pid（Settings.pid_file_path で上書き可）

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず同一路径）

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

- Research / AI モジュールの利用（プログラム内呼び出し）
  - DuckDB 接続を構築して以下の関数を呼ぶ例:
    - from kabusys.research import calc_momentum
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - OpenAI を使う関数は OPENAI_API_KEY を要求する（引数で渡すことも可）

プロセス制御とフラグ
--------------------
- stop_requested.flag:
  - run_monitoring/run_execution はプロジェクト内 data/stop_requested.flag を検知して安全に終了する
- kill.flag:
  - KillSwitch が条件を満たすと data/kill.flag を作成し ExecutionEngine に停止シグナルを送る
  - KILL_FLAG_CLEAR_ON_START=1 を設定するとエンジン起動時に kill.flag を自動クリア（本番では推奨しない）
- PID ファイル:
  - ExecutionEngine は起動時に pid ファイルを書きます（デフォルト data/execution.pid）

ログ
----
- ログはデフォルトで stdout とファイル（logs/<app_name>.log）に出力されます。
- LOG_DIR 環境変数でログ保存先を変更可能。ログは日次ローテーションされ 30 日分保持されます。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数解決・Settings クラス
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前の設定検証 CLI

run スクリプト
- run_execution.py
  - ExecutionEngine の起動スクリプト（KABUSYS_ENV により本番/ペーパーの挙動を切替）
- run_monitoring.py
  - SystemMonitor を定期実行する監視用スクリプト

monitoring/
- monitoring_db.py
  - SQLite を使った監視ログの永続化層（テーブル定義・CRUD）
- monitoring_engine.py
  - 各 Monitor を束ねるポーリング実装
- system_monitor.py
  - CPU/メモリ/ディスク、データ鮮度、プロセス死活などのチェック
- trade_monitor.py
  - 注文ログの整合性・滞留注文・価格異常チェック（実装参照）
- risk_monitor.py
  - ドローダウン・ポジション上限のチェック
- kill_switch.py
  - フラグファイルによる停止シグナル制御
- alert_manager.py
  - （通知送信）アラート管理（実装ファイル参照）

execution/
- execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 発注ロジック・リスク管理・ブローカ抽象化など

portfolio/
- portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定・重み・株数決定・セクター制限・レジーム乗数

research/
- factor_research.py, feature_exploration.py
  - DuckDB によるファクター計算・将来リターン・IC 計算など

ai/
- news_nlp.py
  - ニュースをまとめて LLM でセンチメント評価、ai_scores テーブルへ書き込み
- regime_detector.py
  - ETF MA とマクロニュースを組合せたレジーム判定、market_regime へ保存

utils/
- logging_setup.py
  - 統一ログ設定（stdout + 日次ファイル）
- process_priority.py
  - psutil を利用したプロセス優先度 / CPU affinity 設定

tools/
- paper_verification_report.py
  - ペーパートレードの検証レポート出力スクリプト

開発・運用メモ
--------------
- Paper Trading は本番 DB と分離する設計です（PAPER_TRADING_SQLITE_PATH を利用）。
- run_monitoring は監視用 DB（Settings.sqlite_path）を常に使用します（KABUSYS_ENV に依存しない）。
- OpenAI 関連機能は API 呼び出し失敗時にフォールバック動作を行うよう設計されています（安全重視）。
- DuckDB を用いたデータ分析機能は、prices_daily / raw_financials / raw_news 等のテーブルを前提としています。
- config/*.yaml はプロジェクト固有の設定を想定しています。PyYAML があれば validate_config で内容のパース検証を行います。

よくある起動例
--------------
- 初期セットアップ（ウィザード + 検証）
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- デバッグ（開発環境）
  - export KABUSYS_ENV=development
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

- ペーパートレード
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
----
本 README はコードベースの主要機能と起動手順をまとめたものです。実行前に必ず python -m kabusys.validate_config による検証を行ってください。各モジュールの詳細な仕様はソース内の docstring を参照してください。

質問や追加したいドキュメント項目があれば教えてください。