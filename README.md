# KabuSys

日本株自動売買システムのコアライブラリ／起動スクリプト群

この README は提供されたコードベース（src/kabusys 以下）を元にした概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアモジュール群です。  
主要機能として、シグナル→ポートフォリオ構築→発注（ExecutionEngine）に加え、実行中の監視・アラート・Kill Switch、研究用ファクター計算、LLM を用いたニュースセンチメント解析などを提供します。

設計方針の特徴：
- 実行ロジックと永続化（SQLite / DuckDB）を分離
- Paper Trading モードで本番 DB と完全分離（専用 SQLite）
- OpenAI API を使った NLP / レジーム判定機能（環境変数でキー指定）
- 自動ログ設定（コンソール + 日次ローテーションファイル）
- .env ベースの設定読み込み（.env.local を上書き）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（発注処理）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
- 設定ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 環境変数・config/*.yaml の事前検証 CLI
- 研究（Research）
  - factor_research.py / feature_exploration.py: ファクター計算・IC 等の統計解析
- ポートフォリオ構築
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py
- AI
  - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector.py: マクロ + ETF MA200 を用いた市場レジーム判定
- 監視・Kill Switch
  - monitoring_engine.py, system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py
  - monitoring_db.py: 監視用 SQLite のテーブル初期化 / 永続化ロジック
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成
- ユーティリティ
  - utils/logging_setup.py: 共通ログ設定
  - utils/process_priority.py: プロセス優先度 / CPU アフィニティ設定

---

## 要件（推奨）

- Python 3.10+
- 必須 Python パッケージ例:
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（validate_config の YAML 検証）
- SQLite は組み込みなので追加不要

（実際の依存はプロジェクトの requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / 展開します。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は最低限 duckdb, psutil, openai をインストール:
     - pip install duckdb psutil openai

4. 初期設定（.env）を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で `.env` をプロジェクトルートに作成（.env.example を参照）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合は `--strict` を付ける

6. データディレクトリ
   - デフォルトの DB / pid / flag 等は `data/` 配下に作成されます。必要に応じて .env のパスを上書きしてください。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（デフォルト値あり）:
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
  - paper_trading: MockBrokerClient を使用しデータは `data/paper_trading.db` に記録（本番 DB と隔離）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（"DEBUG"/"INFO"/...）
- OPENAI_API_KEY — OpenAI 呼び出しに必要（ai モジュールを使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番時のアラート通知（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — paper_trading 時のモック約定挙動: "instant" | "partial" | "never" | "reject"（デフォルト "instant"）

注意:
- .env と .env.local は自動でロードされます（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## 使い方（起動例）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、`PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）へ記録
    - プロセス優先度を high に設定し、thread で engine.run_session を実行
    - data/stop_requested.flag を検知すると停止

- Monitoring を起動（常時ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を参照（環境にかかわらず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- ログ
  - ルートロガーはコンソール（stdout）とファイル（logs/<app_name>.log）へ出力（デフォルト logs ディレクトリ、日次ローテーション）

---

## 実運用上の注意点

- Kill Switch / Stop Flag
  - ExecutionEngine 停止は `data/kill.flag`（KillSwitch）または `data/stop_requested.flag`（run_*.py が監視）で制御する仕組みがあります。運用時は KILL_FLAG_CLEAR_ON_START の設定に注意してください（本番ではクリアしない方が安全）。

- Paper Trading
  - paper_trading モードは本番 DB とは分離されます。必ず `KABUSYS_ENV` を確認してください。

- OpenAI
  - news_nlp や regime_detector は OPENAI_API_KEY が必要です。API エラーはフォールバック実装（0.0 等）で安全に継続しますが、結果の信頼性に注意してください。

- DB マイグレーション
  - monitoring_db.init_monitoring_db() は初回起動時に必要テーブルを作成し、既存 DB の列追加マイグレーションを行います。

- 権限
  - process_priority の設定は OS とユーザー権限に依存します。設定できない場合は警告が出ますが実行自体は継続します。

---

## ディレクトリ構成（主要ファイル）

(src/kabusys 以下を想定)

- __init__.py
- config.py — 環境変数／Settings 管理（自動 .env ロード含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py

- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - risk_monitor.py
  - trade_monitor.py (存在する想定)
  - kill_switch.py
  - alert_manager.py (存在する想定)

- execution/ (発注関連コンポーネント、ファクトリ等)
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
  - ...（他）

- utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py

- tools/
  - paper_verification_report.py
  - __init__.py

- data/（実行時に作成・利用）
  - monitoring.db (デフォルト SQLITE_PATH)
  - kabusys.duckdb (デフォルト DUCKDB_PATH)
  - paper_trading.db (paper_trading 用)
  - execution.pid, stop_requested.flag, kill.flag など

---

## 参考／よく使うコマンドまとめ

- 対話式 .env 作成:
  - python -m kabusys.config_setup

- 設定チェック:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動:
  - python -m kabusys.run_execution

- 監視サービス起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの構成と主要な使い方をまとめたものです。実運用の前に `python -m kabusys.validate_config` で設定を確認し、.env の必須値（特に API トークンやパスワード）を適切に設定してください。必要があればドキュメントに追記します。