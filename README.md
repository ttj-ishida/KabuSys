# KabuSys — 日本株自動売買システム

このリポジトリは、日本株向けの自動売買システム（KabuSys）のコアユーティリティ群を含みます。
戦略構築／ポートフォリオ構成、実行エンジン、監視機構、研究用・ツールスクリプト、AI（ニュース NLP / レジーム判定）連携などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の機能を備えたモジュール群で構成されています。

- 戦略・ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算、リスク調整）
- ExecutionEngine（発注管理、ブローカークライアント抽象化、リスク管理、リコンサイル）
- Monitoring（システム状態・注文ログ・リスク監視、Kill Switch）
- Research（ファクター計算、特徴量探索、IC 計算）
- AI モジュール（ニュースの NLP によるセンチメントスコア、マクロを使ったレジーム判定）
- ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度設定、ツールスクリプト）

設計方針の特徴:
- DuckDB/SQLite をローカル DB に使い、分析と運用ログを分離
- .env による環境変数管理と自動読み込み（プロジェクトルートが見つかれば .env/.env.local を読み込み）
- Paper Trading（KABUSYS_ENV=paper_trading）の際は本番 DB と分離して paper_trading DB を利用
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定をサポート（API キー必須）
- フェイルセーフ（API失敗時のフォールバック、DB マイグレーション、冪等な書き込み）

---

## 主な機能一覧

- config_setup.py
  - 対話式で .env を生成 / 更新するウィザード
- validate_config.py
  - .env と config/*.yaml の設定検証（--strict オプションあり）
- run_execution.py
  - ExecutionEngine を起動（本番／ペーパートレードの切替、PID ファイル管理、停止フラグ対応）
- run_monitoring.py
  - SystemMonitor をポーリング実行（MONITOR_POLL_INTERVAL で間隔変更可）
- monitoring/*
  - MonitoringDB（SQLite）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager など
- portfolio/*
  - 候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数など純粋関数群
- research/*
  - ファクター計算（momentum/volatility/value）、forward returns、IC、統計サマリ
- ai/*
  - news_nlp (ニュースセンチメント → ai_scores)、regime_detector（マクロ + ETF MA によるレジーム判定）
- tools/paper_verification_report.py
  - ペーパートレード DB を解析して Pass/Fail 判定を出すレポート生成

---

## セットアップ手順

以下はローカル開発 / 実行のための手順例です。

1. Python 環境を用意（推奨: 3.10+）
   - 仮想環境を作ることを推奨します:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要な Python パッケージをインストール
   - 本コードで参照される主なパッケージ:
     - duckdb, psutil, openai, PyYAML（オプション: config の YAML 検証用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt は本リポジトリに含まれていないため、プロジェクトで必要な追加パッケージがあれば都度インストールしてください。

3. .env を用意
   - 対話式ウィザードを実行して .env を生成:
     - python -m kabusys.config_setup
   - または手動で .env を作成してください（以下は主要な環境変数の例）:

     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_password_here
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=（AI を使う場合に設定）

   - 注意:
     - .env は Git にコミットしないでください（config_setup もヘッダーで警告を出しています）。
     - 自動ロードはプロジェクトルートの検出が成功した場合に .env / .env.local を読み込みます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います:
     - python -m kabusys.validate_config --strict

5. 初回ディレクトリ作成
   - data/ や logs/ は自動作成されることが多いですが、パーミッションの確認は行ってください。

---

## 使い方（主要コマンド）

- 実行エンジン（ExecutionEngine）を起動
  - デフォルト（env に応じて paper_trading なら専用 DB を使用）:
    - python -m kabusys.run_execution
  - 実行中は data/execution.pid を生成し、停止は data/stop_requested.flag を作成して促します（または KillSwitch が data/kill.flag を書き込む場合があります）。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き（秒）。例: MONITOR_POLL_INTERVAL=30

  - 監視は SystemMonitor（CPU/MEM/DISK、データ鮮度、Execution プロセスの有無）や RiskMonitor、TradeMonitor を呼び出します。
  - Monitoring では Settings.env にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します。

- .env の生成・更新（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニュース NLP / レジーム判定）
  - ai.news_nlp.score_news、ai.regime_detector.score_regime をプログラムから呼び出し可能
  - 環境変数 OPENAI_API_KEY を必ず設定してください。API 失敗時にフォールバック・リトライロジックがあります。

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）

- データベース / ファイル
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite（監視 DB）（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch 用フラグファイル（デフォルト: data/kill.flag）

- ログ / 実行制御
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR — ログ保存先（デフォルト: logs/）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - KILL_FLAG_CLEAR_ON_START — 本番での自動 kill flag クリア制御（0/1）

- Paper Trading 固有
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）
  - KABUSYS_ENV=paper_trading の時、MockBrokerClient を使用し paper_trading.db に記録します（本番 DB と完全分離）。

- AI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で必要）

---

## 運用上のファイル / フラグ

- data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルの存在を見て安全にループを抜けます（外部から停止を促すためのフラグ）。
- data/kill.flag
  - KillSwitch が書き込むと ExecutionEngine に停止シグナルを与えます（設定で上書き可）。
- data/execution.pid
  - run_execution が PID を書き込みます。
- data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb
  - それぞれ SQLite / DuckDB のデフォルトパスです。
- logs/<app_name>.log
  - 日次ローテートされるログファイル（TimedRotatingFileHandler）。logs ディレクトリが作れない場合はコンソール出力のみになります。

---

## 開発者向けメモ

- ログ設定: kabusys.utils.logging_setup.setup_logging を起動時に呼ぶことで、アプリケーション全体で統一されたログ出力を行います（stdout と日次ファイル）。
- プロセス優先度: run_execution / run_monitoring は起動時に set_process_priority("high") を呼びます（psutil に依存、権限不足時は警告）。
- DB 初期化: monitoring_db.init_monitoring_db は冪等にテーブル・インデックスを作成し、必要に応じて簡易マイグレーション（カラム追加）を行います。
- テスト: 多くの関数は副作用がなく純粋関数（portfolio/*, research/*）として実装されているため単体テストが容易です。AI 呼び出しはラップ関数をモックすることでテスト可能です。

---

## ディレクトリ構成

以下はソースルート（src/kabusys）の主要ファイル／ディレクトリ一覧（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - data/                 (データ関連実装は別ディレクトリ想定)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (参照される想定)
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py

（上記は主要ファイルを抜粋した構成です。実際のファイル数やサブモジュールはリポジトリ内を参照してください。）

---

## よくある質問（FAQ）

Q: Paper Trading と Live はどう切り替える？
- KABUSYS_ENV を `paper_trading` に設定すると、run_execution は MockBrokerClient を使い paper_trading 用 SQLite に記録します。本番 DB と分離されます。

Q: 監視プロセスのポーリング間隔を短くしたい
- 環境変数 MONITOR_POLL_INTERVAL を秒数で指定してください（例: MONITOR_POLL_INTERVAL=30）。不正な値や 0 以下の場合はデフォルトの 60 秒にフォールバックします。

Q: AI 機能を使うには？
- OPENAI_API_KEY を環境変数に設定してください。news_nlp/regime_detector は OpenAI の応答に対する堅牢な検証とリトライを実装していますが、API使用量に注意してください。

---

以上が README の概要です。必要であれば、インストール用の requirements.txt や運用の runbook、コンテナ化（Dockerfile / docker-compose）手順、ユニットテスト／CI 設定例等を追加で作成できます。希望があれば教えてください。