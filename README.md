# KabuSys

日本株向け自動売買システム（ライブラリ & 起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注（実環境/ペーパートレード）・監視・研究用ユーティリティを含むモジュール群です。  
ここに記載する README はコードベース（src/kabusys 以下）の使用方法、設定、ディレクトリ構成の概要をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つ自動売買プラットフォームのコンポーネント群です。

- シグナル（ファクター）計算および研究用ツール（DuckDB を利用）
- ポートフォリオ構築（候補選定・重み計算・セクター制約・ポジションサイズ）
- ExecutionEngine（発注エンジン）：実口座／ペーパートレード対応（環境によりブローカークライアントを切り替え）
- 監視システム（System / Trade / Risk のモニタリング、Kill Switch）
- AI モジュール（OpenAI を用いたニュースセンチメント／レジーム判定）
- 運用ユーティリティ（.env 設定ウィザード、設定検証、ペーパートレード検証レポート）

主要な永続化は以下のファイルに行われます（デフォルト）:
- DuckDB: data/kabusys.duckdb
- SQLite（監視用）: data/monitoring.db
- ペーパートレード用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時）

---

## 機能一覧（抜粋）

- 環境変数管理: kabusys.config（.env/.env.local の自動読み込み、Settings クラス提供）
- .env ウィザード: kabusys.config_setup（対話式で .env を作成／更新）
- 設定検証: kabusys.validate_config（起動前に環境変数・config/*.yaml の健全性をチェック）
- 発注エンジン起動: run_execution.py（KABUSYS_ENV により本番／ペーパートレード切替）
- 監視ループ起動: run_monitoring.py（SystemMonitor の定期実行）
- 監視永続層: monitoring.monitoring_db（SQLite ベースのテーブル初期化・CRUD）
- 各種モニタ: system_monitor, trade_monitor, risk_monitor、KillSwitch、AlertManager（通知は設定次第）
- ポートフォリオ: portfolio.{portfolio_builder, position_sizing, risk_adjustment}
- 研究・ファクター計算: research.{factor_research, feature_exploration}
- AI: ai.news_nlp（ニュースセンチメント）, ai.regime_detector（市場レジーム判定）
- ユーティリティ: utils.logging_setup（統一ログ設定）, utils.process_priority（優先度設定）
- ツール: tools.paper_verification_report（ペーパートレード検証レポート生成）

---

## 前提 / 依存パッケージ

主な外部依存（必須／推奨）:

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を使う場合）

インストール例:
```
pip install duckdb psutil openai PyYAML
```
（プロジェクトに requirements.txt があればそれを使ってください）

---

## セットアップ手順

1. リポジトリをクローン / checkout

2. Python 仮想環境を用意して依存をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # ある場合
   # または
   pip install duckdb psutil openai PyYAML
   ```

3. 対話式で .env を作成（推奨）
   ```
   python -m kabusys.config_setup
   ```
   このウィザードは .env を生成／更新します。重要シークレット（API トークン等）はマスクされます。生成後に `python -m kabusys.validate_config` で検証してください。

4. DB / ディレクトリの初期準備
   - 多くのスクリプトは起動時に必要なディレクトリを自動で作成しますが、念のため `data/` と `logs/` を作成しておくとよいです。
   ```
   mkdir -p data logs
   ```

5. 環境変数（例）
   - .env を使わない場合は環境変数で指定できます。主な変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（例: INFO）
     - LOG_DIR（ログ出力先、デフォルト: logs/）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト: 60）

---

## 使い方

※ リポジトリ直下で実行することを想定しています（.env 自動読み込みはプロジェクトルート検出に依存）

- .env の作成（推奨）
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- 実行エンジン（ExecutionEngine）起動
  - 本番（実ブローカー） / 開発は KABUSYS_ENV に依存:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。本番 DB とは分離されます。
  ```
  # 直接起動
  python -m kabusys.run_execution

  # 例: ペーパートレードを明示
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  - 起動時に data/execution.pid（デフォルト）へ PID を書きます。停止指示は data/stop_requested.flag を作成することで行えます。

- 監視ループ起動
  ```
  # デフォルトのポーリング間隔は 60 秒。環境変数で上書き可。
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は Settings.sqlite_path（monitoring DB）に接続します（監視は常に本番 sqlite_path を使用）。
  - 停止はプロジェクトルートの data/stop_requested.flag（ファイル作成）で行います。

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  # 厳格モード（警告も失敗扱い）
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート（ツール）
  ```
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーを環境変数にセット
  ```
  export OPENAI_API_KEY="sk-..."
  ```
  - モジュールを呼び出してプログラム内から利用する（例）
  ```
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date, api_key=None)  # api_key=None -> 環境変数を参照
  ```

- ログ設定
  - 全スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出して統一されたログ出力を行います。LOG_DIR / LOG_LEVEL を .env で設定可能です（デフォルト: logs/、INFO）。

---

## 運用上のファイル / フラグ

- data/stop_requested.flag
  - run_monitoring / run_execution が監視している停止フラグ（存在したらループを止める）
- data/kill.flag
  - KillSwitch により ExecutionEngine の強制停止指示（Execution 側が監視して処理する）
- data/execution.pid
  - 実行エンジンの PID 保存先（デフォルト）
- SQLite / DuckDB ファイル
  - data/monitoring.db（監視用 SQLite）
  - data/paper_trading.db（ペーパートレード用、KABUSYS_ENV=paper_trading 時に使用）
  - data/kabusys.duckdb（分析用 DuckDB）

---

## 主要モジュール概要（簡易）

- kabusys.config
  - .env 自動読込ロジック、Settings クラスを提供。KABUSYS_ENV の値や DB パス等を取得。
- kabusys.config_setup
  - .env の対話式生成／更新ウィザード。
- kabusys.validate_config
  - 起動前の環境設定検証 CLI。
- kabusys.run_execution
  - ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading のときは MockBroker を使い DB を隔離。
- kabusys.run_monitoring
  - SystemMonitor をポーリングする起動スクリプト。MONITOR_POLL_INTERVAL で間隔設定可。
- kabusys.monitoring.*
  - MonitoringDB（SQLite スキーマ初期化、CRUD）、SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine / AlertManager 等。
- kabusys.execution.*
  - 実際の発注ロジック（Engine、OrderManager、RiskManager など）。（この README では概観のみ）
- kabusys.portfolio.*
  - 候補選定、重み計算、ポジションサイズ決定、セクター制約などの純粋関数群。
- kabusys.research.*
  - DuckDB を用いたファクタ計算・統計・IC 解析など研究用途の関数群。
- kabusys.ai.*
  - OpenAI を用いたニュースセンチメント（news_nlp）とレジーム検出（regime_detector）。

---

## よくある運用注意点

- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup でも注意喚起あり）。
- KABUSYS_ENV の値により挙動が大きく変わります。特に `live` は本番発注を行うため設定と権限を厳密に確認してください。
- モニタリング（監視）は監視 DB（SQLITE_PATH）を使いますが、ExecutionEngine の DB（ペーパートレード／本番）とは別にすることを推奨します（コードもその前提で分離）。
- AI 機能を使う場合は OPENAI_API_KEY を設定してください。API の失敗はフェイルセーフでスコア 0 等にフォールバックする実装が多いですが、呼び出し側でのログ確認を推奨します。
- process priority / CPU affinity の設定は OS 権限、プラットフォームにより失敗することがあります（警告ログが出ます）。

---

## ディレクトリ構成

（src/kabusys 以下を示します）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py  (実装がある想定)
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - data/ (ランタイム生成想定)
  - logs/ (ランタイム生成想定)

（コードの一部は上記ファイルに依存しており、実際のリポジトリではさらに詳細なモジュールとサブパッケージが存在します）

---

## トラブルシューティング / デバッグのヒント

- ログが出ない場合:
  - LOG_DIR の書き込み権限を確認（logs/ ディレクトリの生成に失敗するとファイルハンドラは無効化されます）。
  - LOG_LEVEL を DEBUG に設定して詳細ログを確認。
- DB の初期化に失敗する場合:
  - sqlite / duckdb のファイルパスと親ディレクトリの存在・書き込み権限を確認。
- OpenAI API 呼び出し失敗:
  - OPENAI_API_KEY が正しいか、ネットワーク疎通、rate limit、タイムアウトを確認。リトライロジックは実装されていますが、鍵が無効な場合は即失敗します。
- 強制停止 / キルスイッチ:
  - 運用側で kill.flag（Settings.kill_flag_path）を操作することで Execution を停止させる設計になっています。KillSwitch の判定条件は RiskMonitor などに依存します。

---

README は以上です。必要であれば以下を追加で用意できます：
- 主要 CLI のサンプル systemd / supervisor ユニットファイル
- Docker 化手順（Dockerfile / docker-compose）
- 詳細なモジュール間アーキテクチャ図
- API（BrokerClient）仕様書

どれを追加しますか？