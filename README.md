# KabuSys

日本株向けの自動売買システム（KabuSys）のコードベース用 README。  
このリポジトリは、戦略・ポートフォリオ構築、発注実行（本番／ペーパートレード）、監視、リサーチ、ニュース NLP（OpenAI）などの機能を備えたモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを想定したモジュール式のシステムです。主な役割は以下の通りです：

- データ解析・ファクター計算（DuckDB を用いたバッチ処理）
- ポートフォリオ構築（候補選定・重み計算・株数算出）
- 発注実行エンジン（kabuステーション連携、ペーパートレード対応）
- 監視（システム安定性、注文滞留、リスク指標の監視）と Kill Switch
- ニュースの NLP によるセンチメント計算（OpenAI API）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート など）

設計方針として、外部 API の呼び出し箇所を限定し（例：発注・OpenAI）、多くの計算は DuckDB/SQLite や純粋関数で再現可能にしています。ペーパートレードは本番 DB と分離される設計です。

---

## 主な機能一覧

- config 管理・自動ロード
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 対話式ウィザードで .env を作成する `kabusys.config_setup`
  - 設定検証 CLI `kabusys.validate_config`

- 実行エンジン
  - `run_execution.py`：ExecutionEngine を起動
  - KABUSYS_ENV=paper_trading の際は MockBrokerClient を使用し DB を分離

- 監視・アラート
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動
  - MonitoringDB（SQLite）へのログ永続化
  - Kill Switch（データベースやリスク条件に基づき data/kill.flag にフラグを立てる）

- ポートフォリオ構築
  - 候補選定（スコア順）、等金額／スコア加重配分
  - セクター上限、レジーム乗数、株数算出（単元丸め・aggregate cap）

- リサーチ
  - ファクター計算（Momentum, Volatility, Value など）
  - 将来リターン、IC（Information Coefficient）、統計サマリ

- AI（OpenAI）
  - ニュースを LLM でスコアリング（ai.news_nlp）
  - レジーム判定（ETF MA とマクロニュースの LLM スコアを合成）

- ツール
  - ペーパートレード検証レポート生成（kabusys.tools.paper_verification_report）

- ユーティリティ
  - ロギングセットアップ（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提：
- Python 3.10 以上（型注釈に | を使っています）
- Git クローン済み

1. 仮想環境の作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai
   - 任意: pip install PyYAML （config YAML 検証を行う場合）

   （requirements.txt があればそれを使ってください）

3. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動作成

4. 設定の検証
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ（必要に応じて）
   - デフォルトでは data/ 下に DB・フラグ・PID 等を作成します。必要に応じて DB パス（DUCKDB_PATH, SQLITE_PATH）を .env で変更してください。

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading: 発注はモック、paper_sqlite_path を使用
    - live: 本番運用

- DB / ファイルパス（デフォルト）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag

- ロギング
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - LOG_DIR: デフォルト logs/

- その他
  - OPENAI_API_KEY: ニュース NLP / レジーム判定で必要
  - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

- 自動 env ロードを無効にする
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（起動例）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は paper_trading DB に書き込まれ、本番 DB と分離されます。
    - 起動時に data/stop_requested.flag があると起動を中止します。
    - 実行中は data/execution.pid に PID を書きます。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（0 以下は無効でデフォルト 60）。
  - 監視は常に（KABUSYS_ENV にかかわらず）本番 sqlite_path を参照します（監視 DB は production path を使う設計）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- OpenAI を使うモジュール
  - ai.news_nlp.score_news / ai.regime_detector.score_regime を呼ぶ際は OPENAI_API_KEY を設定するか、api_key 引数を渡してください。

---

## 運用上の注意

- Kill Switch
  - リスク条件（ドローダウン, ポジション上限）を検出すると data/kill.flag を書き込み、Execution 側で停止をトリガーします。
  - 本番環境では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。

- ログ
  - 標準で stdout に出力し、logs/<app_name>.log に日次ローテートで保存します（デフォルト 30日保持）。
  - ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル作成と簡易マイグレーション（カラム追加）を行います。

- パーミッション / 優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼びますが、権限により失敗する場合があります。失敗時は警告ログを出して継続します。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (実装一部)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装想定)
  - execution/
    - execution_engine.py (実装想定)
    - order_manager.py (実装想定)
    - broker_factory.py (実装想定)
  - utils/
    - logging_setup.py
    - process_priority.py

（上は主要ファイルの抜粋。詳細は src/kabusys 以下の各ファイルを参照してください。）

---

## 開発・拡張のヒント

- DuckDB を使っている分析・リサーチ系は、DuckDB の接続を渡してテストデータで検証可能です。
- OpenAI 呼び出し箇所（news_nlp、regime_detector）は内部の API 呼び出し関数をモックしやすい設計です（テスト時は patch して差し替え推奨）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

もし README に追記してほしい情報（例：実際の依存関係リスト、起動時の systemd ユニット例、詳細な API 仕様、ユニットテストの実行方法）があれば教えてください。必要に応じて追補します。