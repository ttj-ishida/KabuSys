# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・研究ツールを含む自動売買基盤の一部実装です。Python モジュール群として設計されており、スクリプト単位で起動して運用できます。

---

## 概要

- ポートフォリオ構築（候補選定・重み付け・株数算出）
- 発注実行エンジン（本番 / ペーパートレード切替、リスク管理、オーダー管理）
- 監視（システム状態、注文ログ、リスク監視、Kill Switch）
- 研究（ファクター計算・特徴量探索）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話式作成）: python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml のチェック）: python -m kabusys.validate_config
- 実行エンジン起動スクリプト（ExecutionEngine）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し data/paper_trading.db に記録
- 監視ループ起動スクリプト（SystemMonitor）: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）
  - 注意: Monitoring は KABUSYS_ENV に関わらず 本番 sqlite_path を使用
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- ニュース NLP（OpenAI を使用して銘柄ごとのセンチメント算出）
- 市場レジーム判定（ETF + マクロニュースを組み合わせる）
- DuckDB（分析用） / SQLite（監視・注文ログ用）への永続化操作ユーティリティ
- ロギング統一化（stdout + 日次ローテーションファイル出力）
- プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 必要要件（主な依存パッケージ）

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の内容検証を行う場合）
- （その他、プロジェクトで必要な依存がある場合は requirements.txt を参照）

インストール例:
- 仮想環境を作成して pip でインストール:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -U pip
  - pip install duckdb psutil openai pyyaml

（本リポジトリに requirements.txt があればそれを使用してください）

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン / 配布パッケージを展開
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数設定
   - 推奨: 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主な環境変数（代表）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb（分析 DB）
     - SQLITE_PATH: data/monitoring.db（監視用 SQLite）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード専用 DB）
     - LOG_LEVEL, LOG_DIR
     - OPENAI_API_KEY（AI 機能を使用する場合）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）
     - PAPER_FILL_MODE（ペーパートレードの約定挙動: instant|partial|never|reject）
4. 設定検証（推奨）:
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで終了コード 1 を返す
5. data ディレクトリ等が必要な場合は作成されます（logs/ はログ生成時に自動作成されます）

---

## 使い方（起動例）

- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 仕様:
    - デフォルトポーリング 60 秒
    - 停止はプロジェクトルートの data/stop_requested.flag を作成することで検知して終了
    - 監視は常に settings.sqlite_path（監視 DB）を使用

- 実行エンジン起動:
  - KABUSYS_ENV=development python -m kabusys.run_execution
  - ペーパートレード:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - この場合、MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
  - 実行中の停止:
    - プロジェクトルートの data/stop_requested.flag を作成するとエンジンが停止処理を行う
  - 実行エンジンは data/execution.pid を作成します（PID 管理）

- .env ウィザード:
  - python -m kabusys.config_setup
  - 既存 .env を読み込み、対話的に更新可能

- 設定検証:
  - python -m kabusys.validate_config
  - config/*.yaml の存在やパースもチェック（PyYAML が必要）

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH による指定も可

---

## 運用上のファイル（data/ 下）

- data/stop_requested.flag
  - run_monitoring / run_execution が監視している停止フラグ（存在で停止）
- data/kill.flag
  - KillSwitch が書き込む停止トリガ（ExecutionEngine を停止させるためのシグナル）
- data/execution.pid
  - run_execution が作成する PID ファイル（Engine の起動管理）
- デフォルト DB ファイル
  - data/monitoring.db（SQLite: 監視・ログ）
  - data/paper_trading.db（ペーパートレード用 SQLite）
  - data/kabusys.duckdb（DuckDB: 研究/分析用）

注意:
- Monitoring は設定に関わらず sqlite_path（通常 data/monitoring.db）を使用します。実運用ではファイルパスに注意してください。
- KillSwitch は条件（ドローダウン超過・ポジション上限超過など）で data/kill.flag を作成します。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番では 0 を推奨します。

---

## ログ

- ロギングは共通ユーティリティで設定されます（kabusys.utils.logging_setup.setup_logging）
- 出力先:
  - コンソール（stdout）
  - 日次ローテーションファイル: logs/<app_name>.log（デフォルト logs/ ディレクトリ）
- ログレベルは環境変数 LOG_LEVEL または引数で指定可能（デフォルト INFO）
- ファイルハンドラは logs/ ディレクトリ作成に失敗した場合は自動で無効化され、コンソールのみの出力になります

---

## 主要モジュールの説明（抜粋）

- kabusys.config
  - .env の自動読み込み（.env, .env.local）、Settings クラスで環境変数をラップ
- kabusys.config_setup
  - .env を対話式に生成 / 更新するウィザード
- kabusys.validate_config
  - 必須環境変数やファイルの検証ツール
- kabusys.run_execution
  - ExecutionEngine の起動スクリプト（本番 / ペーパートレード切替）
- kabusys.run_monitoring
  - SystemMonitor のポーリングループ起動スクリプト
- kabusys.monitoring.*
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db など監視関連実装
- kabusys.portfolio.*
  - ポートフォリオ構築（候補選定、重み算出、株数算出、セクター上限、レジーム乗数）
- kabusys.research.*
  - ファクター計算（momentum, volatility, value）、特徴量探索、IC 計算
- kabusys.ai.*
  - news_nlp: OpenAI を使った銘柄ニュースのセンチメント評価
  - regime_detector: ETF とマクロニュースを使った市場レジーム判定
- kabusys.tools.paper_verification_report
  - ペーパートレード結果を集計して Pass/Fail 判定するレポート生成

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_monitoring.py
    - run_execution.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - data/
      - pipeline.py
      - stats.py
    - tools/
      - paper_verification_report.py

---

## 環境変数（代表的なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db） — Monitoring が使用
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- OPENAI_API_KEY（AI 機能）
- LOG_LEVEL（INFO / DEBUG など）
- LOG_DIR（ログ保存先ディレクトリ）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、デフォルト 60）
- PAPER_FILL_MODE（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を消すか、1=消す、0=消さない）

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では設定とシークレットの管理に注意してください。validate_config は本番向けの追加警告チェックを行います。
- Monitoring は監視 DB を使ってシステムの稼働率やトレードログを保存します。DB のパスは .env で適切に管理してください。
- Kill Switch と stop フラグ（data/kill.flag, data/stop_requested.flag）によりプロセス停止を行います。運用手順を整備してください。
- OpenAI を使う処理は API 呼出に失敗した場合もフェイルセーフに動作するよう設計されていますが、API キー・コスト・レート制限管理は運用者側で行ってください。
- ロギングや DB のファイル作成権限に注意。ログディレクトリや data/ ディレクトリには実行ユーザーが書き込みできる必要があります。

---

## よく使うコマンドまとめ

- .env 作成/更新:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- 研究 / 分析はモジュールをインポートして利用:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, ...

---

もし README に追加してほしい内容（例: systemd サービス定義例、Dockerfile、詳しい設定ファイル仕様、API のドキュメントなど）があれば教えてください。必要に応じてセクションを追記します。