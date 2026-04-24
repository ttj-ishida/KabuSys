# KabuSys

日本株向け自動売買システムの一部実装。ポートフォリオ構築、注文実行エンジン、監視・アラート、リサーチ（ファクター計算）、ニュース NLP（LLM）によるセンチメント評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能群を持つモジュール化されたシステムです。

- 実行（ExecutionEngine）: 注文発行・注文管理・リスク管理を行う実行エンジン（`run_execution.py` 起動スクリプト）。
- 監視（Monitoring）: システム状態、注文ログ、リスク（ドローダウン・保有数）を定期的にチェックし、必要に応じて Kill Switch を発動する（`run_monitoring.py` 起動スクリプト）。
- ポートフォリオ構築: 銘柄選定、重み計算、ポジションサイズ計算、セクター制限などの純粋関数群（`kabusys.portfolio`）。
- リサーチ: DuckDB ベースでファクター計算・特徴量探索を行う（`kabusys.research`）。
- AI（ニュース NLP / レジーム検知）: OpenAI を利用したニュースセンチメントスコアリングや市場レジーム判定（`kabusys.ai`）。
- ユーティリティ: ロギング設定、プロセス優先度設定、設定読み込みウィザード・検証ツールなど。

設計上、データベースは DuckDB（分析用）と SQLite（監視・発注ログ等）を併用します。Paper Trading モードでは本番 DB と分離された専用 SQLite を使用します。

---

## 主な機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution: ExecutionEngine を起動
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `data/paper_trading.db` を利用
  - python -m kabusys.run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可能）

- 設定操作
  - 対話式 .env 作成: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config (--strict オプションあり)

- 監視
  - system_status / trade_logs / positions / risk_logs / dashboard の永続化（SQLite）
  - Kill Switch: 条件（ドローダウンやポジション数超過）で `data/kill.flag` を書き込み ExecutionEngine に停止シグナルを送信
  - 監視エンジン: 各種アラート管理（AlertManager 経由で通知）

- ポートフォリオ
  - 候補選定・スコアベース/等配分の重み付け
  - ポジションサイズ計算（単元株丸め、aggregate cap スケールダウン）
  - セクター集中制限、レジーム乗数適用

- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 利用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI
  - ニュースの銘柄ごとのセンチメントスコア化（OpenAI）
  - 市場レジーム判定（ETF MA + マクロニュースセンチメントの混合）

- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順（例）

1. リポジトリをクローンして作業ディレクトリに移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストール
   - 本リポジトリに requirements.txt がない場合は以下を最低限インストールしてください:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証に任意）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. .env を作成（推奨: 対話式ウィザードを利用）
   ```
   python -m kabusys.config_setup
   ```
   - 対話ウィザードで J-Quants トークン、kabu API パスワード、DB パスや環境（KABUSYS_ENV）などを設定します。
   - 生成される .env は絶対に Git にコミットしないでください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も厳格に扱う場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリの準備（必要に応じて）
   - デフォルトのデータパス: `data/kabusys.duckdb`, `data/monitoring.db`, `data/paper_trading.db`
   - ログは `logs/` に日次ローテートで出力されます（設定: LOG_DIR / LOG_LEVEL）

注意:
- 自動で .env を読み込む処理が動作します（プロジェクトルートの .env / .env.local）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI を使う機能は環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時に `api_key` を渡してください。

---

## 使い方（代表的なコマンド）

- ExecutionEngine を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用して `data/paper_trading.db` に記録します。
  - `_STOP_FLAG`（data/stop_requested.flag）が存在すると起動を停止します。
  - 実行時に PID ファイル `data/execution.pid` を生成します。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は環境にかかわらず本番の sqlite_path (`Settings.sqlite_path`) を使用する点に注意。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート（ローカル実行）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を直接指定する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- プログラムからの利用例（Python インポート）
  - ニューススコアリング:
    ```py
    from kabusys.ai.news_nlp import score_news
    # DuckDB 接続を渡して呼ぶ
    score_news(conn, target_date, api_key="...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")
    ```

---

## 主要な環境変数

- 必須（運用に応じて設定）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境／挙動
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - LOG_DIR: ログ出力ディレクトリ（デフォルト `logs/`）
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）

- データベース関連
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
  - SQLITE_PATH: SQLite 監視 DB（デフォルト `data/monitoring.db`）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト `data/paper_trading.db`）
  - PAPER_FILL_MODE: paper_trading 時の MockBroker の約定モード（instant | partial | never | reject）

- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で利用）

- 監視関連
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト `data/execution.pid`）
  - KILL_FLAG_PATH: Kill Switch のフラグファイル（デフォルト `data/kill.flag`）

その他、`config_setup` に示されている項目を参照してください。

---

## 注意事項 / 実装上の挙動メモ

- run_monitoring は設定に関わらず `Settings.sqlite_path`（本番監視 DB）を使います。環境に依らず監視用 DB を統一したい設計。
- run_execution は KABUSYS_ENV=paper_trading のとき `Settings.paper_sqlite_path` を使い、本番 DB と分離します。
- Kill Switch はファイルベース（`data/kill.flag`）で ExecutionEngine に停止を要求します。監視側が条件満たすと flag を書き込みます。
- Logs: `kabusys.utils.logging_setup.setup_logging` により stdout と日次ローテートファイル（logs/<app>.log）に出力します。ログディレクトリ作成に失敗した場合はコンソールのみの出力になります。
- プロセス優先度設定（set_process_priority）は OS に依存し、権限がない場合は警告を出してスキップします（psutil を使用）。
- .env 自動読み込み: プロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動で読み込みます。自動ロード無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py               # 環境変数と Settings クラス
    - config_setup.py         # .env 対話式ウィザード
    - validate_config.py      # 設定検証 CLI
    - run_execution.py        # ExecutionEngine 起動スクリプト
    - run_monitoring.py       # SystemMonitor 起動スクリプト
    - ai/
      - news_nlp.py           # ニュース NLP（OpenAI）スコアリング
      - regime_detector.py    # 市場レジーム判定
      - __init__.py
    - monitoring/
      - monitoring_db.py      # SQLite 永続化層（schema 作成・読み書き）
      - system_monitor.py
      - trade_monitor.py      # （参照されるがファイルはここにある想定）
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py      # （参照されるがファイルはここにある想定）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （存在しない場合は生成スクリプト等で用意）

- data/
  - monitoring.db (デフォルト SQLite)
  - paper_trading.db (paper_trading 用)
  - kabusys.duckdb (DuckDB)
  - kill.flag, stop_requested.flag, execution.pid（ランタイムで使用）

---

## よくある運用コマンド・例

- 本番想定で実行（事前に .env で KABUSYS_ENV=live 設定）
  ```
  python -m kabusys.run_monitoring
  python -m kabusys.run_execution
  ```

- ペーパートレード（分離 DB を使用）
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- 監視のポーリング間隔を 30 秒に変更して起動
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- 強制停止シグナル（監視/外部ツールから ExecutionEngine を停止させたいとき）
  ```
  echo "reason..." > data/kill.flag
  ```

---

必要に応じて README を拡張して、実行時のログ例、DB スキーマ説明、BrokerClient の実装ドキュメントやテスト手順を追加してください。README の改善点や追記したい項目があれば指示してください。