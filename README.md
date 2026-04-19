# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群です。  
本リポジトリは、注文エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、研究用ファクター計算、AI（ニュース NLP / レジーム判定）などのモジュールで構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤を意図したモジュール群です。主要な機能は次のとおりです。

- 実行エンジン（ExecutionEngine）による注文管理・発注（本番・ペーパートレード対応）
- システム監視（CPU / メモリ / ディスク / プロセス / データ鮮度）
- リスク監視（ドローダウン / 保有上限など）と Kill Switch（停止フラグ）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算）
- 研究モジュール（ファクター計算・特徴量探索）
- AI モジュール（ニュースを LLM でスコアリング、レジーム判定）
- CLI ツール（.env ウィザード、設定検証、Paper Trading レポート）
- 統一的なロギング / プロセス優先度設定ユーティリティ

設計方針として、データ永続化は DuckDB（時系列・研究用）と SQLite（監視・発注ログ）を使い分け、OpenAI 等の外部 API 呼び出しは明示的に環境変数でキーを与える方式です。

---

## 機能一覧（抜粋）

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、専用の paper_trading DB に記録
- run_monitoring.py
  - SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL 環境変数で間隔変更可）
  - 停止フラグ（data/stop_requested.flag）検出で安全終了
- monitoring/*
  - MonitoringDB: SQLite ベースの監視ログ永続化
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine
- portfolio/*
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクター上限適用、レジーム乗数
- research/*
  - ファクター計算（モメンタム/ボラティリティ/バリュー）、将来リターン、IC 計算、統計サマリー
- ai/*
  - news_nlp: OpenAI を用いたニュースのセンチメントスコアリング（ai_scores へ保存）
  - regime_detector: MA とマクロニュースで日次レジーム判定
- tools/paper_verification_report.py
  - ペーパートレード DB から検証レポートを生成（稼働率・約定率・レイテンシ等）
- config_setup.py / validate_config.py
  - .env の対話式作成・更新ウィザード
  - 起動前の設定検証 CLI

---

## 前提 / 必要環境

- Python 3.10+
- 必要な Python パッケージ（主なもの）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config の YAML 検証を行う場合、必須ではない）
- SQLite（Python 標準ライブラリ sqlite3 を使用）
- ネットワーク接続（本番で外部サービスを使う場合）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```
※ 実際のプロジェクトでは requirements.txt を用意して pip install -r で揃えてください。

---

## セットアップ手順

1. リポジトリをクローン、またはソースを配置
2. Python 仮想環境を作成して依存パッケージをインストール（上記参照）
3. データ・ログ用ディレクトリ作成（必要に応じて）
   - デフォルト DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
     - SQLite (monitoring): data/monitoring.db（SQLITE_PATH）
     - Paper Trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログディレクトリ: logs/（LOG_DIR 環境変数で変更可）
4. .env の作成（対話式ウィザード推奨）
   - 実行:
     - python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト development
     - OPENAI_API_KEY（AI 機能を使う場合）
   - サンプル（.env）:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_jquants_token_here
     KABU_API_PASSWORD=your_kabu_password_here
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     ```
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いにできます

---

## 使い方

各種スクリプトはパッケージモジュールとして実行できます。

- ExecutionEngine を起動（本番 / ペーパートレード）
  - 本番（KABUSYS_ENV=live 等の適切な .env を設定）
    ```bash
    python -m kabusys.run_execution
    ```
  - ペーパートレード（.env で KABUSYS_ENV=paper_trading を設定）
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 補足:
    - paper_trading の場合、MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 停止:
    - data/stop_requested.flag を作成すると監視ループは検出して終了します。

- .env ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB 指定:
    ```bash
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```

- AI / 研究モジュールの利用（ライブラリ呼び出し）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    - 引数に DuckDB 接続と target_date, api_key を与えて呼び出す
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
  - ファクター計算:
    from kabusys.research import calc_momentum, calc_volatility, calc_value, ...

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant / partial / never / reject）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（デフォルト 60）

---

## 停止 / Kill Switch

- run_execution / run_monitoring はプロセス内で data/stop_requested.flag（またはプロジェクトルートの data/stop_requested.flag）を監視して、安全にループを抜けます。
- KillSwitch は条件（ドローダウン超過、ポジション上限超過等）に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- 実運用では KILL_FLAG_CLEAR_ON_START の設定値に注意してください（本番で自動クリアは危険）。

---

## ログ

- ログ設定は kabusys.utils.logging_setup.setup_logging を通して統一されています。
- デフォルトは stdout（コンソール）と logs/<app_name>.log（日次ローテート、30日保持）です。
- LOG_DIR 環境変数や setup_logging の引数で変更可能です。

---

## ディレクトリ構成

（リポジトリルートに src/kabusys 配下がある想定）

- src/kabusys/
  - __init__.py
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - config.py                      — 環境変数 / 設定読み込みロジック（Settings）
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py              — （存在を想定、抜粋コードでは未表示）
    - kill_switch.py
    - alert_manager.py              — （存在を想定、抜粋コードでは未表示）
  - execution/                      — ExecutionEngine 周辺（OrderManager 等。抜粋）
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
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/                           — データファイル（data/*.db, *.flag, *.pid）
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

（実際のリポジトリでは上記に加えて execution や monitoring の完全な実装ファイルが存在します）

---

## 開発メモ / 注意事項

- Settings（config.py）は自動的にプロジェクトルートの .env / .env.local をロードしますが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。
- research / ai モジュールは外部 API や DuckDB を前提とするため、テスト時はモックして使うことを推奨します（各モジュールにテスト用フックあり）。
- DuckDB の SQL 実行はパフォーマンス上の考慮（窓関数や範囲限定）を行っています。大規模データを扱う場合はメモリやクエリ計画に注意してください。
- run_execution のリスク設定やレートリミット等は ExecutionEngine の設定で調整できます（リファレンスは該当ファイル内コメント参照）。

---

必要があれば、README に「運用手順」「Dockerfile / systemd サービス例」「サンプル .env の完全版」などを追加します。どの情報がさらに欲しいか教えてください。