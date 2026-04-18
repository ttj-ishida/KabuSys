# KabuSys

日本株向けの自動売買・リサーチ基盤（KabuSys）のリポジトリです。  
この README はローカルでのセットアップ、主要機能、実行方法、ディレクトリ構成などを説明します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群から構成された、株式自動売買および研究用の基盤です。

- データ読み書き / DuckDB を用いたファクター計算（research）
- ポートフォリオ構築（選定・重み付け・株数算出）
- ExecutionEngine を介した発注処理（実口座 / ペーパー口座切替）
- 監視（system / trade / risk）と Kill Switch による自動シャットダウン
- AI を使ったニュース NLP / レジーム判定（OpenAI API 統合）
- ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証）
- ペーパートレード検証レポート生成ツール

設計上の注意点：
- 設定は .env（もしくは環境変数）で管理します。`.env` は絶対にコミットしないでください。
- Paper trading（`KABUSYS_ENV=paper_trading`）は本番 DB と分離され、専用 SQLite（デフォルト: `data/paper_trading.db`）を使用します。
- OpenAI を使う機能は `OPENAI_API_KEY` が必要です。
- 監視や起動スクリプトはファイルフラグ (`data/stop_requested.flag`, `data/kill.flag`) によって制御します。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト: `run_execution.py`
  - Paper trading と Live の切替（MockBrokerClient を用いたペーパートレード）
  - リスク管理（最大ポジション比率、ドローダウン制御等）
- Monitoring
  - System / Trade / Risk の監視コンポーネント
  - KillSwitch による自動停止（kill.flag の書込み）
  - 監視 DB（SQLite）へログ永続化（`monitoring_db.py`）
- Portfolio
  - 銘柄選定、等金額／スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB を利用）
  - 将来リターン、IC（Information Coefficient）計算等
- AI
  - ニュースから銘柄別センチメントを評価（OpenAI API）
  - マクロニュース + ETF MA200 を利用した市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成ツール（`paper_verification_report.py`）
- Utilities
  - 対話式 .env 生成（`config_setup.py`）
  - 設定検証 CLI（`validate_config.py`）
  - ログ設定ユーティリティ（`utils/logging_setup.py`）
  - プロセス優先度・CPU affinity 設定（`utils/process_priority.py`）

---

## セットアップ手順（ローカル）

前提: Python 3.9+ を想定（コードに依存する機能により最新版推奨）。  

1. リポジトリをクローン / 取得
2. 仮想環境を作成・有効化（推奨）
   - Linux / macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1
3. 必要なパッケージをインストール
   - 最低限の依存（例）:
     - pip install duckdb psutil openai
   - 追加（YAML 検証を行いたい場合）:
     - pip install pyyaml
   - （バージョンは環境に合わせて固定してください）
4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくは `.env` を手動で作成してください。必要な主要環境変数は下記参照。
5. 設定検証
   - python -m kabusys.validate_config
   - 本番前は `--strict` オプションで警告も FAIL 扱いにできます。
6. データディレクトリ作成
   - デフォルトでは `data/` 配下に DB や pid/flag ファイルが作られます。必要に応じて作成してください。
7. ログディレクトリ（任意）
   - デフォルトは `logs/`。環境変数 `LOG_DIR` で変更可能。

注意: `.env` の自動ロードはプロジェクトルート（`.git` または `pyproject.toml`）を探して実行されます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要な環境変数（抜粋、デフォルト含む）

- KABUSYS_ENV
  - 値: `development` | `paper_trading` | `live`
  - デフォルト: `development`
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL
  - デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY
  - AI 機能（ニュース NLP / レジーム判定）で必要
- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH
  - デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH
  - デフォルト: data/paper_trading.db（`KABUSYS_ENV=paper_trading` 時に使用）
- LOG_LEVEL
  - デフォルト: INFO
- LOG_DIR
  - デフォルト: logs/
- MONITOR_POLL_INTERVAL
  - 監視ループのポーリング間隔（秒）。run_monitoring はこの環境変数で上書き可能。デフォルト: 60
- PAPER_FILL_MODE
  - mock broker の挙動（paper_trading 時）。`instant` | `partial` | `never` | `reject`
  - デフォルト: `instant`
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
  - Execution のプロセス管理 / Kill Switch に関する設定

（上記は抜粋です。詳しくは `src/kabusys/config.py` と `config_setup.py` を参照してください。）

---

## 使い方（起動 / 実行例）

- .env を作成・編集
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 本番チェック: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 / ペーパー）
  - python -m kabusys.run_execution
  - 実行中は `data/execution.pid` が作成され、`data/stop_requested.flag` を作成すると停止します。
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録します。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 `MONITOR_POLL_INTERVAL` を設定（秒）。
  - 監視は常に production の sqlite_path（`SQLITE_PATH`）を参照してログを書き込みます。
  - 監視ループは `data/stop_requested.flag` の存在で終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` でも変更可能

- AI 機能（例）
  - OpenAI API キーを設定（`OPENAI_API_KEY`）
  - kabusys.ai.score_news（関数 API）や kabusys.ai.regime_detector.score_regime を使用して、DuckDB 接続を与えて実行します。

- ログ
  - `kabusys.utils.logging_setup.setup_logging(app_name=...)` により:
    - コンソール（stdout）出力
    - 日次ローテートされたファイル出力（`logs/<app_name>.log`）

---

## 監視 / 停止フラグについて

- 停止要求（全プロセス共通）
  - `data/stop_requested.flag` の存在を監視して、run_execution / run_monitoring のループやスレッドを安全に終了します。
- Kill Switch（自動停止）
  - RiskMonitor などによる評価で `KillSwitch` が `data/kill.flag` を書き込むと、ExecutionEngine の起動を阻止し（あるいは稼働中のエンジンに停止命令を送る）ます。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動で消します（本番では推奨されません）。

---

## DB / マイグレーション

- 監視用 DB スキーマは `kabusys.monitoring.monitoring_db.init_monitoring_db` にて冪等に作成されます。
  - 起動スクリプト実行時に自動でテーブル作成・簡易マイグレーション（カラム追加）を行います。
- DuckDB（分析用）は `DUCKDB_PATH` を指定してください。
- Paper trading は `PAPER_TRADING_SQLITE_PATH` に分離可能です。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 配下の主要モジュールと概要です。

- kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）→ ai_scores 書き込み
    - regime_detector.py — レジーム判定（ETF MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種モニタ
    - monitoring_engine.py — 各 monitor を束ねるエンジン
    - kill_switch.py, alert_manager.py — Kill Switch / 通知管理（alert_manager は要確認）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py (および MockBroker)
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
  - research/
    - factor_research.py, feature_exploration.py — ファクター・解析ユーティリティ
  - data/ (実行時に使用する DB / ファイルが配置される想定)
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity
  - その他（詳細は各ファイルを参照）

---

## 開発時のヒント

- DuckDB / SQLite のパスは `.env` で変更できます。テスト用の DB を用意して、実運用 DB と分離してください。
- OpenAI 連携部分は外部 API 呼び出しを伴うため、ユニットテストではモック化（patch）してテストするのが推奨です。
- `config.py` はプロジェクトルートの検出ロジックを持つため、パッケージ配布後でも環境変数読み込みが安定しています。テストで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- logging の設定は `setup_logging` を各起動スクリプトの最初で呼んで統一してください。

---

## ライセンス / 備考

この README はコードベースから主要点を抜粋して作成しています。各モジュールの詳細実装や API 使用法（例: ExecutionEngine の public メソッド、BrokerClient インターフェース等）は該当ファイルの docstring / コメントを参照してください。

何か特定の機能（例: ExecutionEngine の起動引数、AI モジュールの詳細な使い方、monitoring の alert_manager 実装）についてのドキュメントが必要であれば、対象モジュール名を指定して追加の README を作成します。