# KabuSys

日本株自動売買システムの一部を実装したコードベースの README（日本語）。

このドキュメントはプロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・研究基盤です。本リポジトリは以下の主要な関心事を含むモジュール群を提供します。

- 環境変数 / .env の対話式ウィザードと検証ツール
- 実行エンジン（ExecutionEngine）の起動スクリプト（本番 / ペーパートレード切替）
- 監視（Monitoring）サブシステム（システム状態、注文ログ、リスク監視、Kill Switch）
- ポートフォリオ構築（候補選定・重み計算・サイズ計算）
- 研究用モジュール（ファクター計算、特徴量探索）
- AI 関連（ニュース NLP / レジーム判定）のラッパー
- ツール類（Paper Trading 検証レポート生成 等）

設計方針の一部：
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV に応じる）
- DuckDB を分析用に使用、SQLite を監視・トランザクションログ用に使用
- API キー（OpenAI 等）は環境変数から読み込む
- ログはコンソールおよび日次ローテートファイルに出力

---

## 主な機能一覧

- config_setup.py: 対話式 .env 生成ウィザード
- validate_config.py: .env と config/*.yaml の事前検証 CLI
- run_execution.py: ExecutionEngine 起動（KABUSYS_ENV により Mock/実ブローカー切替）
- run_monitoring.py: SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL で調整可能）
- monitoring サブパッケージ:
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db
- portfolio サブパッケージ:
  - 候補選定・重み付け・ポジションサイジング・セクター制限・レジーム乗数
- research サブパッケージ:
  - ファクター計算（momentum/value/volatility）、前方リターン、IC、統計サマリ
- ai サブパッケージ:
  - news_nlp（ニュースを LLM でスコアリング）、regime_detector（市場レジーム判定）
- tools:
  - paper_verification_report: ペーパートレードの検証レポート生成

---

## 前提条件 / 必要パッケージ

- Python 3.10 以上（型注釈で `|` を使用しているため）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- 標準ライブラリ: sqlite3, logging, datetime など

（requirements.txt はリポジトリに含まれていません。下記コマンドを参照してインストールしてください。）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / 展開する
2. 仮想環境を作成して依存パッケージをインストールする（上記参照）
3. .env を準備する
   - 対話式に作成する（推奨）:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは、プロジェクトルートに `.env` を手動で作成してください。
   - 自動ロード:
     - デフォルトでプロジェクトルートの `.env` と `.env.local` を起動時に自動読み込みします（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   - 警告も失敗扱いにする場合:
     ```
     python -m kabusys.validate_config --strict
     ```
5. 必要なディレクトリとファイル:
   - デフォルトでは `data/`（DB や pid/flag ファイル）と `logs/`（ログ）を使用します。`setup_logging` が起動時にディレクトリを作成しますが、ファイル作成権限を確認してください。

---

## 環境変数（主なもの）

- KABUSYS_ENV: execution モード
  - "development"（開発、発注なし）
  - "paper_trading"（ペーパートレード：MockBroker を使用し data/paper_trading.db を使用）
  - "live"（本番）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が必要）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト `logs/`）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" でクリア、推奨は "0"）

代表的な .env の例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 使い方（コマンド / スクリプト）

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動
  - 本番 / ペーパートレードは KABUSYS_ENV に依存します。
  ```
  python -m kabusys.run_execution
  ```
  - 実行時の挙動:
    - プロセス優先度を high にセット（可能な場合）
    - SQLite（本番 or paper）と DuckDB に接続
    - BrokerClient をファクトリから作成（paper_trading では MockBroker）
    - ExecutionEngine をデーモンスレッドで実行し、data/stop_requested.flag を監視して停止

- Monitoring（SystemMonitor ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path を使用（環境にかかわらず）

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または `data/paper_trading.db`
  - レポートでは稼働率・注文成功率・送信率・P95 レイテンシ等を計算し PASS/FAIL を判定します

- AI 機能（プログラムから呼び出す）
  - ニューススコアリング:
    ```
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
    ```
  - OpenAI API の接続には `OPENAI_API_KEY` を設定するか、api_key 引数を渡してください。

---

## 監視・停止フロー（重要）

- 実行中に致命的なリスクが検出された場合、KillSwitch が `data/kill.flag` を書き込みます。ExecutionEngine はこのフラグを監視して停止します。
- 外部で強制停止したい場合は `data/stop_requested.flag` を作成すると run_execution/run_monitoring のループが検知して終了します。
- ExecutionEngine の PID は `data/execution.pid` に書かれます（起動時／停止時の管理に使用）。

---

## ログ

- ログはデフォルトで stdout と `logs/<app_name>.log`（日次ローテート、30 日分保持）に出力されます。
- ログ設定は `kabusys.utils.logging_setup.setup_logging(app_name=...)` を通じて統一的に行われます。

---

## モジュール概要（主要ファイルの説明）

- kabusys/config.py
  - .env 自動読み込み、Settings クラス（環境変数のラッパ）
- kabusys/config_setup.py
  - 対話式 .env 生成ウィザード
- kabusys/validate_config.py
  - 起動前の設定検査 CLI
- kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV に基づき DB を切り替え）
- kabusys/run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- kabusys/utils/
  - logging_setup.py: ログ設定ユーティリティ
  - process_priority.py: プロセス優先度 / CPU affinity 設定（psutil ベース）
- kabusys/monitoring/
  - monitoring_db.py: SQLite のスキーマ作成・永続化ラッパ
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py
- kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- kabusys/research/
  - factor_research.py, feature_exploration.py（DuckDB を用いた分析ロジック）
- kabusys/ai/
  - news_nlp.py, regime_detector.py （OpenAI を使った NLP / レジーム推定）
- kabusys/tools/
  - paper_verification_report.py

（上記は含まれる主要ファイルの抜粋です）

---

## ディレクトリ構成（抜粋）

プロジェクトルートに `src/kabusys` を格納する構成を想定しています。代表的なファイルを示します。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - __version__ / メタ情報
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - execution/
      - (ExecutionEngine, OrderManager, BrokerFactory 等 — 本 README のコードベースで参照)
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
- data/              # デフォルト DB・pid・flag を置く場所（起動時自動作成される場合あり）
- logs/              # ログファイル（setup_logging により作成）

---

## 開発上の注意 / 補足

- Python の型注釈やモジュール間インポートはプロジェクトルートから実行することを前提に書かれています。
- DuckDB / SQLite のスキーマは `monitoring_db.init_monitoring_db()` で自動作成・マイグレーションされます。起動スクリプトは適宜この初期化を呼びます。
- AI（OpenAI）機能は API キーが無い場合はエラーまたはフェイルセーフ動作（スコア 0.0 等）となる箇所があります。API コールはリトライ・バックオフを備えていますが、コスト・レート制限にはご注意ください。
- ペーパートレード実行時は実口座に影響が出ないよう専用 DB（PAPER_TRADING_SQLITE_PATH）と MockBroker を使用する設計です。
- 本番モード（KABUSYS_ENV=live）での起動前には `.env` と `config/*.yaml` を慎重に確認してください。validate_config は live 時に追加の警告チェックを行います。

---

必要であれば README の英語版、あるいは各モジュール（ExecutionEngine、OrderRepository、BrokerClientFactory 等）の詳しい API ドキュメントを別途作成します。どの部分を詳細化したいか指示ください。