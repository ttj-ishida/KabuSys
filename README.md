# KabuSys — README (日本語)

概要
---
KabuSys は日本株の自動売買・リサーチ基盤を想定した Python パッケージです。  
主要機能として、戦略の研究用ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、システム監視・アラート、AI（ニュース NLP / レジーム判定）連携、ペーパートレード検証レポート生成などを含みます。

主な特徴
---
- ファクター計算（momentum / value / volatility など）を DuckDB で高速に実行
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ExecutionEngine（本番 / ペーパートレード分離、Broker クライアントファクトリ）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- ロギングユーティリティ（コンソール + 日次ローテートファイル出力）
- OpenAI を使ったニュースセンチメント（news_nlp）とレジーム判定（regime_detector）
- .env 対話式ウィザード（config_setup）と設定の検証ツール（validate_config）
- ペーパートレード検証レポート生成ツール（tools.paper_verification_report）

セットアップ手順
---
1. リポジトリをクローン／配置し、Python 仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします（requirements.txt / pyproject.toml に依存）。
   - 例（pip）:
     - pip install -r requirements.txt
   - 必須ライブラリ（主なもの）:
     - duckdb, psutil, openai, sqlite3（標準）, PyYAML（config 検証に必要な場合）

3. .env を作成します（対話式ウィザード推奨）。
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 既存 .env がある場合は上書きまたは編集して設定します。

4. 設定検証:
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict

環境変数（主なもの）
---
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード

推奨 / デフォルト:
- KABUSYS_ENV — 実行環境: development | paper_trading | live  （デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールを使う場合）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant / partial / never / reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動消去するか（0/1、デフォルト: 0）

使い方（コマンド）
---
- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告を FAIL とする）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全に分離します。
    - 起動時に実行中フラグ（pid ファイル）を書き、data/stop_requested.flag を検知すると停止します。
    - プロセス優先度を高に設定します（set_process_priority("high")）。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60 秒）。不正値はデフォルトへフォールバックします。
    - 監視は KABUSYS_ENV に関わらず本番の sqlite_path（SQLITE_PATH）を使用します（監視ログは一元管理）。
    - stop_requested.flag を検知するとループを終了します。
    - プロセス優先度を高に設定します。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

主要コンポーネントの説明
---
- config_setup.py
  - .env を対話的に生成・上書きするウィザード。秘密値はマスク表示。
- validate_config.py
  - .env と config/*.yaml の存在・基本整合性をチェックする CLI。
- run_execution.py
  - ExecutionEngine を起動するエントリポイント。BrokerClientFactory により本番/ペーパートレードクライアントを切替。
- run_monitoring.py
  - SystemMonitor を定期実行するエントリポイント。MONITOR_POLL_INTERVAL で間隔制御。
- monitoring/*
  - システム状態・注文ログ・リスク監視・KillSwitch（kill.flag の書き込み）など、監視ロジックと永続化（SQLite）を提供。
- ai/*
  - news_nlp: raw_news を集約して OpenAI に問い合わせ、ai_scores を DuckDB に書き込む。
  - regime_detector: ETF 1321 の MA とマクロニュースを組み合わせて市場レジームを判定し永続化。
- research/*
  - factor_research, feature_exploration: DuckDB 上でファクターや将来リターン、IC 等を計算。
- portfolio/*
  - 候補選定、重み付け、ポジションサイズ計算、セクター制約・レジーム乗数適用などの純粋関数を提供。
- utils/logging_setup.py
  - stdout と 日次ローテーションファイル（logs/<app_name>.log）を設定するユーティリティ。
- utils/process_priority.py
  - プラットフォーム差を吸収してプロセス優先度や CPU affinity を設定するユーティリティ。

運用上の注意
---
- 本番環境（KABUSYS_ENV=live）では設定値の確認を厳重に行ってください（validate_config の警告を無視しないこと）。
- .env は機密情報を含むため Git にコミットしないでください（config_setup はヘッダにその旨を出力します）。
- KillSwitch は data/kill.flag を書き込み、ExecutionEngine 停止のために使用します。KILL_FLAG_CLEAR_ON_START=1 を本番で使うのは危険です（自動クリアされるため誤動作のリスク）。
- Monitoring は監視用 DB（SQLITE_PATH）を使います。run_monitoring は環境に関わらずその監視 DB を参照します。
- run_execution はペーパートレード時に paper_trading DB を使って本番 DB と分離します（PAPER_TRADING_SQLITE_PATH）。

設定例（.env に記載する代表項目）
---
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- OPENAI_API_KEY=sk-...
- LOG_LEVEL=INFO
- LOG_DIR=logs
- KILL_FLAG_CLEAR_ON_START=0
- PAPER_FILL_MODE=instant

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py
- config.py                 — 環境変数／設定読み込みロジック
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor 起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py  — ペーパートレード検証レポート生成スクリプト
- ai/
  - __init__.py
  - news_nlp.py             — ニュース NLP（OpenAI）
  - regime_detector.py      — 市場レジーム判定（OpenAI）
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- monitoring/
  - monitoring_db.py        — SQLite テーブル初期化 & 永続化 API
  - system_monitor.py
  - trade_monitor.py        — （注）実装ファイルあり（コードベースに含まれる）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py        — （注）実装ファイルあり（コードベースに含まれる）
- execution/
  - broker_factory.py       — BrokerClientFactory（本番/Mock 切替）
  - execution_engine.py     — ExecutionEngine（メインの発注ロジック）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- data/                     — 実行時に使用する data/ 以下のファイル群（DB・フラグ等）
- utils/
  - __init__.py
  - logging_setup.py
  - process_priority.py

補足（ログ / フラグ / PID）
---
- ログ:
  - setup_logging により stdout と logs/<app_name>.log（日次ローテーション）へ出力します。
- 停止フラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution はこれを検知して安全に停止します。
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine 停止シグナルを送ります。
- PID:
  - 実行時に data/execution.pid（デフォルト）等に PID を出力します。

よくある運用フロー（例）
---
1. .env を作成（python -m kabusys.config_setup）  
2. 設定を検証（python -m kabusys.validate_config）  
3. DuckDB・SQLite ファイルの配置（必要に応じてスキーマを準備）  
4. 監視プロセス起動（daemon で run_monitoring）  
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
5. 実行エンジン起動（本番／ペーパー切替）  
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
6. ペーパートレード検証（任意期間）  
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
---
このドキュメントはコードベースから抽出した設計・利用情報をまとめたものです。実際に運用する場合はライセンス条項、セキュリティ、取引所 API の利用規約に従ってください。貢献や修正は Pull Request を通じてお願いします。

---

不明点や README に追加して欲しい具体的な情報（例: CI 手順、Docker 化、詳細な設定テンプレートなど）があれば教えてください。README を拡張して対応します。