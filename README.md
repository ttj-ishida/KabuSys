# KabuSys

日本株向けの自動売買 / 研究ツール群の軽量フレームワークです。  
このリポジトリには実行エンジン（ExecutionEngine）、監視機能（Monitoring）、ポートフォリオ構築ユーティリティ、研究用ファクター計算、LLM を用いたニュース・レジーム判定などのモジュールが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は「自動売買ロジックの実行」と「運用監視・リスク管理」、および「研究用データ処理・解析」を分離して提供することです。  
主要な特徴:

- ExecutionEngine（発注・リスク管理・注文リコンサイル）
- Monitoring（システム稼働・注文・リスクのポーリング監視、必要時の Kill Switch 発動）
- Portfolio 構築ユーティリティ（候補選定、重み計算、ポジションサイジング、セクター制約）
- Research（DuckDB を用いたファクター計算・特徴量解析）
- AI モジュール（OpenAI を用いたニュースセンチメント・レジーム判定）
- 各種 CLI（.env 作成ウィザード、設定検証、Paper Trading レポート生成）

---

## 機能一覧

- 実行系
  - run_execution.py: ExecutionEngine を起動するメインスクリプト
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に分離
    - 起動時にプロセス優先度を高くする
    - 停止は `data/stop_requested.flag` / `data/kill.flag` によるフラグで制御
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（デフォルト 60 秒）
  - MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor によるポーリング、アラート管理、Kill Switch 評価
  - 監視ログは SQLite（デフォルト: data/monitoring.db）に永続化
- データ / 研究
  - research/*.py: DuckDB 接続を受けたファクター計算、特徴量解析、IC 計算など
  - tools/paper_verification_report.py: Paper Trading の検証レポートを生成
- AI
  - ai/news_nlp.py: raw_news を集約して OpenAI API に投げ、銘柄ごとのセンチメントを ai_scores に書き込む
  - ai/regime_detector.py: ETF の MA とマクロニュースの LLM センチメントを合成して市場レジームを判定・永続化
- ユーティリティ
  - config.py: 環境変数と .env 自動読み込み（.env / .env.local ）
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前チェック（必須環境変数、YAML、パス等）
  - utils/logging_setup.py: 一元的なログ設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py: OS 横断的なプロセス優先度設定（psutil 使用）

---

## セットアップ手順（開発環境）

1. レポジトリをクローンしてワークディレクトリに移動
   - 例: git clone ... && cd <repo>

2. Python 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 必須（主なもの）:
     - duckdb
     - psutil
     - openai
   - 推奨 / オプション:
     - PyYAML（validate_config の YAML 検証）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合はそれを使用してください）

4. ディレクトリ作成（初回）
   - mkdir -p data logs

5. 環境変数の設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - またはプロジェクトルートに .env を直接作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要なオプション（デフォルト値は括弧内）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db) — paper_trading 用 DB
     - LOG_LEVEL (INFO)
     - OPENAI_API_KEY（AI機能を使う場合）
     - KILL_FLAG_CLEAR_ON_START (0|1)

   - 自動読み込み:
     - config.py はプロジェクトルートの .env / .env.local を自動で読み込みます（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）

6. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も致命的扱いにする場合:
     - python -m kabusys.validate_config --strict

---

## 使い方（実行例）

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、paper_trading DB（PAPER_TRADING_SQLITE_PATH）に分離されたモックブローカーで動きます。

- 監視プロセスを起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- .env の初期生成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート出力:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI スコアリング / レジーム判定（スクリプトを直接呼ぶ例）
  - Python REPL やスクリプト内で duckdb 接続を作成して呼び出す:
    - from kabusys.ai.news_nlp import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, target_date=datetime.date(2026, 4, 1), api_key="sk-...")

- 終了 / 停止フラグ
  - ExecutionEngine / monitoring はフラグファイルや pid ファイルで制御します:
    - data/stop_requested.flag: run_* スクリプトがこのファイルを検知するとループを終了します
    - data/kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine に停止シグナル）
    - data/execution.pid: 実行エンジンの PID を保持（run_execution で使用）
  - Kill Switch 自動クリア:
    - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリア（本番では注意）

---

## 主要設定と環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 主要（デフォルト）
  - KABUSYS_ENV (development|paper_trading|live) — default: development
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
  - LOG_LEVEL — default: INFO
  - OPENAI_API_KEY — AI 機能を使うなら必須
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒） default: 60
  - KILL_FLAG_CLEAR_ON_START — default: 0
  - LOG_DIR — ログ出力先（utils.logging_setup で参照）

---

## ディレクトリ構成

以下はパッケージ内の主要ファイルと簡単な説明です（src/kabusys 以下）。

- __init__.py
- config.py — 環境変数 / .env の読み込みと Settings クラス
- config_setup.py — .env 作成ウィザード（CLI）
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

- execution/
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  （発注・リスク管理に関連する実装）

- monitoring/
  - monitoring_db.py — SQLite スキーマと永続化層
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度・プロセス生存チェック
  - trade_monitor.py
  - risk_monitor.py — ドローダウン・ポジション上限チェック
  - kill_switch.py — フラグファイルによる停止判定
  - monitoring_engine.py — 各 Monitor を束ねる

- portfolio/
  - portfolio_builder.py — 候補選定・重み
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - position_sizing.py — 株数計算・スケーリング

- research/
  - factor_research.py — Momentum/Value/Volatility ファクター計算（DuckDB）
  - feature_exploration.py — forward returns / IC / 統計サマリー

- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — マクロ + MA によるレジーム判定（OpenAI）
- data/ (ランタイム)
  - monitoring.db (SQLite)
  - paper_trading.db (paper trading 用)
  - kabusys.duckdb (分析データベース)
  - kill.flag / stop_requested.flag / execution.pid などの制御ファイル

- utils/
  - logging_setup.py — 共通ログ設定
  - process_priority.py — 優先度 / CPU affinity 設定

- tools/
  - paper_verification_report.py — Paper Trading の評価レポート作成

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）の場合は特に .env / 秘密情報の管理に注意してください。`.env` をリポジトリにコミットしないでください。
- Kill Switch、stop flag、pid ファイルでプロセス制御を行います。KILL_FLAG_CLEAR_ON_START=1 は本番で危険です（自動クリアを避けてください）。
- Paper Trading モードは本番 DB と完全分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 等の外部 API を使う機能は API キーが必要です。失敗時はフェイルセーフなフォールバック（スコア 0 など）を実装している箇所がありますが、料金とレート制限に注意してください。
- ログは stdout と logs/<app_name>.log に出力されます。ログディレクトリ作成に失敗した場合はファイルログをスキップして stdout のみになります。

---

## 追加情報 / 開発メモ

- config.py はプロジェクトルートを .git または pyproject.toml から検出して .env 自動読み込みを行います（CWD に依存しない設計）。
- monitoring_db.py は既存 DB の簡単なマイグレーション処理（カラム追加）を行います。
- AI モジュールはレスポンスの検証・リトライ・局所的なフェイルセーフを備えていますが、LLM の振る舞いは常に注意して運用してください。

---

必要があれば README に「起動時の systemd ユニット例」や「Docker / コンテナ運用の簡易手順」などの追加セクションを作成します。どの情報を優先して追記しましょうか？