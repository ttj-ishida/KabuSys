# KabuSys — 日本株自動売買システム

このリポジトリは、日本株の自動売買（Execution）および運用監視（Monitoring）、リサーチ（Research）、AI支援（ニュースNL P / レジーム判定）などのコンポーネントを含むプロジェクトです。  
以下はコードベースに基づいた README（日本語）です。

注意: 実行前に必ず .env を作成し、必須の環境変数を設定してください（wizard と検証ツールを用意しています）。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムの骨格実装です。主な機能群は以下の通りです。

- ExecutionEngine（発注エンジン）: ブローカークライアント経由で発注を行う。KABUSYS_ENV により paper_trading（MockBroker）を利用可能。
- Monitoring（監視）: システム状態、注文の滞留・約定異常、ドローダウンなどを定期チェックしログ（SQLite）に保存。必要に応じて Kill Switch を発動。
- Portfolio / Position Sizing: 候補選定、重み付け、株数計算（単元丸め、リスク制約）。
- Research: DuckDB を使ったファクター計算（Momentum / Volatility / Value 等）や特徴量評価。
- AI モジュール: OpenAI を使ったニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）。
- ユーティリティ: 環境設定ウィザード、設定検証ツール、Paper Trading 検証レポート生成など。

---

## 機能一覧（要点）

- 環境設定ウィザード（.env の作成 / 更新）
  - python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml のチェック）
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード対応）
  - python -m kabusys.run_execution
- Monitoring 起動スクリプト（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` で間隔上書き（デフォルト 60 秒）
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- DuckDB を利用したリサーチ関数群（ファクター計算 / forward returns / IC 等）
- OpenAI を使ったニュースのセンチメントスコアリング・レジーム判定（要 OPENAI_API_KEY）
- Process priority / CPU affinity 設定ユーティリティ（psutil ベース）
- 監視用 SQLite DB（monitoring_db）管理クラス（テーブル作成・マイグレーション含む）

---

## セットアップ手順

1. Python 環境の準備
   - 推奨: Python 3.10+ を使用してください。
   - 仮想環境を作成・有効化（例）
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - 最低限必要な外部パッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config が YAML 検証を行う場合に任意）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクト配布パッケージがある場合は pip install -e . を利用してください。）

3. .env の作成
   - ウィザードを利用する:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY: OpenAI を使う場合に設定
     - LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, 等

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります。

5. データディレクトリの用意
   - デフォルト DB 等は `data/` 以下を参照します。自動作成されることが多いですが権限を確認してください。

---

## 使い方（実行例）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（実行プロセス）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは `data/paper_trading.db` に記録されます（本番 DB と分離）。
  - 停止方法:
    - プロセスが起動中に `data/stop_requested.flag` を作成すると停止処理が行われます。
    - Kill Switch（監視側がトリガーして書き込む `data/kill.flag`）により ExecutionEngine が停止される設計です。
    - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアします（本番では推奨しません）。

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30  # 秒
  - Monitoring は環境に関係なく `Settings.sqlite_path`（デフォルト: data/monitoring.db）を使用します（run_monitoring の仕様）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: PAPER_TRADING_SQLITE_PATH 環境変数 または data/paper_trading.db を参照
  - 出力は標準出力に整形されたサマリと PASS/FAIL 判定を行います。

- AI 機能（ニュース / レジーム）
  - OPENAI_API_KEY を設定してください（.env に記載可）。
  - kabusys.ai.news_nlp.score_news / kabusys.ai.regime_detector.score_regime を呼び出して DuckDB 上のテーブルを操作します。
  - 注意: OpenAI API 呼び出しは課金が発生します。失敗時はフェイルセーフ（多くの場面で 0.0 を採用）になっていますが、API キー未設定時は例外が出ます。

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 重要な設定
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
  - OPENAI_API_KEY: OpenAI を使う場合に必須
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0|1）

---

## 停止 / Kill Switch / フラグファイル

- stop_requested.flag
  - run_execution / run_monitoring がチェックする「停止要求」フラグ。ファイルが存在するとループを抜けて終了します。
  - パス: project_root/data/stop_requested.flag（スクリプトが想定する位置）

- kill.flag
  - Monitoring 側の KillSwitch が条件を満たした場合に書き込まれるファイル。ExecutionEngine はこれを検知して停止します。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 により起動時に自動でクリア可能（本番では推奨しない設定）

---

## ディレクトリ構成（主なファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 読み込みロジックおよび Settings クラス
  - config_setup.py
    - .env の対話式ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine の起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py (psutil を使った優先度 / CPU affinity 設定)
  - execution/  (発注関連コンポーネント)
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
  - monitoring/
    - monitoring_db.py (SQLite テーブル作成・永続化層)
    - monitoring_engine.py (各 Monitor を束ねるループ)
    - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, alert_manager.py
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - research/
    - factor_research.py, feature_exploration.py
  - ai/
    - news_nlp.py, regime_detector.py
  - tools/
    - paper_verification_report.py
  - data/（ランタイムで使用）
    - monitoring/ orders/ 等の DB ファイル（デフォルトは data/*.db）
    - stop_requested.flag, kill.flag, execution.pid など

---

## 注意事項 / 運用上のヒント

- DB 分離
  - paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 monitoring.db とデータを分離します。運用時に誤って本番 DB を上書きしないよう注意してください。

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロードします。テスト等で自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI
  - news_nlp / regime_detector は OpenAI API を呼びます。API 利用料が発生するため、テスト時はモック化するかキー提供に注意してください。API 呼び出し失敗時のリトライやフェイルセーフ処理は実装されています。

- ログレベル
  - LOG_LEVEL を設定してログ出力量を制御できます。デフォルト INFO。

- 権限
  - process priority の設定は psutil を介して行いますが、プラットフォームや権限によって設定できない場合があります（警告ログが出ます）。

---

## よく使うコマンドまとめ

- .env を対話式で作る:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README にサンプル .env のテンプレート、systemd サービスユニットや Docker 実行例、より詳細なディレクトリツリー/各モジュールの API ドキュメントを追加できます。どの追加情報がほしいか教えてください。