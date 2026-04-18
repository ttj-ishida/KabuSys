# KabuSys — 日本株自動売買システム（README）

本リポジトリは日本株向けの自動売買フレームワークのコア部分を含むモジュール群です。
この README ではプロジェクト概要、主な機能、セットアップ手順、使い方（起動コマンドや環境変数）、ディレクトリ構成を日本語でまとめます。

重要: 本 README はリポジトリ内のソース（src/kabusys/**/*.py）に基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。主な役割は以下です。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定、重み付け、単元丸め）
- 発注エンジン（ExecutionEngine）とブローカークライアント抽象化（本番 / ペーパートレード切替）
- 監視サブシステム（System/Trade/Risk モニタ、Kill Switch、アラート）
- AI モジュール（ニュースセンチメント、レジーム判定） — OpenAI API を利用
- 各種ツール（ペーパートレード検証レポート等）
- 設定ウィザード・検証ユーティリティ（.env の生成、設定検証）

設計方針として、できるだけ副作用を小さくし DB や外部 API へのアクセスを明示的に行うようにしています（例: DuckDB 接続を関数引数で受け取る等）。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（.env / .env.local）および Settings クラス（環境変数検証）
  - 対話式設定ウィザード: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`

- 実行コンポーネント
  - ExecutionEngine（発注ロジック、リスク管理、OrderManager 等）
  - BrokerClientFactory による本番 / モック（ペーパートレード）クライアント切替

- 監視コンポーネント
  - SystemMonitor: CPU/MEM/DISK・データ鮮度・プロセス存否の監視
  - TradeMonitor: 発注ログ監視（滞留注文、約定異常など）
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 監視結果に基づく停止フラグ（data/kill.flag）発行
  - MonitoringEngine: 各監視を束ねてポーリング

- ポートフォリオ構築
  - 候補選定（score/rank ベース）
  - 重み計算（等分・スコア重み）
  - ポジションサイズ計算（リスクベース、上限、単元丸め）
  - セクターキャップ適用、レジーム乗数

- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（OpenAI）
  - ニュースセンチメントスコアリング（ai.news_nlp.score_news）
  - マーケットレジーム判定（ai.regime_detector.score_regime）

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## システム要件 / 依存ライブラリ

- Python 3.10+
  - 型記法（|）や標準ライブラリ機能に依存しています。
- 推奨インストール（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証を使う場合）
- インストール例:
  - pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がある場合はそれを使ってください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを準備

2. Python 環境を作成・有効化（例: venv）

3. 依存関係をインストール
   - pip install duckdb psutil openai PyYAML

4. 対話式で .env を作成（推奨）
   - python -m kabusys.config_setup
   - 画面の指示に従い JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD などを入力してください。
   - 生成された .env は Git 管理対象に入れないでください（README / .gitignore を参照）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります（exit code 1）。

6. データディレクトリの確認
   - デフォルト DB /ファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading DB: data/paper_trading.db
     - ログ: logs/<app_name>.log
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を設定

---

## 主要な環境変数（主なものとデフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (デフォルト: development)
  - 有効値: development, paper_trading, live
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- LOG_LEVEL (デフォルト: INFO)
- LOG_DIR (デフォルト: logs/)
- OPENAI_API_KEY (AI モジュール利用時に必要)
- PAPER_FILL_MODE (ペーパートレード時のフィルモード。instant/partial/never/reject)
- MONITOR_POLL_INTERVAL (監視ループのポーリング間隔秒、デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (0/1。起動時に kill.flag を自動クリアするか)

---

## 使い方（起動 / コマンド）

各スクリプトはモジュールとして実行できます（プロジェクトルートから）。

- 設定ウィザード（.env を生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 監視プロセス起動（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します。
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループを終了します。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB とは分離）。
  - 起動前に data/stop_requested.flag が存在する場合、エンジンは起動せず終了します。
  - 実行中は PID ファイル（data/execution.pid）を作成します。停止は stop flag/kill flag により制御されます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- AI モジュール（スクリプトではなくライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OpenAI API キーは引数または OPENAI_API_KEY 環境変数で指定

ログ:
- 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` により
  - stdout（コンソール）出力（StreamHandler）
  - 日次ローテートファイル（logs/<app_name>.log、30日保持）
  の両方にログ出力します。

監視による強制停止:
- Kill Switch がトリガーされると data/kill.flag が書かれ、ExecutionEngine に停止を促します（起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアしますが、本番では 0 を推奨します）。

プロセス優先度:
- 起動スクリプトは最初に set_process_priority("high") を試みます。プラットフォームや権限によっては無視される場合があります。

---

## ディレクトリ構成（主要ファイル説明）

プロジェクトの重要なファイル群を抜粋して示します（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数の取得・検証、自動 .env 読み込みロジック
  - config_setup.py
    - 対話式 .env 生成ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV による本番 / paper_trading 切替）
  - monitoring/
    - monitoring_db.py
      - SQLite を用いた監視ログ永続化（テーブル作成・Migration・CRUD ラッパー）
    - system_monitor.py
      - CPU/MEM/DISK・プロセス・データ鮮度監視
    - trade_monitor.py
      - （ソース内に存在）発注ログ監視（滞留注文・価格異常など）
    - risk_monitor.py
      - ドローダウン・ポジション上限監視（Kill Switch と連携）
    - kill_switch.py
      - data/kill.flag 書き込み・クリア
    - monitoring_engine.py
      - 上記 Monitor を束ねるエンジン（ポーリング）
    - alert_manager.py
      - （アラート送信ロジック）
  - execution/
    - execution_engine.py
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
    - news_nlp.py
      - ニュースを OpenAI でスコアリングし ai_scores テーブルへ書き込み
    - regime_detector.py
      - ETF MA とマクロニュースの LLM スコアを合成してレジーム判定
  - tools/
    - paper_verification_report.py
      - Paper Trading のパフォーマンス/健全性を検証するレポート生成
  - utils/
    - logging_setup.py
      - ログ設定ユーティリティ
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定
  - data/ (実行時に生成される想定)
    - monitoring.db (SQLite)
    - paper_trading.db (ペーパートレード用 SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - config/ (テンプレート/生成される設定ファイル)
    - system_config.yaml, data_config.yaml, ... （validate_config で存在確認・パース検証）

（注）上記はソースの抜粋です。細かいモジュールは該当ディレクトリを参照してください。

---

## 運用上の注意 / ヒント

- KABUSYS_ENV=live を設定する場合は十分に設定を確認してください。validate_config は live 環境時に追加の注意喚起を行います。
- ペーパートレード時は本番 DB と完全分離されるため、PAPER_TRADING_SQLITE_PATH の設定を確認してください。
- OpenAI API を使うモジュール（news_nlp / regime_detector）は API の利用制限や費用に注意してください。失敗時はフェイルセーフでゼロスコア等にフォールバックする設計ですが、頻繁な呼び出しはコストになります。
- ログディレクトリ作成に失敗すると stdout のみの出力になります（warning が出ます）。
- process_priority や CPU affinity の設定は OS 権限が必要な場合があります（AccessDenied に注意）。

---

## 例: よくある起動フロー（ローカル開発）

1. .env を作成
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config

3. DuckDB/SQLite データがない場合は初期化（必要なスクリプトがあれば実行）

4. 監視プロセス起動（別ターミナル）
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

5. ExecutionEngine 起動（別プロセス）
   - KABUSYS_ENV=development python -m kabusys.run_execution

6. ペーパートレード検証（任意）
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

もし README に追加したい情報（例: 実際の設定例ファイル、Docker／systemd ユニット、CI 用のコマンド、より詳しいディレクトリ木など）があれば教えてください。必要に応じてサンプル .env や systemd ユニットのテンプレートも作成します。