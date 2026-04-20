KabuSys
======

バージョン: 0.1.0

概要
----
KabuSys は日本株の自動売買／研究プラットフォームです。本リポジトリには、以下の主要機能を備えたモジュール群が含まれます。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理の実行
- 監視（Monitoring）: プロセス監視・データ鮮度・リスク監視・アラート、Kill Switch
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出、セクター制限
- リサーチ: ファクター生成（モメンタム・バリュー・ボラティリティ等）、特徴量解析（IC 等）
- AI 支援: ニュースの NLP スコアリング、レジーム判定（OpenAI を利用）
- ツール: ペーパートレード検証レポート生成、環境設定ウィザード、設定検証 CLI
- ユーティリティ: ロギング設定、プロセス優先度設定、DB 永続化ヘルパー等

機能一覧
--------
主な機能（抜粋）:

- Execution
  - BrokerClientFactory によるブローカークライアント抽象化（paper_trading 時はモック）
  - OrderManager / OrderRepository による注文管理
  - RiskManager によるポジション・投下資金・回路遮断の管理
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス稼働チェック、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常等の検出（コードベース参照）
  - RiskMonitor: ドローダウン、ポジション数上限の監視とリスクログ記録
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 上記をまとめたポーリングループ
- Portfolio
  - 候補選定（スコア降順）、等配分・スコア加重配分、リスクベース配分
  - セクターキャップ適用、レジーム乗数
- Research
  - DuckDB を用いたファクター計算（prices_daily / raw_financials ベース）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- AI
  - OpenAI を用いたニュースセンチメント scoring（ai_scores テーブルへ保存）
  - 市場レジーム判定（ma200 + マクロセンチメントの合成）
- Tools
  - .env ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート（tools/paper_verification_report.py）

前提条件
--------
- Python 3.10+（型注釈の Union 表記などを利用）
- 推奨ライブラリ:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証時に任意）
- 開発環境: 仮想環境 (venv, pipenv, poetry 等) を推奨

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動:
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール:
   - pip install duckdb psutil openai
   - （YAML 検証を行う場合は pip install pyyaml）

   ※ requirements.txt がある場合:
   - pip install -r requirements.txt

4. 環境変数設定 (.env):
   - 対話式ウィザードを使って .env を作成:
     - python -m kabusys.config_setup
   - または .env を手動で作成。主要な環境変数：
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 時の専用 DB、デフォルト: data/paper_trading.db)
     - LOG_LEVEL (DEBUG/INFO/...)
     - OPENAI_API_KEY（AI 機能利用時に必要）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用、任意）
   - 自動ロード:
     - パッケージ起動時にプロジェクトルートの .env / .env.local が自動で読み込まれます。
     - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. 設定検証（任意）:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方
------
主な起動スクリプト／CLI:

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と完全分離）
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中に data/stop_requested.flag を検知するとエンジンに stop() を呼び出します
    - pid ファイル: data/execution.pid（設定により変更可）
- 監視ループ（Monitoring）を起動:
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60 秒）
    - Monitoring は実行環境にかかわらず settings.sqlite_path（本番用監視 DB）を使用します
    - 停止方法: プロジェクトルートの data/stop_requested.flag ファイルを作成するとループを終了します
- 環境設定ウィザード:
  - python -m kabusys.config_setup
  - .env を対話式に作成・更新します
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いになります
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB は --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH を指定

主要な環境変数（抜粋）
--------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: ログレベル（例: INFO）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 用）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1、本番は 0 推奨）

停止・Kill Switch の仕組み
------------------------
- data/stop_requested.flag:
  - run_monitoring / run_execution はこのファイルの存在を検知すると再起動ループ/エンジンを終了します
- data/kill.flag:
  - KillSwitch（監視ロジック）が条件を満たした際にこのファイルを書き込み、ExecutionEngine に停止信号を送る運用に使用します
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動クリアされますが、本番では 0 が推奨されます

開発・テストのヒント
--------------------
- DuckDB / SQLite のパスは .env で設定できるため、ローカルでテスト用 DB を用意して実行してください
- OpenAI を使ったテストは API レートやコストに注意。ユニットテストでは API 呼び出しをモックしてください
- logging_setup.setup_logging() を各スクリプト冒頭で呼ぶことでログの出力先（stdout + 日次ファイル）を統一できます
- process_priority.set_process_priority() は権限により失敗することがあるため、その場合は警告が出て処理は継続します

ディレクトリ構成
----------------
（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み・Settings
  - config_setup.py           — .env ウィザード CLI
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite 永続化レイヤ
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — システム・データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - trade_monitor.py        — 注文監視（参照箇所あり）
    - kill_switch.py          — Kill Switch（flag 書き込み）
    - alert_manager.py        — アラート送信（LINE 等、参照箇所あり）
  - execution/
    - execution_engine.py     — ExecutionEngine コア（発注セッション等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI 依存）
    - regime_detector.py      — 市場レジーム判定
  - data/                     — （実行時に DB / flag / pid / etc を置く想定）
  - logs/                     — ログ出力先（デフォルト）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

付記
----
- 本 README はコードベースの説明を目的としており、実運用の際は config/*.yaml（strategy / risk / execution 等）や運用手順書に従ってください。
- 本番環境 (KABUSYS_ENV=live) での起動前に必ず validate_config を実行して設定を確認してください。
- .env は機密情報を含むため、絶対にバージョン管理にコミットしないでください。

質問や補足を希望される点があれば教えてください（例: 実行例を具体的な環境で示す、主要クラスの API ドキュメントを追加、など）。