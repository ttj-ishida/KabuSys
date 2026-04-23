# KabuSys

日本株自動売買システムのライブラリ/スクリプト群（参考実装）。  
このリポジトリには実運用を想定した複数のコンポーネント（ExecutionEngine / Monitoring / Research / AI 等）が含まれます。

> 注意: 本リポジトリはサンプル実装を含みます。実資金で運用する場合は十分なレビューと試験を行ってください。

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 注文実行エンジン（ExecutionEngine） — ブローカークライアントと連携して発注を行う。
- 監視（Monitoring） — システム稼働状況・注文状態・リスクを定期チェックし、Kill Switch を発動可能。
- ポートフォリオ構築（Portfolio） — 候補選定、重み付け、ポジションサイズ算出等の純粋関数。
- リサーチ（Research） — DuckDB を用いたファクター計算・特徴量解析。
- AI 支援（AI） — ニュースの NLP スコアリングや市場レジーム判定（OpenAI API を使用）など。
- ユーティリティ群（logging / process priority / config） — 共通処理。

主要な起動スクリプト:
- monitoring（ポーリング監視）: src/kabusys/run_monitoring.py
- execution（実行エンジン）: src/kabusys/run_execution.py
- 設定ウィザード: src/kabusys/config_setup.py
- 設定検証: src/kabusys/validate_config.py
- ペーパートレード検証レポート: src/kabusys/tools/paper_verification_report.py

## 機能一覧

- SystemMonitor: CPU/メモリ/ディスク、プロセス生存チェック、データ鮮度チェック
- TradeMonitor: 発注ログの検査（滞留注文・価格異常など）
- RiskMonitor: ドローダウン監視・保有銘柄数上限監視、ダッシュボード更新
- KillSwitch: ドローダウンやポジション上限で停止フラグ（data/kill.flag）を書き込む
- MonitoringDB: SQLite に監視ログやトレードログを永続化
- ExecutionEngine: ブローカーとのやり取り、リスク管理、注文管理、再突合せ
- Paper trading モード: KABUSYS_ENV=paper_trading 時に MockBrokerClient を使用し、本番 DB と分離して data/paper_trading.db に記録
- Research: モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB 前提）
- AI: ニュース NLP（OpenAI）による銘柄センチメント、レジーム判定
- ロギング設定: 日次ローテーション + コンソール出力（logs/<app>.log）

## セットアップ手順

以下はローカルで動かすための概略手順です。

1. Python 環境を用意（推奨: 3.10+）
2. 必要パッケージをインストール
   - 主な依存: duckdb, psutil, openai, PyYAML（設定検証で必要）など  
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   実際の requirements.txt がある場合はそれを使用してください。

3. プロジェクトルートに .env を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env.example を参考に手動で作成してください。

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   警告も失敗扱いにする場合:
   ```
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリを確認（必要なら作成）
   - デフォルトの DB / フラグ等:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / flag: data/execution.pid, data/kill.flag, data/stop_requested.flag
   ログはデフォルトで logs/ 以下に書き出されます。

6. （OpenAI 機能を使う場合）OPENAI_API_KEY を環境変数または .env に設定

## 使い方

主要スクリプトと使い方の例を示します。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 監視ループ起動
  - デフォルトでは 60 秒間隔でポーリングします。環境変数で変更可能:
    - MONITOR_POLL_INTERVAL（秒、1 以上）
  ```
  python -m kabusys.run_monitoring
  ```
  - 備考:
    - Monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（監視用 SQLite）を使用します。
    - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します。

- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db（設定で上書き可）へ記録します（本番 DB と完全分離）。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - 実行中に stop flag を検知するとエンジンを停止します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / レジーム判定（プログラムから呼び出す）
  - OpenAI API キーが必要です（env OPENAI_API_KEY）。
  - ニュース NLP: kabusys.ai.score_news
  - レジーム判定: kabusys.ai.regime_detector.score_regime

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution 実行モード（development | paper_trading | live）。デフォルト: development
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB のパス（monitoring.db）。デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの発注充足モード（instant | partial | never | reject）。デフォルト: instant
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）、デフォルト INFO
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、既定 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（0/1。production では 0 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH: 各種ファイルパス（Settings 経由で取得）

（詳細は src/kabusys/config.py を参照してください）

## 停止・Kill Switch の扱い

- ExecutionEngine 停止のためのフラグ:
  - data/kill.flag — KillSwitch が書き込むファイル（ExecutionEngine 停止を意味する）
  - data/stop_requested.flag — run_* スクリプトが監視している「即時停止フラグ」
- KillSwitch は RiskMonitor の出力やその他条件に応じて kill.flag を書き込みます。起動時の KILL_FLAG_CLEAR_ON_START 設定に注意してください。

## ディレクトリ構成

（主要ファイルのみ。src/kabusys 以下を示します）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - config_setup.py           — .env 初期化ウィザード（CLI）
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py        — ロギング設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル作成・読み書き）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — （省略）トレード関連監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag の書き込み管理
    - monitoring_engine.py    — 複数モニタを束ねるエンジン
    - alert_manager.py        — （省略）通知管理
  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig 等）
    - order_manager.py        — 発注・状態管理
    - order_repository.py     — 注文永続化
    - broker_factory.py       — ブローカークライアント生成（Mock を含む）
    - reconciler.py           — 注文突合せ
    - risk_manager.py         — 実行時のリスク制御
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 発注株数決定・丸め
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン・IC 等の解析
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py      — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

※上記の一部ファイル（trade_monitor.py、alert_manager.py、execution の詳細等）はこの README の説明用に省略しています。ソースコードを直接参照してください。

## 開発・運用上の注意

- 本番運用では KABUSYS_ENV=live の設定が危険設定でないか十分に確認してください。
- .env は絶対にリポジトリへコミットしないでください（認証情報を含むため）。
- OpenAI API を利用する機能はコストとレイテンシが発生します。キーの管理・呼び出し頻度に注意してください。
- ペーパートレードモードを利用するときは PAPER_TRADING_SQLITE_PATH により本番 DB と切り離してください（run_execution は paper_trading の場合専用 DB を使用します）。
- ログは logs/<app>.log に日次ローテーションで出力されます。ログディレクトリのパーミッションに注意してください。

---

この README はコードベースから抽出した情報をまとめた概要です。各モジュールの詳細な挙動・パラメータはソースコードの docstring / コメントをご確認ください。ご不明点があれば、どの項目についてもう少し詳しく知りたいか指示してください。