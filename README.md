# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト。  
このリポジトリはトレード実行エンジン、監視・アラート、ポートフォリオ構築、研究用ファクター計算、AI ベースのニュースセンチメント評価などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を持つモジュール群から構成される自動売買基盤です。

- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（システム稼働監視、トレード監視、リスク監視、Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用モジュール（ファクター計算・特徴量解析）
- AI モジュール（OpenAI を用いたニュースセンチメント評価・市場レジーム判定）
- ユーティリティ（設定ロード、ログ設定、プロセス優先度設定）
- CLI ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

設計方針の一部：
- DuckDB / SQLite をデータ層として利用（分析用 DuckDB、監視/取引記録は SQLite）
- Paper Trading は本番 DB と分離（専用 SQLite）
- OpenAI 呼び出しは冪等・フェイルセーフに配慮（リトライ・部分成功保護）
- .env による環境変数管理、.env ウィザード・検証ツールを提供

---

## 主な機能一覧

- run_execution.py: ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
  - プロセス優先度を high に設定し、別スレッドで engine.run_session を実行
  - stop_requested.flag の検知で安全に停止

- run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を設定（デフォルト 60 秒）
  - 監視データは monitoring 用 SQLite（settings.sqlite_path）に永続化（監視は常に本番 sqlite_path を使用）

- monitoring パッケージ
  - SystemMonitor: CPU/メモリ/ディスク・Execution プロセス監視、データ鮮度チェック
  - TradeMonitor: 注文の滞留・約定異常検出（trade_logs テーブル参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ記録
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を止める
  - MonitoringEngine: 各モニタを束ねてポーリング、アラート送出

- portfolio パッケージ
  - 候補選定、等配分/スコア配分、セクター制限、レジーム乗数、ポジションサイズ計算（単元株丸め・aggregate cap）

- research パッケージ
  - ファクター計算（モメンタム／ボラティリティ／バリュー）、将来リターン、IC 計算、統計サマリ

- ai パッケージ
  - news_nlp.score_news: raw_news を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースの LLM センチメントを合成して日次の市場レジーム判定を行う

- utils
  - logging_setup.setup_logging: stdout と日次ローテーションファイルへのロギング設定（logs/<app>.log、30日保持）
  - process_priority.set_process_priority / set_cpu_affinity: Windows/Linux 抽象化でプロセス優先度・CPU affinity を設定

- CLI ツール
  - python -m kabusys.config_setup : .env 初期作成ウィザード（対話式）
  - python -m kabusys.validate_config : .env と config/*.yaml の事前検証
  - python -m kabusys.tools.paper_verification_report : Paper Trading の検証レポート生成

---

## セットアップ手順

1. Python 環境の用意（推奨: 3.10+）
   - 仮想環境を作成して有効化
     ```
     python -m venv .venv
     source .venv/bin/activate  # Linux / macOS
     .venv\Scripts\activate     # Windows
     ```

2. 必要パッケージをインストール
   - 本リポジトリに requirements.txt がない場合は主に次を入れてください:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - PyYAML は config/*.yaml の検証を行う場合に必要です。

3. プロジェクトルートに `data/` と `logs/` を作成（通常は自動作成されますが手動で作ると権限関連で安全）
   ```
   mkdir -p data logs
   ```

4. 環境変数の設定
   - 対話式ウィザードで .env を作成するのが推奨:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（デフォルト値）
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - LOG_LEVEL — default: INFO
     - OPENAI_API_KEY — OpenAI を利用する場合必須（ai.score_news / score_regime）
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒） default: 60

5. 設定検証
   - ウィザード後は設定を検証:
     ```
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict  # 警告を FAIL 扱いにする
     ```

---

## 使い方

- ExecutionEngine を起動（本番 or paper_trading に応じて .env の KABUSYS_ENV を設定）
  - 本番（例）:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 備考:
    - ペーパートレード時は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
    - 起動前に `data/stop_requested.flag` が存在すると起動しません。停止は `data/stop_requested.flag` を作成することで実行中のプロセスに通知します。

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - run_monitoring は監視用に settings.sqlite_path（SQLITE_PATH）を使用します（KABUSYS_ENV にかかわらず本番の sqlite_path を参照する点に注意）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI 関連（スクリプトは提供されているが、関数として利用するのが想定）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と `target_date` を渡して呼び出し、OpenAI API キー（OPENAI_API_KEY）を環境変数または引数で渡します。
  - 例（スクリプトは直接提供されていないため、REPL やカスタムスクリプトから呼び出してください）:
    ```py
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, date(2026, 4, 1), api_key='sk-...')
    ```

- .env 自動読み込み
  - `kabusys.config` はプロジェクトルート（.git または pyproject.toml がある場所）を基準に `.env` と `.env.local` を自動で読み込みます（OS 環境変数を保護）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- Kill / Stop フラグ
  - data/kill.flag : KillSwitch が作成するフラグ。ExecutionEngine はこれを検出して停止します。
  - data/stop_requested.flag : run_monitoring / run_execution の外部停止トリガ（存在を検出するとループを抜ける）

---

## 主要な設定項目（抜粋）

- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABUSYS_ENV — development | paper_trading | live（default: development）
- DUCKDB_PATH — data/kabusys.duckdb（分析用 DB）
- SQLITE_PATH — data/monitoring.db（監視ログ）
- PAPER_TRADING_SQLITE_PATH — data/paper_trading.db（paper_trading 用）
- LOG_LEVEL — INFO（デフォルト）
- OPENAI_API_KEY — AI 機能を利用する場合に設定
- MONITOR_POLL_INTERVAL — 監視間隔（秒、default 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1、default 0）

---

## ログとファイル

- ログ: デフォルト `logs/<app_name>.log`。stdout 出力と日次ローテーション（30 日保持）。
- PID/フラグ:
  - ExecutionEngine の PID: デフォルト `data/execution.pid`（設定で変更可）
  - Kill Switch: `data/kill.flag`
  - 外部停止要求: `data/stop_requested.flag`

---

## ディレクトリ構成（主要ファイル）

（実ファイルは `src/kabusys` 以下に配置）

- kabusys/
  - __init__.py
  - config.py                — .env 自動読み込み / Settings
  - config_setup.py          — .env 対話ウィザード（CLI）
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (※実装参照)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
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

（上記は主要モジュールの一覧です。実際のファイルはプロジェクトを参照してください。）

---

## 動作上の注意と運用メモ

- 監視（run_monitoring）は監視用 SQLite（SQLITE_PATH）を使用します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照するため、テスト時は注意してください。
- Execution の paper_trading モードは本番 DB と分離されます（paper_sqlite_path を使用）。
- OpenAI の呼び出しを行うモジュールは API 失敗に対してリトライやフォールバックを行いますが、API キーの漏洩に注意して .env を管理してください。
- 本番 (KABUSYS_ENV=live) では設定を慎重に確認してください（validate_config にて live 時の追加ワーニングが出ます）。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効になり stdout のみになります。権限やパスに注意してください。

---

以上がプロジェクトの概要・セットアップ・基本的な使い方です。  
必要な追加情報（例: 実行ログのサンプル、詳細な設定例、各モジュールの API 仕様など）があれば教えてください。README を拡張して追記します。