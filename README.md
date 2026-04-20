# KabuSys

日本株自動売買システムのコードベース用 README。  
このファイルはリポジトリ内の主要機能・起動手順・使い方・ディレクトリ構成を簡潔にまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的とした小規模なフレームワークです。  
主な機能群は以下の通りです。

- 実行エンジン（ExecutionEngine）: ブローカークライアントを通じた発注管理・リスク管理・注文調整
- 監視（Monitoring）: システム稼働状態、注文状況、リスクを定期ポーリングしてログ / アラート / Kill Switch を処理
- ポートフォリオ構築（Portfolio）: 候補選定、重み付け、株数決定、セクターキャップ、レジーム乗数
- リサーチ（Research）: DuckDB ベースでファクター計算・前方リターン・IC 計算など
- AI モジュール（AI）: ニュース NLP（OpenAI を利用）によるセンチメントスコア化、レジーム判定
- ツール: ペーパートレード検証レポート生成など

設計方針として、DB（DuckDB / SQLite）／外部 API への依存は明確に分離され、テストしやすい純粋関数群と実行コンポーネントが混在しています。

---

## 機能一覧（抜粋）

- 設定管理
  - .env 自動読み込み（.env.local を上書き）
  - 対話式環境設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 実行/監視
  - run_execution: 実取引／ペーパートレードの ExecutionEngine 起動
  - run_monitoring: SystemMonitor を継続ポーリングして監視ログを保持
  - Kill Switch（data/kill.flag）により ExecutionEngine 停止制御

- データベース
  - DuckDB: 時系列・ファクターデータ（デフォルト: data/kabusys.duckdb）
  - SQLite: 監視・発注ログ（デフォルト: data/monitoring.db）
  - Paper Trading 用 SQLite は完全分離（KABUSYS_ENV=paper_trading 時は data/paper_trading.db）

- ポートフォリオ/ポジション計算:
  - 候補選定、スコア配分、等金額配分
  - リスクベース割当、lot（単元）丸め、aggregate cap スケーリング

- AI（OpenAI）
  - ニュースを集約し LLM でセンチメントを算出して ai_scores に保存
  - レジーム判定（ETF MA とマクロニュースの合成）

- ツール
  - paper_verification_report: ペーパートレード検証レポート生成（稼働率 / 成功率 / レイテンシ等）

---

## セットアップ手順

1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境作成（例）
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - ない場合は最低限:
     - pip install duckdb psutil openai
     - （YAML パースを行う場合: pip install PyYAML）

3. プロジェクト設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（例は下記参照）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗 (exit 1) 扱い

5. 必要なディレクトリ
   - logs/ や data/ は起動時に自動作成されることが多いですが、権限エラーが出る場合は手動で作成してください。

---

## 環境変数（主要）

自動ロード順: OS 環境変数 > .env.local > .env  
自動ロードはデフォルトで有効。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須（最低限）:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要なオプション:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、Execution は MockBrokerClient を使い data/paper_trading.db に記録
- OPENAI_API_KEY — OpenAI を利用する機能（news_nlp / regime_detector 等）で必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、production は 0 推奨）

例（.env の最小例）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

## 使い方（起動・CLI）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、PAPER_TRADING_SQLITE_PATH に記録
    - 起動時に data/stop_requested.flag が存在すると起動しない
    - 停止要求は data/stop_requested.flag を作成することで行う（run_execution は定期的に存在を確認）

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL によるポーリング間隔変更が可能（秒）
    - 監視は常に本番の sqlite_path を使用（環境に関係なく）
    - 停止は data/stop_requested.flag を作成

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
    - オプション:
      - --from YYYY-MM-DD
      - --to YYYY-MM-DD
      - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）

- ログ
  - logs/<app_name>.log に日次ローテーションで出力（setup_logging が設定）
  - コンソールは stdout に出力されます（stderr ではない点に注意）

---

## 停止・Kill Switch

- 停止フラグ:
  - data/stop_requested.flag — 管理用の「プロセスを優雅に停止する」フラグ（実行スクリプトでチェック）
  - data/kill.flag — Kill Switch（監視側が条件を満たすとここに理由を書き込み、ExecutionEngine を停止させる）
- PID ファイル:
  - data/execution.pid — ExecutionEngine の PID を保存するパス（Settings.pid_file_path）

Kill Switch の発動要件や監視でのログは kabusys.monitoring 配下に実装されています。

---

## 主要モジュール（簡易説明）

- kabusys.config
  - 環境変数と .env の読み込み・検証ロジックを提供
- kabusys.config_setup
  - 対話式 .env 生成ウィザード
- kabusys.validate_config
  - 起動前の設定検証ツール
- kabusys.run_execution
  - ExecutionEngine の起動スクリプト（KABUSYS_ENV により挙動切替）
- kabusys.run_monitoring
  - SystemMonitor のポーリング起動スクリプト
- kabusys.monitoring
  - monitoring_db.py: SQLite のスキーマ初期化・CRUD ヘルパー
  - system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py / kill_switch.py / alert_manager.py（監視ロジック）
- kabusys.portfolio
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py（候補選定・重み・株数計算）
- kabusys.research
  - factor_research.py / feature_exploration.py（DuckDB を用いたファクター計算・IC 等）
- kabusys.ai
  - news_nlp.py / regime_detector.py（OpenAI を使ったニュースのスコアリング・レジーム判定）
- kabusys.tools
  - paper_verification_report.py（レポート生成）

---

## トラブルシューティング / 注意点

- 必須ライブラリ（duckdb, psutil, openai 等）がないと一部機能が動作しません。エラーメッセージを見て必要パッケージをインストールしてください。
- PyYAML がインストールされていない場合、validate_config は YAML 内容検証をスキップします（ファイルの存在チェックは行います）。
- OPENAI_API_KEY が未設定だと AI 機能（news_nlp, regime_detector）は動作しません。API 呼び出しはリトライ/Fail-safe を備えていますが、キーは必須です。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能。1 秒未満や 0 を与えるとデフォルト 60 秒にフォールバックされます。
- KABUSYS_ENV=paper_trading のときは paper_sqlite_path にログを書きます。本番 DB と分離されます。

---

## ディレクトリ構成（抜粋）

リポジトリルート例:

- .git/
- pyproject.toml / setup.cfg / requirements.txt
- .env, .env.local (not committed)
- data/
  - monitoring.db (SQLite)
  - paper_trading.db (Paper Trading 用 SQLite)
  - execution.pid
  - stop_requested.flag
  - kill.flag
- logs/
  - execution.log
  - monitoring.log
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/ (DuckDB 用の SQL / スクリプト等、プロジェクトに依存)
    - config/ (各種 yaml テンプレート: system_config.yaml 等)

---

## 最後に（推奨ワークフロー）

1. 仮想環境を用意して依存をインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定を検証
4. 本番運用前にローカルで paper_trading モードで動作検証する:
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - python -m kabusys.run_monitoring
5. レポートや AI 機能は OPENAI_API_KEY をセットして実行

ご不明点や追加したいドキュメント項目があれば教えてください。README の補足（例: .env.example、起動スクリプトの systemd サービス定義、より詳細なアーキテクチャ図など）を作成できます。