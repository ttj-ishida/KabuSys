# KabuSys

日本株自動売買システムの軽量実装（モジュール群）。  
このリポジトリには運用用の起動スクリプト、監視・キルスイッチ、ポートフォリオ構成、ファクター計算、AI ベースのニューススコアリングなどの主要コンポーネントが含まれます。

## プロジェクト概要
- DuckDB を分析用に、SQLite を監視・発注ログ用（およびペーパートレード用）に使用するハイブリッド構成。
- 本番 / ペーパートレード / 開発の実行環境を切り替え可能（KABUSYS_ENV）。
- 監視 (Monitoring) が稼働状況やデータ鮮度を監視し、リスク条件が満たされれば kill.flag を書き込んで ExecutionEngine を安全に停止する仕組みを備える。
- AI（OpenAI）を用いたニュースセンチメント評価や市場レジーム判定機能を実装（API キー必要）。
- 研究用モジュール（ファクター計算、IC 計算、特徴量解析）やポートフォリオ構成アルゴリズムを提供。

## 主な機能一覧
- 環境設定ウィザード: .env の対話的生成（kabusys.config_setup）
- 設定検証: .env / config/*.yaml の事前検証（kabusys.validate_config）
- ExecutionEngine 起動スクリプト: 発注エンジン（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db を利用
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）で安全停止
- Monitoring 起動スクリプト: SystemMonitor のポーリングループ（run_monitoring.py）
  - 環境に関係なく本番 sqlite_path を監視用 DB として使用
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor の統合とアラート送出
- KillSwitch: リスク条件に基づく kill.flag の書き込み（Execution 停止）
- RiskMonitor: ドローダウン・ポジション上限の監視
- MonitoringDB: SQLite ベースの永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
- Portfolio モジュール:
  - 銘柄選定、等重・スコア重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- Research モジュール:
  - Momentum / Volatility / Value のファクター計算、将来リターン、IC、統計サマリ
- AI モジュール:
  - news_nlp: OpenAI を使ったニュースの銘柄別センチメント評価（ai_scores テーブルへ書込）
  - regime_detector: ma200 とマクロニュースを合成して市場レジームを判定
- ユーティリティ:
  - ログ設定（ログの stdout + 日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール:
  - paper_verification_report: ペーパートレード結果の検証レポート生成

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - 例: git clone <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 最低限必要なパッケージ:
     - duckdb, psutil, openai, pyyaml（YAML 検証をする場合）

4. 環境変数設定 (.env)
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または .env を手動で作成。最低必須:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 重要: .env をリポジトリにコミットしないこと

5. データディレクトリの準備（必要なら）
   - デフォルトの DB/ログパス:
     - SQLite (監視): data/monitoring.db
     - Paper SQLite: data/paper_trading.db
     - DuckDB: data/kabusys.duckdb
     - PID / kill flag: data/execution.pid, data/kill.flag
     - ログ: logs/
   - これらは起動時に自動作成されることが多いですが、権限やパスに注意してください。

## 使い方（主要コマンド）
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL 扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（発注エンジン）
  - 通常:
    - python -m kabusys.run_execution
  - 実行中停止:
    - 監視/手動で data/stop_requested.flag を作成するとエンジンが停止します
    - KillSwitch により data/kill.flag が書かれる場合もあります（Execution 側で kill.flag の挙動を確認してください）
  - ペーパートレード:
    - KABUSYS_ENV=paper_trading を .env または環境変数で設定すると MockBroker を使用し data/paper_trading.db に記録

- Monitoring を起動（定期ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を指定（秒）:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルトは 60 秒
  - 監視プロセスは data/stop_requested.flag を検出すると終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 環境変数:
    - PAPER_TRADING_SQLITE_PATH でデフォルト DB を上書き可能

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーが必須（env: OPENAI_API_KEY または引数で渡す実装あり）
  - 例（モジュール呼び出し）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

## 重要な環境変数
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: 発注はモックで、専用 SQLite を使用
  - live: 本番（注意深く設定を行うこと）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- OPENAI_API_KEY: OpenAI を利用する場合必須
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

## ログ
- デフォルト出力: コンソール（stdout）と logs/<app_name>.log（日次ローテート、30 日保持）
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。
- app_name は起動スクリプトで "execution" / "monitoring" など指定されています。

## 停止 / キルの仕組み
- data/stop_requested.flag:
  - run_monitoring と run_execution が監視している停止フラグ（stop を要求する外部トリガー）
  - 存在を検出するとそれぞれのループを終了または Engine.stop() を呼んで停止
- KillSwitch:
  - 監視側でリスク条件（ドローダウン、ポジション上限など）を評価し、必要なら data/kill.flag を書き込む
  - Execution は起動時に kill.flag の有無や起動時クリア設定に従って動作

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / .env 読み込みロジック
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - ...（TradeMonitor, AlertManager 等の実装が想定される）
  - execution/             — Execution 系コンポーネント（Engine, BrokerFactory, OrderManager 等）
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

（上記は本コードベースに含まれる主要ファイルを抜粋したものです）

## 運用上の注意
- KABUSYS_ENV=live の場合は非常に慎重に構成を確認してください（validate_config によるチェックを推奨）。
- .env に機密情報を保存する場合は Git 等に絶対にコミットしないこと。
- OpenAI 使用時は API のレート制限やコストに注意。news_nlp モジュールは一定の retry/backoff ロジックを備えていますが、運用時のモニタリングが必要です。
- run_execution / run_monitoring 起動直後にプロセス優先度を "high" に設定しようとしますが、OS 権限や環境によっては警告が出ることがあります（スキップされます）。

## 開発・テスト
- モジュールは依存注入を念頭に置いて設計されており、DB 接続や OpenAI 呼び出し等はテスト時に差し替え可能です（例: duckdb の接続、OpenAI 呼び出し関数のモック）。
- validate_config は設定ファイルの存在・YAML パース（PyYAML がインストールされている場合）もチェックできます。

---

必要であれば、README に「よくあるトラブルと対処」「システム図」「データベーススキーマの詳細」「デプロイ手順（systemd / docker-compose など）」を追加できます。どの情報を優先して追加しましょうか？