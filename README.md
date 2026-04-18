# KabuSys

日本株向け自動売買システム（ライブラリ + 実行スクリプト群）

このリポジトリは、シグナル生成〜ポートフォリオ構築〜発注・モニタリング・リサーチ・AI（ニュースNLP / レジーム判定）までを含む自動売買フレームワークの実装です。各コンポーネントはモジュール化されており、ローカル開発・ペーパートレード・本番（ライブ）運用を想定しています。

バージョン: 0.1.0

---

## 概要（Project overview）

- シグナル生成やポートフォリオ構築に関する純粋関数群（portfolio/ 以下）
- DuckDB を用いたリサーチ・ファクター計算（research/ 以下）
- OpenAI を用いたニュースセンチメントおよびレジーム判定（ai/ 以下）
- 発注エンジン・注文管理・リスク管理（execution/ 以下、エントリポイントは run_execution.py）
- システム稼働監視・アラート・Kill Switch（monitoring/ 以下、エントリポイントは run_monitoring.py）
- 各種ユーティリティ（設定読み込み、ログ設定、プロセス優先度設定 等）

設計上のポイント:
- .env による環境変数管理（config.py / config_setup.py）
- 本番 DB とペーパートレード DB を分離（Settings により切替）
- DuckDB を分析用に使用、SQLite を監視・トレードログ用に使用
- OpenAI 呼び出しは外部 API を扱うため、APIキーが必要（ai モジュール）

---

## 主な機能一覧（Features）

- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動（発注ループ）
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループ起動（監視）
- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local）
  - 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config [--strict]
- モニタリング
  - システムリソース・プロセス稼働・データ鮮度監視
  - リスク監視（ドローダウン・ポジション上限）
  - Kill Switch（data/kill.flag）により ExecutionEngine 停止
- 発注・リスク管理
  - Broker クライアント抽象化（実運用 / mock for paper trading）
  - OrderManager / RiskManager / Reconciler 等
- ポートフォリオ構築
  - 候補選定、等比率・スコア加重の重み計算
  - リスク調整（セクター上限・レジーム乗数）
  - 株数算出（単元株丸め、aggregate cap）
- リサーチ
  - モメンタム / ボラティリティ / バリュー 等のファクター計算（DuckDB）
  - 将来リターン計算、IC 計算、統計サマリー
- AI
  - ニュース集約→OpenAI（gpt-4o-mini）による銘柄ごとのセンチメントスコア付与（ai.score_news）
  - マクロニュース + ETF MA200 による市場レジーム判定（ai.score_regime）
- ツール
  - ペーパートレード検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順（Setup）

以下は一般的なローカル開発環境構築例です。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - requirements.txt はこのコード抜粋に含まれていません。最低限必要なパッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config で YAML 検証を行う場合）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   - 開発用にパッケージにまとめている場合:
   ```
   pip install -e .
   ```

4. .env を作成
   - 対話式ウィザードで生成:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは `.env.example` を参考に手動で作成。
   - 自動読み込み:
     - config.py はプロジェクトルートに `.env` / `.env.local` があれば自動で読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

5. 設定検証（必須環境変数の確認）
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする strict モード
   python -m kabusys.validate_config --strict
   ```

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要なオプション:
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイル（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper trading 専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する際に必要）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の MockBroker の約定挙動（instant/partial/never/reject）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START などの監視設定

注意:
- run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番用の sqlite_path）を使用して監視データを記録します（監視 DB の分離は行っていません）。
- run_execution は KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用し、本番 DB と分離します。

---

## 使い方（Usage）

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine（発注エンジン）起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV により paper_trading / live の動作が切り替わります。
  - 実行中に停止させたい場合は monitoring 側の Kill Switch（data/kill.flag）やプロジェクトの停止フラグ（data/stop_requested.flag）を利用します。

- Monitoring（監視ループ）起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視が停止されるときは data/stop_requested.flag を作成するとループが終了します。

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示したい場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（スコア計算）をプログラムから呼ぶ
  - ニュース NLP（ai.score_news）やレジーム判定（ai.score_regime）はライブラリ関数として呼び出します。OpenAI API キーが必要です。
  - 例（Python スクリプト内）:
    ```py
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, datetime.date(2026,4,1), api_key="sk-...")
    ```

---

## 監視 / 停止フラグ

- data/kill.flag: Kill Switch が書き込むファイル。ExecutionEngine はこれを検知して安全に停止します。
- data/stop_requested.flag: run_monitoring / run_execution の起動ループを停止するために使用されます（手動でファイルを作成するとループが終了します）。
- PID ファイル: data/execution.pid（ExecutionEngine の PID を記録）

---

## ログ

- デフォルトディレクトリ: logs/
- setup_logging() によって stdout と日次ローテーションファイル（<app_name>.log）が設定されます（30日保持）。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御できます。

---

## ディレクトリ構成（Directory structure）

主要なファイル/ディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポートツール
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
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照)
  - execution/                     — 発注エンジン関連（OrderManager, BrokerFactory 等）
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に生成される想定)
    - *.db, kill.flag, stop_requested.flag, execution.pid, ...

（上記は抜粋されたファイルを中心に記載しています。実際のリポジトリにはさらにモジュールやサンプル設定、スクリプトが含まれる可能性があります。）

---

## よくある問題と対処（Troubleshooting）

- 必須環境変数が足りない
  - python -m kabusys.validate_config で不足を検出できます。config_setup で初期 .env を作成してください。
- DuckDB / SQLite ファイルが見つからない
  - Settings の DUCKDB_PATH / SQLITE_PATH を確認、.env で上書きしてください。必要ならディレクトリを作成してください。
- OpenAI に接続できない / キーがない
  - AI 機能（news_nlp, regime_detector）を使うには OPENAI_API_KEY を設定してください。テスト時はモック可能です（内部の _call_openai_api を patch）。
- ログファイルが作れない
  - LOG_DIR のパーミッションを確認。作成に失敗した場合はコンソール出力のみで継続します（warning が出ます）。
- run_monitoring のポーリング間隔を変更したい
  - 環境変数 MONITOR_POLL_INTERVAL（秒）を設定してください。不正な値を与えるとデフォルト 60 秒にフォールバックします。
- デバッグや開発中に自動 .env ロードを無効化したい
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みをスキップします。

---

## ライセンス / 貢献

（ここには実際のライセンス情報や貢献方法を記載してください。サンプル README のため省略しています。）

---

この README はコード抜粋に基づいて作成しています。実際のプロジェクトでは requirements.txt / setup.cfg / pyproject.toml / .env.example 等を参照し、運用手順や本番環境での注意事項を追記してください。