# KabuSys

日本株自動売買システムのコンポーネント群（ライブラリ・起動スクリプト・運用ツール群）。

以下はリポジトリに含まれる主要機能、セットアップ方法、使い方、ディレクトリ構成の概要です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォーム向けユーティリティ群・ライブラリの集合です。主な責務は以下：

- 注文実行エンジン（ExecutionEngine）の起動補助スクリプト
- 監視ループ（Monitoring）の起動・監視ログ永続化
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量解析）
- AI を用いたニュースセンチメント・レジーム判定
- 運用用ユーティリティ（設定ウィザード、設定検証、レポート生成）

設計方針として、データ永続化は SQLite / DuckDB を利用し、Paper Trading（ペーパートレード）と本番 DB を分離して運用できるようになっています。

---

## 機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートに .env / .env.local がある場合）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 実行 / 監視
  - run_execution.py: ExecutionEngine 起動スクリプト（KABUSYS_ENV によって paper_trading モードを分離）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
  - Kill Switch 機構（data/kill.flag を書き込むことで ExecutionEngine に停止シグナル）
  - 停止フラグ（data/stop_requested.flag）でループを終了

- データベース / ロギング
  - monitoring_db: 監視ログ用 SQLite スキーマ初期化と CRUD
  - DuckDB を用いた分析 / リサーチ用データアクセス
  - 共通ログ設定ユーティリティ（TimedRotatingFileHandler + stdout）

- ポートフォリオ構築
  - 候補選定、等重／スコア重み付け、リスク調整（セクター上限）、ポジションサイズ計算（丸め、上限、aggregate cap）

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上で SQL 処理）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリ

- AI（OpenAI API）
  - ニュースを LLM（gpt-4o-mini 想定）でスコアリングして ai_scores に書き込み
  - マクロニュース + ETF (1321) MA200 に基づく市場レジーム判定

- 運用ツール
  - Paper Trading 検証レポート生成スクリプト: python -m kabusys.tools.paper_verification_report

---

## 前提（推奨）

- Python 3.10 以上（PEP 604 の型記法や型ヒントで | を使用）
- SQLite（標準ライブラリで可）
- インストール推奨パッケージ:
  - duckdb
  - psutil
  - openai
  - pyyaml（設定検証で YAML をパースする場合）
- ネットワーク接続（OpenAI を使う機能を利用する場合）

pip での例:
pip install duckdb psutil openai pyyaml

（requirements.txt があればそれを利用してください）

---

## セットアップ手順

1. リポジトリをクローン、作業ディレクトリへ移動。

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. .env の作成
   - 対話式ウィザード（推奨）:
     python -m kabusys.config_setup
     ウィザードは .env を生成します（.env は絶対に Git にコミットしないでください）。
   - または手動で .env を作成。主要項目（例）:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0

   - 自動読み込み: モジュール import 時にプロジェクトルートの .env / .env.local を自動ロードします。
     自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. データディレクトリ作成（通常はスクリプトが自動生成しますが、手動で準備しておくと安全です）
   - mkdir -p data logs

6. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 必須環境変数・DBパス・config/*.yaml の存在や YAML 構文を検証します。
   - --strict を指定すると警告も失敗（exit 1）として扱います。

---

## 環境変数（主要なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- データベース
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）

- Paper Trading 設定
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- ログ / モニタ
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LOG_DIR: ログ保存ディレクトリ（デフォルト logs）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

- OpenAI
  - OPENAI_API_KEY: AI 機能を使うために必要

- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

---

## 使い方（主要スクリプト）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録して本番 DB と分離します。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 停止は data/stop_requested.flag を作成するか、Execution 側の PID ファイルを参照して停止処理が行われます。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - 環境にかかわらず（KABUSYS_ENV に依らず）本番用 sqlite_path を使用して監視テーブルを初期化します。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で変更可能（デフォルト 60 秒）。
    - data/stop_requested.flag を検知するとループ終了。
    - Process 優先度を上げる等の初期化処理を行います。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD
    --to YYYY-MM-DD
    --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）
  - 出力: システム稼働率、注文成功率、送信率、レイテンシ等のサマリと PASS/FAIL 判定

- AI 関連（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を利用

---

## 運用上の注意

- .env は機密情報を含むため Git 管理しないでください（config_setup のヘッダにも明示）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します。validate_config がライブ環境向けのアラートを行います。
- Paper Trading は本番 DB と分離されるので、テスト時は KABUSYS_ENV=paper_trading を使用してください。
- run_monitoring は監視用 DB（SQLITE_PATH）を必ず使用します。monitoring は本番 DB を読む設計になっています（監視用テーブルは init_monitoring_db で作成・移行されます）。
- OpenAI API 呼び出しはネットワークエラーや 429/5xx を考慮してリトライロジックがありますが、API 利用時はコスト・レイテンシを考慮してください。

---

## ディレクトリ構成（要約）

以下はリポジトリ内の主要なモジュールと役割（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数管理、自動 .env ロード）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト

  - utils/
    - logging_setup.py : 統一ログ設定（stdout + 日次ローテーションファイル）
    - process_priority.py : プロセス優先度 / CPU affinity 設定ユーティリティ

  - monitoring/
    - monitoring_db.py : 監視用 SQLite スキーマ・永続化ロジック（init / CRUD）
    - system_monitor.py : システム状態・データ鮮度監視
    - trade_monitor.py : （注文関連の監視ロジック）
    - risk_monitor.py : ドローダウン・ポジション上限監視
    - kill_switch.py : kill.flag 書き込みロジック
    - monitoring_engine.py : 各モニタの束ね・アラート発行

  - execution/
    - order_manager, order_repository, reconciler, execution_engine, broker_factory, risk_manager 等
      （ExecutionEngine および注文管理に関連するコンポーネント群）

  - portfolio/
    - portfolio_builder.py : 候補選定・重み付け
    - position_sizing.py : 発注株数計算（丸め・上限・aggregate cap）
    - risk_adjustment.py : セクター上限・レジーム乗数

  - research/
    - factor_research.py : ファクター計算（Momentum/Volatility/Value）
    - feature_exploration.py : 将来リターン・IC・統計サマリ

  - ai/
    - news_nlp.py : ニュース NLP スコアリング（OpenAI 使用）
    - regime_detector.py : マクロ + ETF MA200 によるレジーム判定

  - tools/
    - paper_verification_report.py : Paper Trading 検証レポート生成スクリプト

  - data/ （ランタイムで使用）
    - kill.flag, stop_requested.flag, execution.pid, monitoring.db, paper_trading.db, kabusys.duckdb など

---

## 例: よく使うコマンドまとめ

- 仮想環境作成・依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai pyyaml

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動（開発モード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

---

この README はコードベースの主要ポイントをまとめたものです。より詳しい内部仕様（Engine の挙動、Execution の実装、Strategy の設計書等）は各モジュールの docstring や該当ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）を参照してください。必要なら README を拡張して起動例のログ断片やデバッグ手順、ユニットテスト実行手順なども追加します。