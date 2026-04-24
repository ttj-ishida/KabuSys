# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、注文実行エンジン、監視（モニタリング）機能、ポートフォリオ構築・リスク制御、リサーチ／ファクター計算、LLM を使ったニュース NLP などを含む自動売買システムのコア部分です。本 README はローカルでのセットアップ・実行方法や各コンポーネントの概要をまとめたガイドです。

注意: 実際に売買 API を用いると実資金が動きます。`KABUSYS_ENV` を適切に設定し、本番環境 (`live`) では事前に十分な確認を行ってください。

---

目次
- プロジェクト概要
- 主な機能
- 必須 / 主要な環境変数（設定）
- セットアップ手順
- 実行例（使い方）
- 停止・キルスイッチについて
- ディレクトリ構成（主要ファイル）

---

プロジェクト概要
- 日本株を対象とした自動売買（ExecutionEngine）とその周辺ツール群。
- DuckDB を用いた分析・リサーチ（prices_daily, raw_financials 等）。
- SQLite を用いた監視ログ / 発注履歴の永続化（monitoring.db / paper_trading.db）。
- LLM（OpenAI）を利用したニュースセンチメント評価や市場レジーム判定（オプション）。
- ローカル開発・ペーパートレード・本番の3モードをサポート（KABUSYS_ENV）。

主な機能
- ExecutionEngine 起動 / 発注管理（paper_trading モードでは MockBroker を使用して本番 DB と分離）
- Monitoring：システム状態（CPU/メモリ/ディスク）、データ鮮度、滞留注文・約定異常、リスク（ドローダウン・ポジション上限）監視
- Kill Switch：監視結果に基づき ExecutionEngine 停止フラグ（data/kill.flag）を発行
- Portfolio construction：候補選定 / 重み付け / ポジションサイズ計算（純粋関数群）
- Research：ファクター計算（momentum, value, volatility）および特徴量解析（IC 等）
- AI モジュール：ニュース NLP（OpenAI）による銘柄別センチメント、レジーム判定
- ツール：Paper Trading 検証レポート生成スクリプト等
- 設定ウィザードと検証ツール（.env の生成 / validate_config）

主要な環境変数（抜粋）
- 必須（実行に必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境切替
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- DB / ファイル
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch のフラグパス（デフォルト: data/kill.flag）
- ログ関連
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - LOG_DIR — ログ保存先（デフォルト: logs/）
- AI（OpenAI）
  - OPENAI_API_KEY — OpenAI API キー（AI モジュールを使う場合必須）
- 監視設定（閾値）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（パーセンテージ）
- 監視ループ間隔
  - MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒。デフォルト 60）

PAPER_FILL_MODE（ペーパートレードの約定挙動）
- 有効値: "instant" | "partial" | "never" | "reject"（デフォルト: "instant"）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、仮想環境を作る
   - python >= 3.10 を推奨
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install --upgrade pip
     ```
2. 依存パッケージをインストール
   - 本コードベースで使用している主なパッケージ:
     - duckdb
     - psutil
     - openai（AI 機能を使用する場合）
     - PyYAML（config ファイル検証時に任意）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - （プロジェクトに requirements.txt があればそれを使用してください）
3. .env の準備（env ウィザード推奨）
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - または手動で .env をプロジェクトルートに作成。最低限必須は JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD。
4. 設定検証（任意）
   - 設定が整っているか確認:
     ```
     python -m kabusys.validate_config
     ```
   - --strict を付けると警告も失敗扱いになります:
     ```
     python -m kabusys.validate_config --strict
     ```

使い方（主なエントリポイント）
- ExecutionEngine を起動（通常はシステムのサービス／Supervisor / systemd 経由で起動）
  - 本番（KABUSYS_ENV=live）の例:
    ```
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - ペーパートレード（DBを完全分離）:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 実行時の挙動:
    - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
    - 起動時に data/stop_requested.flag が既に存在する場合は起動を行わず終了します。
    - _EXECUTION_PID（data/execution.pid）に PID を書く仕組みがあり、監視や手動停止用に利用されます。

- Monitoring を起動
  - 監視ポーリングループ（SystemMonitor 等）:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔は環境変数で変更可能:
    ```
    export MONITOR_POLL_INTERVAL=30  # 30秒間隔
    python -m kabusys.run_monitoring
    ```
  - 監視は常に本番 sqlite_path を使用して監視テーブルを操作します（run_monitoring は KABUSYS_ENV に依らず sqlite_path を参照）。

- 設定ウィザード（.env 生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（ツール）
  - デフォルト DB: data/paper_trading.db
  - 例: 期間を指定してレポート出力
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - 別 DB を指定する:
    ```
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
    ```

- AI モジュール（プログラムから利用）
  - ニュース NLP（銘柄別センチメントを ai_scores テーブルへ書き込む）:
    - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
    - 例（スクリプト内で DuckDB 接続を作成して呼び出す）:
      ```py
      import duckdb
      from datetime import date
      from kabusys.ai import score_news

      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, target_date=date(2026,4,11), api_key="sk-...")
      ```
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログ
- ログはデフォルトで stdout（コンソール）と rotating file handler（logs/<app_name>.log、日次ローテーション、30日保持）へ出力されます。
- ログの設定は kabusys.utils.logging_setup.setup_logging で共通化されています。
- ログレベルは LOG_LEVEL と引数で制御できます。

停止・キルスイッチ
- 実行ループ（run_monitoring, run_execution）はプロジェクトの data ディレクトリにあるフラグファイルを参照します。
  - data/stop_requested.flag — 監視ループ・実行ループを優雅に停止させるためのフラグ（存在を検知してループを終了）。
  - data/kill.flag — KillSwitch が書き込むフラグ。ExecutionEngine はこれを検知して停止します。
- KillSwitch はリスク監視（ドローダウン超過、ポジション数超過等）に基づき kill.flag を生成します。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では危険な設定のため推奨されません）。

開発者向けメモ
- 設定の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
- DB 初期化:
  - monitoring のテーブル群は init_monitoring_db(sqlite_conn) により冪等に作成されます。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼び OS に応じて優先度を設定しようとします（psutil を使用）。失敗してもログ警告を出して継続します。

ディレクトリ構成（主要ファイル）
（src/kabusys 以下がパッケージルート）

- src/kabusys/
  - __init__.py
  - config.py             — 環境変数 / Settings 管理
  - config_setup.py       — .env 対話式ウィザード
  - validate_config.py    — 設定検証 CLI
  - run_execution.py      — ExecutionEngine 起動スクリプト
  - run_monitoring.py     — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py    — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 管理
  - monitoring/
    - monitoring_db.py    — SQLite 永続層（テーブル定義 / DB 操作ラッパー）
    - system_monitor.py   — システム / データ鮮度監視
    - trade_monitor.py    — （滞留注文/約定監視等）※実装ファイルが存在
    - risk_monitor.py     — ドローダウン／ポジション上限監視
    - kill_switch.py      — kill.flag 書き込みロジック
    - monitoring_engine.py— 複数 Monitor を束ねるエンジン
    - alert_manager.py    — （アラート送信管理、LINE 連携等）
  - execution/
    - execution_engine.py — ExecutionEngine（発注セッション制御）
    - broker_factory.py   — Broker クライアント生成（実口座 / Mock 切替）
    - order_manager.py    — 注文管理
    - order_repository.py — 注文 DB 永続化
    - reconciler.py       — 注文状態整合処理
    - risk_manager.py     — 発注時のリスク制御
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py         — ニュース NLP（OpenAI 連携）
    - regime_detector.py  — マーケットレジーム判定（LLM + 指標合成）

その他ファイル / ディレクトリ（運用上参照）
- data/ — SQLite ファイル、PID、フラグ等を置く場所（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）
- logs/ — 日次ローテートされるログファイル（logs/execution.log, logs/monitoring.log など）
- config/ — 各種 YAML 設定ファイル（system_config.yaml 等。validate_config でチェック）

トラブルシューティング（よくある注意点）
- .env を作成後は python -m kabusys.validate_config で検証してください。
- OpenAI を使う機能を実行する際は OPENAI_API_KEY を正しく設定してください。API エラーはリトライやフォールバックを行う設計ですが、キー未設定は例外になります。
- monitoring は常に Settings.sqlite_path（監視 DB）を使用します。run_execution は KABUSYS_ENV に応じて paper_trading 用 DB を使い分けます（本番 DB と混ざらないように注意）。

ライセンス / バージョン
- パッケージバージョンは kabusys.__version__ = "0.1.0"（初期版）。

---

この README はコード内の docstring と起動スクリプトを基に作成しました。追加で README に載せたいコマンドや運用手順（systemd ユニット例、監視ダッシュボード構築手順など）があれば教えてください。必要に応じてサンプル .env、systemd サービスファイル、デバッグ手順なども追記できます。