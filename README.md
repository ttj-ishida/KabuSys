# KabuSys

日本株自動売買システムのコードベース。ポートフォリオ構築、発注実行、監視、研究（ファクター計算）および AI を使ったニュースセンチメント評価等の機能を含みます。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動 / CLI）
- 環境変数（主要項目）
- 停止 / Kill Switch / フラグ
- ディレクトリ構成（主要ファイル説明）
- 依存ライブラリ（概要）
- 補足・運用上の注意

---

## プロジェクト概要

KabuSys は日本株自動売買（バックテスト／ペーパートレード／本番運用を想定）用のモジュール群です。以下の主要機能をコンポーネント単位で提供します。

- 発注実行エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- リスク管理（RiskManager）、約定整合性（Reconciler）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート・Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約等）
- 研究用モジュール（ファクター計算・Forward Return / IC 等）
- AI モジュール（OpenAI を用いたニュースの NLP スコアリング、レジーム判定）
- 運用ツール（設定ウィザード・設定検証、Paper Trading 検証レポート生成）

---

## 主な機能一覧

- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV によって paper_trading 時は MockBroker を使用し DB を分離）
- run_monitoring.py: SystemMonitor ポーリング（MONITOR_POLL_INTERVAL 環境変数で間隔変更可）
- config_setup.py: .env を対話式に作成・更新するウィザード
- validate_config.py: .env と config/*.yaml の検証 CLI（--strict で警告も失敗扱い）
- tools/paper_verification_report.py: Paper Trading の検証レポート出力
- monitoring パッケージ: system/trade/risk の監視ロジック、kill switch、alert manager 等
- portfolio パッケージ: 候補選定、重み算出、ポジションサイズ計算、セクター制約、レジーム乗数
- research パッケージ: ファクター計算（momentum/value/volatility）、特徴量解析、IC 計算
- ai パッケージ: ニュースセンチメント（OpenAI）およびレジーム判定（OpenAI）モジュール
- utils: ログ設定、プロセス優先度 / CPU affinity ユーティリティ等
- monitoring_db: SQLite による監視ログ / ダッシュボード / トレードログ永続化

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
   - 本 README はパッケージが `src/kabusys` 配下にあることを前提とします。

2. Python 環境の準備（推奨）
   - Python 3.10+ を推奨（コードは型注釈等を利用）
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 必要な主な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML の読み込み検証をする場合）
   - 例:
     - pip install duckdb psutil openai pyyaml
   - （requirements.txt がある場合はそれを使用してください）

4. 環境変数設定（.env）
   - 対話的に生成する:
     - python -m kabusys.config_setup
   - 生成後、検証:
     - python -m kabusys.validate_config
     - 警告も致命扱いにする場合: python -m kabusys.validate_config --strict

   自動ロード: package の config モジュールはプロジェクトルートに `.env` または `.env.local` があれば自動で読み込みます（OS 環境変数 > .env.local > .env）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方

基本的な起動方法とよく使うコマンド例。

- Execution（エンジン）起動
  - 本番 / 開発 / ペーパートレードの動作は KABUSYS_ENV に依存します。
  - 例（ペーパートレード）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - ペーパートレード時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離されます。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を短くしたい時:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（settings.sqlite_path）を使用します（設計上の注意点）。

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI モジュール（OpenAI を使用する機能）
  - OPENAI_API_KEY を環境変数に設定するか、関数/コマンドの引数で渡します。
  - 例:
    - export OPENAI_API_KEY="sk-..."
    - ai 機能を呼ぶコードを実行

ログ:
- デフォルトのログディレクトリは `logs/`。各アプリケーションは `logs/<app_name>.log`（日次ローテーション、30日保持）に出力されます。
- ログレベルは `LOG_LEVEL` 環境変数で変更可能（例: DEBUG/INFO/WARNING...）。

---

## 環境変数（主要項目）

（設定管理は `src/kabusys/config.py` の Settings クラスを参照）

- 必須（実行に必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用 / 動作切替
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

- DB パス
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視 DB（monitoring.db）デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（default data/paper_trading.db）

- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- ログ / PID / Kill
  - PID_FILE_PATH: デフォルト data/execution.pid
  - KILL_FLAG_PATH: デフォルト data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: 0/1（本番での自動クリアは危険）

- Monitoring
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

- OpenAI
  - OPENAI_API_KEY: OpenAI 呼び出しに使用

- その他
  - LOG_DIR: ログ出力ディレクトリを上書き（デフォルト logs/）

---

## 停止 / Kill Switch / フラグ

- 実行停止
  - run_execution / run_monitoring はプロセス内で `data/stop_requested.flag` を監視しています。停止させたい場合はこのフラグファイルを作成するとプロセスは正常に終了処理を行います。
  - run_execution は `data/execution.pid` を PID ファイルとして使用します。

- Kill Switch（強制停止・保護）
  - monitoring の評価結果が条件を満たすと `data/kill.flag` が書き込まれ、ExecutionEngine に停止要求を伝えます（Settings.kill_flag_path を参照）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

---

## ディレクトリ構成（主要ファイル説明）

（プロジェクトの `src/kabusys` を起点に抜粋）

- __init__.py
  - パッケージ基本情報（__version__ 等）

- config.py
  - 環境変数読み込み・Settings クラス

- config_setup.py
  - .env の対話生成ウィザード

- validate_config.py
  - 起動前設定検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（Main）

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（Main）

- execution/ (発注ロジック一式) — （コードベースに存在する想定モジュール）
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py など

- monitoring/
  - monitoring_db.py — SQLite テーブル作成 / 永続化 API
  - system_monitor.py — システム状況・データ鮮度監視
  - trade_monitor.py — トレード系の監視（滞留注文・約定異常）
  - risk_monitor.py — ドローダウンやポジション上限監視
  - kill_switch.py — kill.flag の作成 / 評価
  - monitoring_engine.py — 各 Monitor をまとめる

- portfolio/
  - portfolio_builder.py — 候補選定・スコア順ソート
  - position_sizing.py — 株数計算・aggregate cap
  - risk_adjustment.py — セクターキャップ / レジーム乗数

- research/
  - factor_research.py — momentum / value / volatility 等
  - feature_exploration.py — forward returns / IC / summary

- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector.py — ETF MA とマクロセンチメントを合成して regime を判定

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

- utils/
  - logging_setup.py — 統一的なロギング初期化（コンソール + 日次ローテートファイル）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/
  - 実行時に使用する DB / フラグ / pid 等（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/execution.pid）

- logs/
  - デフォルトログ出力先（例: logs/execution.log, logs/monitoring.log）

---

## 依存ライブラリ（概要）

- duckdb — 研究・時系列データの集計（prices_daily 等）に使用
- psutil — CPU/メモリ/ディスク使用率・プロセス制御に使用
- openai — ニュース NLP / レジーム検出で OpenAI API にアクセスするため
- PyYAML — validate_config の YAML 検証（任意だが推奨）
- sqlite3 — 標準ライブラリ（監視 DB 等）

インストール例:
- pip install duckdb psutil openai pyyaml

---

## 補足・運用上の注意

- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup.py でも警告があります）。
- run_monitoring はドキュメントにある通り、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（デフォルト 60 秒）。0 や負の値を入れると警告されデフォルトにフォールバックします。
- run_monitoring は監視用 DB（settings.sqlite_path）を常に使用します。run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使って本番 DB と分離します。
- AI 機能を利用する場合は OPENAI_API_KEY を適切に設定してください。API 呼び出しはリトライやフォールバックロジックを持ちますが、API キーやレート制限に注意してください。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合、コンソール出力のみで継続する設計になっています（ログディレクトリの権限等に注意）。

---

この README はコード内の docstring / 設計コメントに基づいて作成しています。より詳細な運用手順や設計ドキュメント（PortfolioConstruction.md や StrategyModel.md 等）が存在する場合はそちらも参照してください。必要であれば起動例や運用チェックリスト、systemd / supervisor 用のプロセスユニット例などの追加ドキュメントを作成します。必要なものがあれば教えてください。