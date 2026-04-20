# KabuSys

日本株自動売買システムのサブセット実装（ライブラリ＋起動スクリプト）。  
このリポジトリには、戦略／ポートフォリオ構築、リサーチ用ファクター計算、AI ベースのニュース評価、発注エンジン（ExecutionEngine）、監視機構（Monitoring）などの主要コンポーネントが含まれています。

---

## 概要

KabuSys は以下の機能群を提供します。

- データ解析（DuckDB 経由で時系列データを扱う）
- ファクター計算・特徴量探索（research）
- ポートフォリオ構築とポジションサイジング（portfolio）
- 発注管理・リスク管理を含む ExecutionEngine（execution）
- 監視（システム状態・注文状態・リスク監視）と Kill Switch（monitoring）
- ニュースの NLP による銘柄センチメント評価（AI モジュール）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定読み込みウィザード等）
- ペーパートレードの検証用レポート生成ツール

この README は、セットアップ・起動方法およびプロジェクト構成の概観を提供します。

---

## 主な機能一覧

- config:
  - 環境変数の自動読み込み（`.env`, `.env.local`）
  - Settings クラスによる一元管理（KABUSYS_ENV、DB パス、API キー等）
  - 対話式の .env 作成ウィザード（`config_setup.py`）
  - 設定検証 CLI（`validate_config.py`）

- execution:
  - ExecutionEngine（ブローカークライアントを抽象化、paper_trading 用の MockBroker を使用可能）
  - OrderManager / OrderRepository / Reconciler / RiskManager（発注・再整合・リスク制御）

- monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - MonitoringDB: SQLite ベースの永続化（system_status, trade_logs, risk_logs, positions, dashboard）
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込むことで発注エンジンを停止

- research:
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリ）

- portfolio:
  - 候補選定、等重/スコア重み、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算

- ai:
  - ニュースのセンチメント評価（OpenAI を使った LLM 呼び出し）
  - 市場レジーム判定（ETF MA とマクロニュースの合成）

- tools:
  - ペーパートレード検証レポート生成（`paper_verification_report.py`）

---

## 前提条件

- Python 3.9+
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証時に必要）
- OS によりプロセス優先度の設定に管理者権限が必要になる場合があります。

依存パッケージはプロジェクトの配布方法により requirements.txt / pyproject.toml を参照してください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動します。

2. 仮想環境を作成・有効化し、依存をインストールします（例）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
   - pip install -r requirements.txt  （requirements.txt がある場合）  
     または必要なパッケージを個別にインストール:
     - pip install duckdb psutil openai PyYAML

3. 環境変数設定（.env）の作成:
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
     - ウィザードが `.env` を生成します（`KABUSYS_ENV`, API トークン, DB パス 等を設定）
   - 手動で `.env` を作成する場合は `.env.example` を参照してください（プロジェクトにある場合）。
   - 主要な環境変数（抜粋、デフォルトは括弧内）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - LOG_LEVEL (INFO 等)
     - KILL_FLAG_CLEAR_ON_START (0/1)
     - PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject") — paper_trading の注文挙動

4. 設定の妥当性チェック:
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの作成（必要なら）:
   - data/, logs/ ディレクトリを作成（`utils.logging_setup` は起動時に自動で作成を試みます）
   - ただし `.env` のパスに存在しない親ディレクトリがあれば警告が出ます（自動作成されることも多い）

---

## 実行方法（使い方）

主要な起動コマンド（プロジェクトルートから）:

- ExecutionEngine（発注エンジン）を起動:
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存します:
    - paper_trading: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に書き込み
    - live: 本番ブローカーを使用

- Monitoring（監視ループ）を起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - Monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数:
    - PAPER_TRADING_SQLITE_PATH を設定している場合は `--db` を省略可

- AI モジュール（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を環境変数に設定してから、該当モジュールを呼び出す Python スクリプト／REPL から利用します。
  - AI 機能は外部 API（OpenAI）に依存し、API キーが必須です。

停止／フラグ関連:

- kill.flag（Settings.kill_flag_path、デフォルト: data/kill.flag）:
  - KillSwitch はリスク条件検出時にこのファイルを書き込んで ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine は起動時に kill.flag の存在を確認し、存在する場合は起動しません（`KILL_FLAG_CLEAR_ON_START` により起動時自動クリアの挙動を制御）。
- stop_requested.flag:
  - run_monitoring / run_execution はプロジェクト内の data/stop_requested.flag を検知してループを終了します（ローカル手動停止用）。

ログ:

- デフォルトログディレクトリ: logs/
- ログファイル名: 起動コマンドに応じて `<app_name>.log`（例: execution.log, monitoring.log）に日次ローテーションで記録されます。
- ログは標準出力（stdout）とファイルの両方に出力されます（ファイル書き込みに失敗した場合はコンソールのみで継続）。

---

## 主要ファイル・モジュール説明（抜粋）

- src/kabusys/config.py
  - Settings クラス: 環境変数をラップして提供。自動 .env ロード機能あり。
- src/kabusys/config_setup.py
  - .env を対話的に作成するウィザード。
- src/kabusys/validate_config.py
  - .env と config/*.yaml の基本チェックを行う CLI。
- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は分離された paper DB を使用。
- src/kabusys/run_monitoring.py
  - Monitoring（SystemMonitor を含む）ポーリングループ起動スクリプト。
  - MONITOR_POLL_INTERVAL で間隔上書き可（デフォルト 60 秒）。
- src/kabusys/monitoring/*
  - monitoring_db.py: SQLite テーブル作成・読書きユーティリティ
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py など
- src/kabusys/execution/*
  - ExecutionEngine と周辺のブローカー抽象化、Order 管理、Risk 管理（エンジン本体はここに実装）
- src/kabusys/portfolio/*
  - ポートフォリオ構築、重み算出、ポジションサイズ計算
- src/kabusys/research/*
  - ファクター計算・特徴量解析
- src/kabusys/ai/*
  - news_nlp.py: ニュース集約 → OpenAI に投げる → ai_scores に保存
  - regime_detector.py: マクロセンチメント + ETF MA でレジーム判定
- src/kabusys/tools/paper_verification_report.py
  - ペーパートレード検証用レポート出力

---

## ディレクトリ構成

（project root 配下、src/kabusys を基準に抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/
      - (ExecutionEngine, OrderManager, BrokerFactory, ...)
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
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
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/           (実行時に DB, pid, flag などが置かれる想定)
    - logs/           (ログ出力先、デフォルト)

プロジェクトルートには pyproject.toml / requirements.txt 等がある想定です（配布方法により異なります）。

---

## 重要な運用上の注意

- 本番環境（KABUSYS_ENV=live）では設定に細心の注意を払ってください。`validate_config` は live の場合に追加の警告を出します。
- kill.flag、stop_requested.flag、execution.pid などフラグ/ファイルを使った停止制御を行います。これらは data/ 下に保存されるため、運用時に適切なパーミッションと監視を行ってください。
- OpenAI など外部 API の呼び出しは料金とレート制限に注意して運用してください。AI 関連機能は API キー（OPENAI_API_KEY）が必須です。
- process priority / CPU affinity の設定はプラットフォーム依存です。設定に失敗した場合は警告が出ますが、プロセスは継続します。
- ペーパートレードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。paper_trading 実行時は必ず適切な DB を使用してデータの混在を回避してください。

---

## 例: 最小起動フロー（ローカル開発）

1. 仮想環境作成・依存インストール
2. python -m kabusys.config_setup （.env を作る）
3. python -m kabusys.validate_config
4. python -m kabusys.run_monitoring  （別ターミナルで）
5. python -m kabusys.run_execution   （別プロセスで ExecutionEngine を起動）

---

この README はコードベースの主要機能と運用上のポイントをまとめたものです。詳細は各モジュールの docstring やソースコードを参照してください。問題や改善提案があれば Issues を作成してください。