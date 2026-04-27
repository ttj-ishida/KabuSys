# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株向けの自動売買システム KabuSys の一部実装です。  
この README ではプロジェクト概要、主な機能、セットアップ手順、使い方（起動コマンド例）、および主要なディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の処理群を備えたシステムです。

- データ収集・前処理（DuckDB を利用）
- ファクター計算・リサーチ（momentum / value / volatility 等）
- ポートフォリオ構築（候補選定、重み付け、リスク調整）
- 発注エンジン（本番 / ペーパートレードを選択可能）
- 実行前チェック（Pre-Market Report）および起動時サマリ
- 監視（SystemMonitor の定期ポーリング）
- 各種レポート生成 / 検証ツール（ペーパートレード検証など）
- ニュース NLP による AI スコアリング（OpenAI を利用）

設計方針として、可能な限り副作用を分離した純粋関数群や、環境変数中心の設定管理、そして運用上の安全ガード（stop フラグ・PID 管理・リスク制限）を重視しています。

---

## 機能一覧（抜粋）

- 環境設定ウィザード（config_setup）
- 設定検証 CLI（validate_config）
- Execution エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を用い、data/paper_trading.db に記録して本番 DB と分離
- 監視ループ起動スクリプト（run_monitoring）
  - 環境に関係なく本番 sqlite_path を監視用 DB として使用
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能
- Pre-Market レポート生成（run_pre_market_report / operations.pre_market_*）
- 夜間バッチ / Execution Startup サマリ生成（operations.night_batch_report, execution_startup_report）
- ポートフォリオ構築ユーティリティ（portfolio パッケージ）
- ペーパートレード用検証レポート（tools/paper_verification_report）
- ニュース NLP による ai_scores 更新（ai/news_nlp） — OpenAI API を使用
- ロギング・プロセス優先度ユーティリティ（utils.logging_setup / utils.process_priority）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンして作業ディレクトリへ移動します。
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成して有効化します（任意）。
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストールします（例）。
   - DuckDB, PyYAML, psutil, openai（ai/news_nlp を使う場合）
   ```
   pip install -r requirements.txt
   ```
   requirements.txt がない場合は最低限次のパッケージを用意してください：
   - duckdb
   - pyyaml
   - psutil
   - openai (ai/news_nlp を使う場合)

4. 初期設定ファイル（.env）を作成します。対話ウィザードを使うと簡単です：
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成・更新します。生成後、設定内容を必ず確認してください。

5. 設定を検証します：
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. 必要な設定ファイル（config/*.yaml）があることを確認してください。リポジトリに含まれていない場合は `scripts/generate_config.py` 等で生成する設計になっている箇所があります（validate_config のメッセージ参照）。

---

## 重要な環境変数（抜粋）

（.env へ設定する、もしくは環境変数で指定）

- 必須（少なくとも設定しておくこと）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用関連
  - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH : DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : ペーパートレード用 SQLite（paper_trading 環境で使用）
  - PAPER_FILL_MODE : ペーパートレードの約定挙動（instant|partial|never|reject）
  - OPENAI_API_KEY : ai/news_nlp を利用する場合に必要

- 監視・プロセス
  - MONITOR_POLL_INTERVAL : 監視ポーリング秒間隔（run_monitoring、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START : 本番での kill flag 自動クリア（0 推奨）
  - LOG_DIR : ログ保存先ディレクトリ（デフォルト logs/）

その他、README 内の「セットアップ手順」や config_setup の案内に従って .env を作成してください。

---

## 使い方（主要コマンド例）

プロジェクトはモジュールとして起動する想定のスクリプトが複数あります。いくつかの典型的な起動例を示します。

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution エンジン起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - 実行中は data/execution.pid に PID、停止は data/stop_requested.flag を作成することで受付（スクリプトは stop フラグを監視して終了します）。

- 監視プロセス起動（SystemMonitor のポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（デフォルト 60）。
  - 監視は本番 sqlite_path を使用（環境にかかわらず本番 DB 参照）。

- Pre-Market Report（CLI）
  ```
  python -m kabusys.run_pre_market_report
  python -m kabusys.run_pre_market_report --save    # artifacts/pre_market/ に保存
  python -m kabusys.run_pre_market_report --json    # JSON を stdout に出力
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- ai/news_nlp（ニュース NLP：モジュール呼び出し）
  - OpenAI API を使用するため `OPENAI_API_KEY` を設定する必要があります。
  - 実際の呼び出しはモジュール関数経由（例: kabusys.ai.news_nlp.score_news）で行います。CLI ラッパーは含まれていません（実装で呼び出してください）。

停止 / 管理関連:
- 停止フラグ（全スクリプト共通）: プロジェクトルートの data/stop_requested.flag を作成すると監視/実行ループが検出して安全終了します。
- PID ファイル: data/execution.pid（Execution エンジン）など、各プロセスが PID を出力します。
- kill フラグ（KILL スイッチ）: Settings.kill_flag_path などの設定に依存します。運用時は KILL_FLAG_CLEAR_ON_START を誤って 1 にしないでください（本番危険）。

---

## よく使うファイル・ディレクトリ

- .env — 環境変数設定ファイル（生成は config_setup により対話式）
- config/ — YAML 設定群（risk_config.yaml 等）
  - config/risk_config.yaml — Execution のリスク関連設定（max_position_pct 等）
- data/ — SQLite / 各種フラグ / PID 等（デフォルトの DB もここに置かれます）
  - data/monitoring.db — 監視用 SQLite（デフォルト）
  - data/paper_trading.db — (paper_trading 用)
  - data/stop_requested.flag — 停止フラグ
  - data/execution.pid — PID ファイル（Execution）
- logs/ — ログ出力（TimedRotatingFileHandler 日次ローテート）
  - logs/execution.log, logs/monitoring.log など
- artifacts/ — レポート保存先（pre_market / night_batch / execution_startup）
- src/kabusys/ — 実装本体
  - config.py — 環境変数と設定ロードロジック（.env 自動読み込み含む）
  - run_execution.py, run_monitoring.py, run_pre_market_report.py — 起動スクリプト
  - operations/ — レポート・収集モジュール（pre_market_*、execution_startup_report 等）
  - portfolio/ — ポートフォリオ構築ロジック（選定・重み・サイズ計算）
  - research/ — ファクター計算・特徴量探索
  - ai/ — OpenAI を使ったニュース NLP
  - utils/ — logging_setup, process_priority 等ユーティリティ
  - tools/ — ペーパートレード検証などユーティリティスクリプト

（プロジェクトルートの `pyproject.toml` / `.git` を基準に自動でルートを検出する実装が config._find_project_root にあります）

---

## 運用上の注意点

- 本番環境（KABUSYS_ENV=live）では LINE 通知トークンや各種設定を確実に設定し、`validate_config` の結果や警告を必ず確認してください。
- run_execution は起動時にリコンシリエーション（Reconciler.run）を実行し、ExecutionStartupReport を生成します。`orders_no_status > 0` の場合は BLOCKED（手動確認が必要）になります。
- risk_config.yaml は内容チェックが厳密です。`max_position_pct`、`max_utilization`、`max_drawdown` などは (0, 1] の範囲である必要があります。設定ファイルが欠落している場合は `git checkout config/risk_config.yaml` で復元する旨のログが出ます。
- ペーパートレードは実際の発注を行わない代わりに mock 実装へ振り分け、データは paper_trading 用 DB に分離されます（本番 DB に影響を与えません）。
- ログの保存先ディレクトリ作成に失敗した場合、ログはコンソール出力のみで継続します（ファイル出力はスキップされます）。
- process priority / CPU affinity の設定はプラットフォームに依存します。psutil による権限不足時は警告を出してスキップします。

---

## 開発者向けメモ・ヒント

- unit tests や CI で自動的に .env の自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（config.py の自動ロードをスキップします）。
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書きできます。0 や負の値は無効でデフォルト 60 秒にフォールバックします。
- DuckDB / SQLite は読み取り専用で接続する箇所と書き込みを行う箇所があるため、DB パスやファイルロックに注意してください（特に複数プロセスで同一ファイルを扱う運用）。
- ai/news_nlp は OpenAI のエラー（RateLimit, 5xx 等）に対して指数バックオフ実装が施されていますが、API キーの管理や利用制限には注意してください。

---

## ディレクトリ構成（主要部分）

下記は主要ファイル・ディレクトリの抜粋（src/kabusys 以下）です：

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - run_pre_market_report.py
    - operations/
      - pre_market_collector.py
      - pre_market_report.py
      - execution_startup_report.py
      - night_batch_report.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - execution/           # 発注エンジン関連（OrderManager, Broker, Reconciler 等）
      - ... (実装ファイル群)
    - monitoring/          # 監視 DB 初期化や SystemMonitor 実装
      - ... (実装ファイル群)
    - ai/
      - news_nlp.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py

プロジェクトルートには data/, logs/, artifacts/ 等が生成されます。

---

## 最後に

この README はリポジトリに含まれるコード（起動スクリプト、設定管理、レポート・ユーティリティ）を元にまとめた概要です。実際の運用では `.env` や `config/*.yaml` の中身、外部 API キー、DB パスなどを適切に設定した上で、まず `python -m kabusys.validate_config` を実行して構成の整合性を確認してください。

不明点や追加したいドキュメント項目があれば教えてください。README の追補やサンプル .env のテンプレート作成も対応します。