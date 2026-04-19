# KabuSys

日本株向けの自動売買 / 研究フレームワークのコードベースです。  
この README はリポジトリ内の主要モジュールと起動スクリプトをもとに、セットアップ・使い方・構成を日本語でまとめたものです。

※ 本ドキュメントはコードリーディングに基づく説明です。実際の運用前に必ず `python -m kabusys.validate_config` で設定検証を行ってください。

---

## プロジェクト概要

KabuSys は以下の責務を持つ Python モジュール群で構成されたシステムです。

- 市場データ（DuckDB）を用いたファクター計算 / 研究（research）
- ポートフォリオ構成、ポジションサイズ計算（portfolio）
- ExecutionEngine による発注処理（execution）
  - 本番（live）／ペーパートレード（paper_trading）を切替可能
- 実行中システムの監視（monitoring）
  - システムリソース、データ鮮度、注文ログ、リスクルール（ドローダウン等）を監視
  - Kill Switch（フラグファイルによる発注エンジン停止）を実装
- AI 補助（OpenAI を使ったニュースセンチメント・レジーム判定）
- 各種 CLI ユーティリティ（設定ウィザード、設定検証、検証レポート生成 など）
- 共通ユーティリティ（ロギング設定、プロセス優先度設定 等）

設計方針として「実行時にルックアヘッドしない」「フェイルセーフで継続」「DB を環境で分離する（paper_trading 用 DB など）」が意識されています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine（発注エンジン）を起動
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、専用 DB に記録
  - run_monitoring.py: SystemMonitor を定期ポーリングして監視ログを記録
- 設定管理
  - config.py: 環境変数と .env(.env.local) の自動読み込み（プロジェクトルート検出あり）
  - config_setup.py: .env を対話的に生成/更新するウィザード
  - validate_config.py: 起動前に環境変数・設定ファイルの検証を行う CLI
- 監視
  - monitoring/monitoring_db.py: SQLite に監視ログ（system_status, trade_logs, risk_logs, positions, dashboard）を永続化
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py: 各種監視ロジックと集約
  - Kill Switch（kill.flag）による ExecutionEngine 停止シグナル
- 研究・計算
  - research/*: momentum, volatility, value 等のファクター計算、forward returns、IC 計算、統計サマリー
- ポートフォリオ
  - portfolio/*: 候補選定、重み計算、セクター制限、ポジションサイズ決定（lot 単位丸め等）
- AI
  - ai/news_nlp.py: OpenAI を用いたニュースセンチメントスコアリング（ai_scores への書込み）
  - ai/regime_detector.py: MA200 とマクロセンチメントを組み合わせた市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を用いた検証レポート生成

---

## 必要な依存パッケージ（例）

リポジトリに requirements.txt がない場合は少なくとも以下をインストールしてください（バージョンは適宜調整）。

- python >= 3.9
- duckdb
- psutil
- openai
- PyYAML（config 検証時に YAML の解析を行う場合）
- その他（標準ライブラリ以外の外部依存がある場合は追加）

インストール例:

```bash
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン・作業ディレクトリへ移動

2. Python 仮想環境を作成して依存をインストール

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb psutil openai PyYAML
   ```

3. .env ファイルの作成（対話式ウィザード推奨）

   ```bash
   python -m kabusys.config_setup
   ```

   必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   重要な環境変数（主なもの）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用）
   - OPENAI_API_KEY: OpenAI を利用する場合に必要
   - LOG_LEVEL: ログレベル（INFO など）
   - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

   注意: config.py はプロジェクトルート（.git または pyproject.toml を探す）を基準に .env/.env.local を自動読み込みします。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 設定検証

   ```bash
   python -m kabusys.validate_config
   # --strict を付けると警告も FAIL 扱いで exit(1)
   python -m kabusys.validate_config --strict
   ```

5. 必要ディレクトリ（data, logs 等）の作成（通常は自動作成されますが、権限問題回避のため予め作成しておくと安心）

   ```bash
   mkdir -p data logs
   ```

---

## 使い方（起動例・主要コマンド）

- ExecutionEngine 起動（通常）

  ```bash
  python -m kabusys.run_execution
  ```

  - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して発注はモックで行われます。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に data/stop_requested.flag が作成されると Engine を停止します。
  - pid ファイルは data/execution.pid（デフォルト）に作成されます（Settings.pid_file_pathで変更可能）。

- Monitoring 起動（SystemMonitor ポーリング）

  ```bash
  # デフォルトポーリング間隔 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可能）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  - 監視は monitoring DB（Settings.sqlite_path）にデータを永続化します（monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用）。
  - 停止制御は上位プロセス用の stop フラグファイル（data/stop_requested.flag）で行います。

- 設定ウィザード（.env 生成/更新）

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証

  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- ライブラリ関数の呼び出し例（AI スコアリング）

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, date(2026, 4, 10), api_key="sk-...")
  ```

---

## ログと DBA の挙動（運用メモ）

- ロギング
  - ログは `kabusys.utils.logging_setup.setup_logging` により統一的に設定されます。
  - デフォルト: stdout と logs/<app_name>.log（日次ローテーション、30 日保持）
  - LOG_DIR 環境変数や引数でログ出力先を変更可能

- データベース
  - DuckDB（分析用）: デフォルト data/kabusys.duckdb
  - SQLite（監視用）: デフォルト data/monitoring.db
  - Paper trading 時は別 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB と分離
  - monitoring_db.init_monitoring_db は冪等でテーブル作成・簡易マイグレーション（カラム追加）を行います

- 停止・緊急停止
  - Kill Switch: `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送る（KillSwitch が存在する場合はエンジンが停止）
  - run_monitoring / run_execution 停止: `data/stop_requested.flag` を作成するとループが終了します

---

## 主要ファイル・ディレクトリ構成

（主要なファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/
    - (ExecutionEngine, OrderManager, BrokerFactory 等の実装が存在)
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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

プロジェクトルート（.git または pyproject.toml を検出）を基準に .env/.env.local を自動読み込みします。

---

## よくある注意点 / トラブルシューティング

- 環境変数が不足していると起動時に ValueError が発生します。必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を .env に設定してください。
- OpenAI 関連関数（news_nlp, regime_detector）は OPENAI_API_KEY を必要とします。未設定の場合は ValueError を送出します。
- MONITOR_POLL_INTERVAL は秒単位（デフォルト 60）。0 や負の値は無効でデフォルトにフォールバックします。
- monitoring は env に関係なく production sqlite_path（Settings.sqlite_path）を使用します。ペーパートレードのログは run_execution 側で PAPER_TRADING_SQLITE_PATH を利用して分離されます。
- process priority の変更は権限が必要な場合があります（設定に失敗しても警告を出して継続します）。
- DuckDB / SQLite のファイルディレクトリに書込み権限が必要です。`data/` と `logs/` の権限を確認してください。
- PyYAML がインストールされていないと config/*.yaml の内容検証はスキップされます（警告）。

---

## 開発者向けメモ

- 各モジュール（research / portfolio / ai 等）は可能な限り外部副作用を持たない純粋関数で実装されており、単体テストを書きやすい設計になっています。
- テスト時の環境変数読み込みを制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- OpenAI API 呼び出し部分はリトライや JSON パースの堅牢化が組み込まれており、テスト時は該当関数をモックで差し替えてください（例: unittest.mock.patch）。

---

必要であれば、この README をベースに運用マニュアル（systemd ユニット、Dockerfile、CI/CD 設定）やコマンドリファレンスを追加で作成できます。どの情報を追加したいか教えてください。