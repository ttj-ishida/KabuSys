README
======

概要
----
KabuSys は日本株向けの自動売買/リサーチ基盤の骨格となる Python パッケージです。
このリポジトリには以下の主要機能を提供するモジュール群が含まれます:

- 実行エンジン（ExecutionEngine）の起動スクリプト（実売買 / ペーパートレード対応）
- 監視デーモン（System / Trade / Risk のポーリング）と Kill Switch
- ポートフォリオ構築・ポジションサイズ計算の純粋関数群
- DuckDB を使ったファクター計算・リサーチモジュール
- ニュース NLP（OpenAI）を用いたセンチメントスコアリング、レジーム判定
- 設定ウィザード (.env 作成) と設定検証 CLI
- ペーパートレードの検証レポート生成ツール

主な特徴
--------
- 環境分離: KABUSYS_ENV による実行モード切替（development / paper_trading / live）
- ペーパートレードは本番 DB と完全分離（data/paper_trading.db）
- DuckDB を用いた高速な時系列ファクター計算（prices_daily / raw_financials 参照）
- OpenAI (gpt-4o-mini 想定) を使ったニュースセンチメント・市場レジーム判定（任意）
- ログは stdout と日次ローテーションファイル（logs/<app>.log）へ出力
- シンプルなファイルフラグによる外部停止（data/stop_requested.flag / data/kill.flag）

前提
----
- Python 3.10+
- 必要なパッケージ（最小例）
  - duckdb
  - psutil
  - openai (NLP / regime 機能を使う場合)
  - pyyaml (config 検証で YAML をチェックする場合)
- 推奨: 仮想環境（venv/conda）を利用すること

セットアップ手順
----------------
1. リポジトリをクローン／展開

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai pyyaml

   ※ requirements.txt がある場合は pip install -r requirements.txt を使用してください。

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - もしくは手動で .env を作成（.env.example を参照）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）:
     - python -m kabusys.validate_config --strict

6. データディレクトリの確認/作成
   - デフォルトでは data/ に SQLite / pid / フラグファイルが置かれます。権限や配置を確認してください。

主要環境変数（主なもの）
-----------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

通常（よく使う／設定例）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）※ monitoring は常に本番 sqlite_path を使用
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレード挙動）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使う機能で使用
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / 各種閾値（CPU/MEM/DISK）: 詳細は Settings クラス参照

使い方（起動・ユーティリティ）
------------------------------

1) 設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

2) 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

3) 監視デーモン起動（SystemMonitor のポーリング）
   - python -m kabusys.run_monitoring
   - 環境変数でポーリング間隔を上書き可能:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視プロセスは data/stop_requested.flag を検知すると終了します（監視側の停止フラグ）。

   備考:
   - run_monitoring は Settings.sqlite_path（本番用 monitoring DB）を使います（KABUSYS_ENV に依らず本番 DB を想定）。

4) 実行エンジン起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、data/paper_trading.db に記録されます（本番 DB と分離）。
   - 実行中に data/stop_requested.flag を作成するとエンジン停止をトリガーします。
   - 実行時は data/execution.pid に PID を書きます。

5) ペーパートレード検証レポート（ツール）
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パス指定:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

6) AI / ニューススコアリング（モジュール API）
   - kabusys.ai.score_news を直接呼ぶことができます（DuckDB 接続と target_date を渡す）。
   - OPENAI_API_KEY を環境変数で設定するか、api_key 引数で明示的に渡してください。

停止・Kill Switch
-----------------
- 外部から監視スクリプトやエンジンを停止するにはプロジェクトルートの data/stop_requested.flag を作成します（run_monitoring/run_execution はこれを監視）。
- システム側からの自動停止条件（ドローダウン超過等）を検知すると data/kill.flag が作成されます。kill.flag があると ExecutionEngine は起動を拒否する挙動を持ちます。
- kill.flag の自動クリアを許可するかは KILL_FLAG_CLEAR_ON_START により制御できます（本番では 0 を推奨）。

ログ
----
- 標準出力（stdout）とファイル（logs/<app_name>.log、日次ローテート）に出ます。
- ログディレクトリは LOG_DIR 環境変数または logs/（デフォルト）。
- 既存のハンドラは setup_logging() 内でクリアされるため、複数回初期化しても二重出力になりにくい設計です。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理（Settings クラス）
- config_setup.py          — .env 対話式ウィザード（python -m kabusys.config_setup）
- validate_config.py       — 起動前検証 CLI（python -m kabusys.validate_config）
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト（ペーパートレード分離）
- tools/
  - paper_verification_report.py — ペーパートレードの検証レポート生成ツール
- utils/
  - logging_setup.py        — 共通ログ設定ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
- monitoring/
  - monitoring_db.py        — SQLite 監視ログ永続化層（テーブル初期化・CRUD）
  - system_monitor.py       — システム状態 / データ鮮度監視
  - trade_monitor.py        — （注文監視）※コードベース内に参照あり
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - kill_switch.py          — kill.flag の書き込みロジック
  - alert_manager.py        —（通知管理）※実装参照
- execution/
  - execution_engine.py     — ExecutionEngine 本体（起動は run_execution.py 経由）
  - broker_factory.py       — BrokerClient の生成
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行関連モジュール
- portfolio/
  - portfolio_builder.py    — 候補選定・重み計算
  - position_sizing.py      — 発注株数計算、リスク制限、単元丸め
  - risk_adjustment.py      — セクターキャップ・レジーム乗数
- research/
  - factor_research.py      — ファクター計算（momentum/value/volatility）
  - feature_exploration.py  — 将来リターン・IC 計算など
- ai/
  - news_nlp.py             — raw_news を OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py      — 市場レジーム判定（ETF MA + マクロセンチメント）
- data/                     — デフォルトの DB / PID / フラグファイルが置かれる想定（実行時に自動作成されることが多い）

注記・運用上のポイント
---------------------
- データ鮮度確認やポートフォリオのハイウォーターマーク等は MonitoringDB（SQLite）で管理されます。運用時は監視 DB のバックアップやアクセス権に注意してください。
- OpenAI API を用いる箇所は外部 API の故障に対してフェイルセーフ設計（失敗時は 0.0 フォールバック等）になっていますが、API キー漏洩に注意してください。
- .env は機密情報を含むため決して Git にコミットしないでください（config_setup のヘッダにも注意書きあり）。
- 本番稼働（KABUSYS_ENV=live）の際は特に KILL_FLAG_CLEAR_ON_START を 0 にし、LINE 通知等のアラート先設定を必ず整備してください。

貢献・拡張
----------
- 追加の BrokerClient 実装、戦略モデル、通知先（LINE / Slack）のプラグインを追加することで拡張できます。
- DuckDB に格納する prices_daily/raw_financials のスキーマやデータロードパイプラインは data.pipeline 周りを参照してください。

ライセンス
----------
このリポジトリに付属するライセンス情報に従ってください（本 README にはライセンス条項は含まれていません）。

以上。README に含めたい追加項目（例: 実際の起動オプション、より詳細な依存関係リスト、テスト方法など）があれば教えてください。