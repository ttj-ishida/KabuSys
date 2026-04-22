# KabuSys

日本株自動売買システムのコアライブラリ群（軽量な実行エンジン / 監視 / リサーチ / AI支援モジュール群）。

以下はコードベースから抽出した README です。実行スクリプトや各モジュールの役割、セットアップ・起動方法を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムを構成するモジュール群です。主な機能は次の通りです。

- ExecutionEngine：発注・注文管理・リスク管理を統合した実行エンジン
- Monitoring：システム状態・注文状態・リスクを定期監視しアラート / Kill Switch を管理
- Portfolio construction：候補選定・重み付け・ポジションサイズ算出・セクター制限などの純粋関数
- Research：DuckDB 上の時系列データからファクター計算・特徴量解析を行う
- AIモジュール：OpenAI を用いたニュースセンチメント評価やレジーム判定
- ユーティリティ：設定読み込み、ログ設定、プロセス優先度調整など

設計方針として、DB（SQLite / DuckDB）や外部 API の扱いは明確に分離され、テストしやすい純粋関数と永続化レイヤに分かれています。

---

## 機能一覧（主要）

- 環境設定ウィザード（config_setup.py）で .env の雛形を対話的に作成
- 設定検証ツール（validate_config.py）で .env と config/*.yaml の事前チェック
- Execution 起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading（MockBroker）と live（実ブローカー）を切替
  - paper_trading 時は専用 SQLite (data/paper_trading.db) を使用して本番 DB と分離
- Monitoring 起動スクリプト（run_monitoring.py）
  - 定期ポーリングで system / trade / risk の各監視を実行
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）
  - 監視は本番用 sqlite_path を常に使用（注：監視 DB は環境に依存せず本番パスを見に行きます）
- MonitoringDB：監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）を SQLite に永続化
- Risk Monitor：ドローダウン・ポジション上限の監視とリスクログ記録
- Kill Switch：条件に応じて data/kill.flag を書き込み、ExecutionEngine 停止シグナルを送出
- Tools：
  - paper_verification_report：Paper Trading DB から検証レポート（稼働率、成功率、レイテンシ等）を生成
- Research：
  - ファクター計算（momentum, volatility, value）
  - 将来リターン / IC 計算 / 統計サマリー
- AI：
  - news_nlp.score_news：OpenAI を用いたニュースセンチメントのバッチスコアリング（ai_scores へ書込）
  - regime_detector.score_regime：MA とマクロセンチメントを合成して市場レジーム判定（market_regime へ書込）
- Utilities：
  - ログ設定（logs/<app>.log、日次ローテート）
  - プロセス優先度・CPU affinity 設定（psutil ベース）

---

## 動作環境・依存

- Python 3.10+（型アノテーションの union 表記などを利用）
- 必須 Python パッケージ（少なくとも以下をインストールしてください）:
  - duckdb
  - psutil
  - openai
- 任意:
  - PyYAML（validate_config で config/*.yaml を検証する場合）
- DB:
  - SQLite（組み込み）
  - DuckDB（分析用）

（プロジェクトに requirements.txt があればそちらを使ってください）

---

## セットアップ手順（例）

1. リポジトリを取得
   - git clone ...（省略）

2. 仮想環境の作成と依存インストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install --upgrade pip
   - pip install duckdb psutil openai
   - （必要であれば）pip install pyyaml

3. 環境変数の作成
   - 対話式ウィザードで .env を作成：
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使うなら:
     - OPENAI_API_KEY（score_news / score_regime 実行時に指定も可）

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

5. ディレクトリ準備（.env のデフォルトで data/ や logs/ が使われます）
   - data/ ディレクトリを作成するか、起動時に自動作成されます。
   - logs/ は setup_logging により自動で作成されます（作成失敗時はコンソールのみで継続）。

---

## 使い方（起動コマンド・主要スクリプト）

- ExecutionEngine を起動する
  - python -m kabusys.run_execution
  - 動作環境 KABUSYS_ENV:
    - paper_trading: MockBroker を使用し data/paper_trading.db を使用（本番 DB と分離）
    - live: 実ブローカーを使用（KABU_API_PASSWORD 等の設定が必要）
  - 起動時に data/stop_requested.flag が既に存在すると起動を行わず終了します。
  - 実行中、data/stop_requested.flag を作成すると安全に停止させる仕組みがあります（run_execution はフラグ検出で engine.stop() を呼びます）。
  - PID ファイル: data/execution.pid（Settings.pid_file_path）

- Monitoring を起動する
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に関係なく本番パスを使用する設計）。
  - 停止は data/stop_requested.flag を作成することで監視ループが終了します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code=1）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD（開始日）
    - --to YYYY-MM-DD（終了日）
    - --db PATH（PAPER_TRADING_SQLITE_PATH の代替）
  - デフォルト DB: data/paper_trading.db

- Python API として呼び出す（例）
  - 簡単な例（AI スコアリング）:
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, datetime.date(2026,4,1), api_key="...")

  - ポートフォリオ関数の使用:
    from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

---

## 主な環境変数（抜粋とデフォルト）

- 必須:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)

- 選択 / デフォルト:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO（DEBUG / INFO / WARNING / ERROR / CRITICAL）
  - LOG_DIR: logs/
  - OPENAI_API_KEY: OpenAI を利用する場合に必要（score_news / score_regime）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）（デフォルト: 60）
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: 0|1 （本番で 1 は危険）

注意: config_setup ウィザードで .env を作成できます。validate_config による検証を推奨します。

---

## 停止・Kill スイッチの動作

- data/stop_requested.flag
  - run_monitoring / run_execution の両方が監視している停止用フラグ。
  - ファイルが検出されると安全にループを抜けてプロセスを終了します。

- data/kill.flag
  - Monitoring 側の KillSwitch で書き込まれるファイル。ExecutionEngine に対する停止要求を示す（Execution は kill.flag の存在を検出して停止動作をとる設計）。
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）。

---

## ロギング

- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます（30日保持）。
- コンソールは stdout に出力されます（cron 等で出力をリダイレクトすることを想定）。
- setup_logging(app_name="execution" など) で統一的に設定されます。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — Settings クラス、.env 自動読み込みロジック
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - execution/              — 実行エンジン関連（broker_factory, execution_engine, order_manager 等）
  - monitoring/
    - monitoring_db.py      — SQLite 永続化 API（system_status, trade_logs 等）
    - system_monitor.py     — システム状態 / データ鮮度監視
    - trade_monitor.py      — 注文滞留・約定異常監視（コード内にあり）
    - risk_monitor.py       — ドローダウン・ポジション上限チェック
    - kill_switch.py        — kill.flag 書込みロジック
    - monitoring_engine.py  — 各 Monitor を束ねるループ
    - alert_manager.py      —（アラート送信のラッパー。LINE 等に送る実装を期待）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py           — ニュースのセンチメントスコアバッチ処理（OpenAI）
    - regime_detector.py    — MA と LLM を組み合わせたレジーム判定
  - tools/
    - paper_verification_report.py  — Paper Trading の検証レポート生成

（上記は主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## 開発メモ / 注意点

- Settings は .env 自動読み込みを行いますが、テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring の起動スクリプトは「監視 DB」を本番 sqlite_path で扱う点に注意（run_monitoring の docstring/実装参照）。
- ExecutionEngine は paper_trading 時に専用 DB を使い、本番 DB と分離する設計です。
- OpenAI を利用する機能は API 呼び出しの失敗に対してフェイルセーフを備えており、リトライやロギングを行いますが、API キーは必ず適切に管理してください。
- Python バージョンは 3.10 以上を推奨（型表記・構文の都合）。

---

必要に応じて、この README をプロジェクトの README.md として保存し、実際の環境（requirements.txt、起動手順、デプロイ方法）に合わせてチューニングしてください。README の補足や特定のコマンド例（systemd unit / docker-compose など）を追加したい場合は指示をください。