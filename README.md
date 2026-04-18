# KabuSys — README (日本語)

このドキュメントは、リポジトリ内の主要モジュールに基づく簡易 README です。KabuSys は日本株向けの自動売買・研究・監視用ライブラリ群および起動スクリプトを含みます。以下はプロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成の要約です。

---
## プロジェクト概要
KabuSys は日本株の自動売買システムで、主に以下の機能を提供します。
- マーケットデータ（DuckDB）を用いたファクター計算・研究（research）
- ポートフォリオ構築、重み計算、ポジションサイズ決定（portfolio）
- ExecutionEngine（発注エンジン）の起動/管理（execution）
- システム監視・リスク監視・アラート・Kill Switch（monitoring）
- ニュース NLP を用いた銘柄センチメント解析（AI モジュール）
- ペーパートレードの検証レポート作成ツール（tools）

設計方針の例:
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV に依存）
- DuckDB による分析用処理、SQLite により監視・発注ログを永続化
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価（任意、APIキー必要）
- .env ファイルで設定を管理。自動読み込み機能あり（プロジェクトルートを探索）

---
## 主な機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用）
  - run_monitoring.py: SystemMonitor をポーリング（MONITOR_POLL_INTERVAL で間隔を制御可能）
- 設定管理
  - config.py: Settings クラス（環境変数 / .env ロード /バリデーション）
  - config_setup.py: .env 作成ウィザード（対話式）
  - validate_config.py: 起動前の設定検証 CLI
- 監視
  - monitoring/：SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine 等
  - monitoring_db.py: SQLite テーブル初期化 & シンプルな永続化 API
- ポートフォリオ構築
  - portfolio/：候補選定、重み計算、セクター制限、ポジションサイズ算出
- 研究・解析
  - research/：ファクター計算（momentum/value/volatility）、forward returns、IC、統計サマリ
- AI（任意）
  - ai/news_nlp.py：ニュース記事から銘柄ごとのセンチメントを OpenAI で評価して ai_scores に格納
  - ai/regime_detector.py：ETF の MA200 とマクロニュースで市場レジーム判定、DB へ書込
- ツール
  - tools/paper_verification_report.py：ペーパートレードの検証レポート生成

---
## セットアップ手順（開発/ローカル向け）
1. Python 仮想環境を作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows (PowerShell は別)
   ```

2. 必要パッケージをインストール（最低限の依存）
   - 必要な主要パッケージ:
     - duckdb
     - psutil
     - openai（ニュース NLP / レジーム判定 を使う場合）
     - PyYAML（config 検証で YAML の中身を検査したい場合）
   ```bash
   pip install duckdb psutil openai pyyaml
   ```
   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. プロジェクトルートに .env を作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成。最低限必須の環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - 参考（キーとデフォルト）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — OpenAI を使用する場合に設定

   注意: config.py はプロジェクトルート（.git または pyproject.toml がある場所）を探索して `.env` / `.env.local` を自動ロードします。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. DB・ディレクトリの準備
   - `data/`、`logs/` ディレクトリはスクリプト実行時に自動作成されることが多いですが、手動作成して権限を確認しておくと安全です。
   - DuckDB/SQLite ファイル: デフォルトでは `data/kabusys.duckdb` と `data/monitoring.db`。`config_setup` で指定したパスを利用してください。

---
## 使い方（主要スクリプト）
以下は代表的なコマンド例です。実行はプロジェクトルートで行ってください。

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（起動前に推奨）
  ```bash
  python -m kabusys.validate_config
  # 警告をエラーとして扱う strict モード:
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（本番／ペーパートレード共通）
  - ペーパートレードモード:
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    この場合、専用の paper_trading DB（デフォルト: data/paper_trading.db）に発注ログが記録され、本番 DB と分離されます。
  - 本番モード:
    ```bash
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - 実行中に停止を要求するにはプロジェクトの data ディレクトリに `stop_requested.flag` を作成します（スクリプトは起動時にプロジェクトルートを基準にこのファイルを監視します）。

- Monitoring（SystemMonitor）起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルトは 60 秒。
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - run_monitoring は、設定がどの環境でも監視用に本番 sqlite_path を利用します（監視ログ保存先は Settings.sqlite_path）。監視ループの停止には `data/stop_requested.flag` を使用します。

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB を使う
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パス指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（プログラムから）:
  - ニュースセンチメント評価:
    ```python
    from kabusys.ai import score_news
    # duckdb_conn は DuckDB の接続オブジェクト
    count = score_news(duckdb_conn, target_date, api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="sk-...")
    ```
  - これらは OpenAI API キー（`OPENAI_API_KEY` または引数 `api_key`）が必要です。

---
## 注意事項 / 運用メモ
- KABUSYS_ENV:
  - development, paper_trading, live のいずれか。live は本番であるため注意して設定してください（validate_config は live 時に追加警告を出します）。
- Kill Switch / Stop フラグ:
  - KillSwitch（監視側）がリスク事象を検出すると `data/kill.flag` を書き込み、ExecutionEngine に対する停止シグナルを出します。Settings.kill_flag_path でパスを指定できます。
  - 各種スクリプトは `data/stop_requested.flag` を監視し、これが存在するとループの終了（プロセス停止）を行います。運用オペレーションでは stop_requested.flag を配置して安全にシャットダウンできます。
- ログ:
  - setup_logging により stdout（StreamHandler）と日次ローテートファイル（logs/<app_name>.log）に出力します。ログディレクトリは自動作成を試みますが、権限やパスに注意してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db はテーブル作成と一部のバージョン互換処理（ADD COLUMN）を行います。既存データのバックアップを運用側で確保してください。
- テスト / モック:
  - KABUSYS_ENV=paper_trading では MockBrokerClient を用いるため本番ブローカに発注されません。開発・検証はこのモードで行うことを推奨します。

---
## ディレクトリ構成（抜粋）
リポジトリの主要なファイル配置（src/kabusys 以下）:

```
src/kabusys/
├─ __init__.py
├─ config.py
├─ config_setup.py
├─ validate_config.py
├─ run_execution.py
├─ run_monitoring.py
├─ execution/                # 発注エンジン関連（OrderManager 等）
│  ├─ ...                   # (実装ファイル群)
├─ monitoring/
│  ├─ monitoring_db.py
│  ├─ system_monitor.py
│  ├─ trade_monitor.py
│  ├─ risk_monitor.py
│  ├─ monitoring_engine.py
│  ├─ kill_switch.py
│  ├─ alert_manager.py
│  └─ ...
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ portfolio/
│  ├─ __init__.py
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  └─ risk_adjustment.py
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ tools/
│  ├─ __init__.py
│  └─ paper_verification_report.py
├─ utils/
│  ├─ __init__.py
│  ├─ logging_setup.py
│  └─ process_priority.py
└─ data/                     # 実行時に使用される SQLite/DuckDB/flag/pid ファイル等
```

（注: 上のツリーは抜粋です。実際のファイル一覧はリポジトリの内容に依存します。）

---
## よく使う環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（KABUSYS_ENV=paper_trading 時に使用）
- LOG_LEVEL — デフォルト: INFO
- OPENAI_API_KEY — OpenAI を使う場合に必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）、デフォルト 60
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動でクリアするか（開発用、0/1）

---
## 開発者向け補足
- config.py の .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストや CI で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ロギングは全スクリプトで共通の setup_logging を使うことで一貫したログ出力を実現しています。
- プロセス優先度や CPU affinity の設定は utils/process_priority.py に集約されており、スクリプト起動直後に優先度を上げる設計になっています（失敗時は警告を出して継続します）。

---
README はコードベースの主要点をまとめたものです。実行時の詳細な挙動や内部 API の使用方法は、各モジュールの docstring / ソースコメントを参照してください。追加で詳しいセットアップ手順や運用手順書が必要であれば、目的に合わせて追記します。