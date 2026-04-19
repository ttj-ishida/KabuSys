# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・研究・監視ツール群です。本リポジトリは以下の機能モジュールを含みます: 発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算・研究、AI ベースのニュースセンチメント / レジーム判定、ツール群（レポート生成等）。

以下にプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成をまとめます。

---

## プロジェクト概要

- 目的: 日本株自動売買システムのコアライブラリと運用ユーティリティを提供する。
- 主なコンポーネント:
  - ExecutionEngine: 実際の発注ロジック（paper_trading モードあり）
  - Monitoring: システム稼働状況や発注状況の監視、Kill Switch（安全停止）
  - Portfolio: 銘柄選定・重み付け・株数決定（純粋関数群）
  - Research: DuckDB を使ったファクター計算・特徴量探索
  - AI: OpenAI を利用したニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）
  - Tools: Paper Trading の検証レポートなど

---

## 主な機能一覧

- 環境設定ウィザード（.env の作成・更新）: `kabusys.config_setup`
- 設定検証 CLI（.env や config/*.yaml の不足・形式チェック）: `kabusys.validate_config`
- Execution エンジン起動スクリプト: `kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` の場合はモックブローカーを使用し、本番 DB と分離して `data/paper_trading.db` に記録
- Monitoring ポーリングループ起動スクリプト: `kabusys.run_monitoring`
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は常に本番の sqlite_path を参照して監視情報を記録
- 監視サブシステム:
  - SystemMonitor: CPU/メモリ/ディスクやデータ鮮度、Execution プロセス生存チェック
  - TradeMonitor: 発注ログ・滞留注文・約定異常の検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボードの管理
  - KillSwitch: 閾値超過時に `data/kill.flag` を書き込み ExecutionEngine に停止シグナルを送信
  - AlertManager: （実装に依存）通知送信
- ポートフォリオ構築ユーティリティ:
  - 銘柄選定、等金額/スコア加重の重み計算、リスク調整（セクター上限）、単元株丸め、ポジションサイズ計算
- Research:
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI モジュール（OpenAI に依存、API キー必要）:
  - news_nlp: ニュース記事を集約して銘柄別センチメント（ai_scores）を生成
  - regime_detector: ETF (1321) の MA 乖離 + マクロニュースセンチメントで市場レジーム判定
- ツール:
  - Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`（SQLite DB を読み取り各種指標を算出）

---

## 必要条件・依存関係

最低限必要な Python 実行環境:
- Python 3.9+

主要な外部パッケージ（機能に応じて必要）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML (config YAML の検証を行う場合)

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt がある場合はそれを利用してください。）

標準ライブラリ（sqlite3 / logging / threading / datetime など）は追加インストール不要です。

---

## セットアップ手順

1. リポジトリをクローンし、プロジェクトルートに移動
2. Python 仮想環境を作成して有効化
3. 必要パッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - 代表的な必須環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - その他主要変数（任意／デフォルトあり）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
     - LOG_LEVEL, LOG_DIR, OPENAI_API_KEY（AI 機能）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の動作）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、開発向け）

5. 設定検証（推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. 必要であれば data/ ディレクトリや logs/ を作成（多くのコードは起動時に自動作成します）

---

## 使い方（主要スクリプト／コマンド）

パッケージ形式で提供されているため、モジュールとして起動できます。プロジェクトルートが Python の import パスに含まれていることを前提とします（通常はルートで実行）。

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動
  - 通常（本番 or 開発）:
    ```bash
    python -m kabusys.run_execution
    ```
  - paper_trading モード（.env で KABUSYS_ENV=paper_trading を設定）では MockBrokerClient を利用し、`data/paper_trading.db` に記録されます。

- Monitoring 起動
  ```bash
  # デフォルト 60 秒間隔
  python -m kabusys.run_monitoring
  # ポーリング間隔を変更する場合 (秒)
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート生成（ツール）
  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または明示的に DB を指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 系関数実行（プログラム呼び出し）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB の接続オブジェクトと target_date、OpenAI API キー（または環境変数 OPENAI_API_KEY）を受け取ります。
  - 例（スクリプト内呼び出し）:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

注意点:
- Monitoring は既定で本番 sqlite_path を使用します（環境にかかわらず）。Execution は paper_trading モード時に専用 DB を使用して本番 DB と分離します。
- 停止フラグ:
  - 実行中のプロセスを止めるには `data/stop_requested.flag`（監視スクリプトで使用）や `data/kill.flag`（KillSwitch 用）を作成/削除する運用フローがあります。
- PID ファイル: ExecutionEngine は PID をファイルに書きます（設定可能: PID_FILE_PATH）。

---

## 主要設定項目（環境変数抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（例: INFO）
- LOG_DIR: ログ出力先（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を利用する機能で必要
- MONITOR_POLL_INTERVAL: Monitoring のポーリング秒（デフォルト: 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など

.env の自動読み込み:
- 起動時、プロジェクトルートの `.env` と `.env.local` が自動で読み込まれます（OS 環境変数を上書きしない / `.env.local` は上書き可能）。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ログと運用

- logging の設定は `kabusys.utils.logging_setup.setup_logging()` で統一されています。
  - stdout（StreamHandler）に出力しつつ、日次ローテーションでファイル出力（logs/<app_name>.log）を行います。
  - デフォルト: logs ディレクトリ、30 日分保持
- プロセス優先度は起動直後に `set_process_priority("high")` で高優先度に設定されます（設定に失敗した場合は警告表示で継続）。
- Kill Switch・監視アラートにより運用上の自動停止や通知を行えます（AlertManager の実装次第で LINE などに通知可能）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内の `src/kabusys` 配下を抜粋）

- kabusys/
  - __init__.py (バージョン等)
  - config.py (環境変数 / Settings クラス、自動 .env ロード)
  - config_setup.py (対話式 .env ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)
  - tools/
    - __init__.py
    - paper_verification_report.py (Paper Trading 検証レポート)
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (省略ファイルは実装に依存)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (実装に依存)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

（補遺）
- data/ : デフォルトの DB ファイルやフラグファイルを置くディレクトリ（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/execution.pid, data/stop_requested.flag）
- logs/ : ログファイル置き場（デフォルトはここ）

---

## 運用上の注意 / ベストプラクティス

- 本番運用時は必ず `KABUSYS_ENV=live` の時の設定（LINE 通知や kill flag の扱い、KILL_FLAG_CLEAR_ON_START の設定）を確認してください。`validate_config` は live 時の追加警告を出します。
- Paper Trading 時は本番 DB と完全分離されるため安全に検証可能です（KABUSYS_ENV=paper_trading を使用）。
- AI 機能は OpenAI API に依存し、呼び出し回数やレイテンシを考慮して運用してください。API キーの取り扱いは慎重に（.env を Git に入れない）。
- データベースファイルのバックアップおよびログローテーションの監視を行ってください（特に DuckDB や SQLite のファイル破損リスクに注意）。

---

以上がこのコードベースの概要 / 利用手順です。詳細な API や内製のクラス設計（ExecutionEngine・OrderManager・BrokerClient 等）は各モジュールのドキュメント / ソースコードの docstring を参照してください。必要であれば個別モジュールごとの README（例: monitoring の詳細設計、AI モジュール利用方法）も作成できますので指示ください。