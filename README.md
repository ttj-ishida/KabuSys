# KabuSys

日本株自動売買システムのコードベース README（日本語）

この README はリポジトリ内の主要スクリプトやモジュールに基づき、プロジェクト概要・機能・セットアップ手順・使い方・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム（研究／ポートフォリオ構築／発注エンジン／モニタリング／リスク管理）です。本リポジトリには以下の主要機能が含まれます。

- ファクター計算・特徴量生成（DuckDB を利用）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ExecutionEngine（発注／注文管理／リスクガード）
- Paper Trading モード（本番 DB と分離されたモックブローカー）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch（フラグによる安全停止）
- LLM を用いたニュースセンチメント解析（OpenAI API）
- 設定ウィザード、設定検証、検証レポート生成ツール

設計上、データ解析（DuckDB）と運用（SQLite / monitoring DB / 実行）の責務を分離しています。また、ランタイムの環境（development / paper_trading / live）に応じた挙動切替が可能です。

---

## 主な機能一覧

- kabusys.research
  - ファクター（モメンタム／ボラティリティ／バリュー）計算
  - 将来リターン計算、IC（Information Coefficient）評価、統計サマリー
- kabusys.portfolio
  - 候補選定（スコア順）、等重/スコア重み付け
  - ポジションサイズ計算（risk_based 等）、セクター制限、レジーム乗数
- kabusys.execution
  - Broker クライアントファクトリ（本番／モック切替）
  - ExecutionEngine（セッション実行、PID 管理、停止フラグ監視）
  - Order 管理（OrderRepository / OrderManager / Reconciler / RiskManager）
- kabusys.monitoring
  - SystemMonitor（CPU/メモリ/ディスク、プロセス生存、データ鮮度）
  - TradeMonitor（発注ログの監視）
  - RiskMonitor（ドローダウン・ポジション上限監視、dashboard 更新）
  - KillSwitch（危険検知時に data/kill.flag を書き込み実行エンジン停止）
  - MonitoringEngine（全 Monitor を束ねてポーリング）
  - 永続化用 SQLite 層（monitoring_db）
- kabusys.ai
  - ニュース NLP（OpenAI を用いたセンチメントスコアリング）
  - 市場レジーム判定（ETF とマクロニュースの組合せ）
- ユーティリティ
  - 設定ウィザード（.env の対話生成）
  - 設定検証 CLI（.env と config/*.yaml のチェック）
  - ログ設定ユーティリティ（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- その他ツール
  - Paper Trading 検証レポート生成（SQLite のペーパートレード DB を集計）

---

## 依存関係（代表）

最低限想定されるパッケージ（バージョンは適宜決めてください）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証を行う場合）
- （必要に応じて）その他ライブラリ

requirements.txt がある場合はそれを使用してください。無い場合は手動でインストールします。

例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を準備します。
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb psutil openai PyYAML
   ```

2. 環境変数（.env）を作成します（推奨: ウィザードを利用）。
   - 対話式ウィザードで .env を作る:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env を手動作成。代表的なキーとデフォルト:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | …) — デフォルト: INFO
     - OPENAI_API_KEY (AI 機能を使う場合)
     - KILL_FLAG_CLEAR_ON_START (0|1, default 0)

   自動読み込み: プロジェクトルート（.git または pyproject.toml が存在する場所）を基準に .env / .env.local を自動ロードします。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. 設定の検証（起動前推奨）:
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合
   python -m kabusys.validate_config --strict
   ```

4. 必要であればデータディレクトリを作成:
   ```
   mkdir -p data logs
   ```

---

## 使い方（主要スクリプト例）

各スクリプトはパッケージモジュールとして実行します。プロジェクトルートで次のように起動します。

- 監視（SystemMonitor をポーリングして監視ログを SQLite に書き込む）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を指定可能（デフォルト 60）。
  - 監視は常に本番（settings.sqlite_path）で指定された monitoring DB を使用します（環境にかかわらず）。
  - 停止: プロジェクトルート `data/stop_requested.flag` ファイルを作成するとループを抜けます。

- 実行エンジン（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient が使われ、書き込み先の SQLite は paper_trading 用に分離されます（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
  - 実行中に停止したい場合は `data/stop_requested.flag` を作成するとエンジンを停止します。
  - ExecutionEngine の PID は `data/execution.pid` に保存されます。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定
  ```

- AI 関連（スコア付与・レジーム判定）はライブラリ関数として呼び出すことを想定しています:
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

---

## 運用・実行周りの注意点

- データベース
  - DuckDB（分析用）: デフォルト `data/kabusys.duckdb`
  - Monitoring / trade logs（SQLite）: デフォルト `data/monitoring.db`
  - Paper Trading（SQLite）: デフォルト `data/paper_trading.db`（paper_trading モードで専用 DB を使用）
- STOP / KILL フラグ
  - 実行停止の外部シグナル: `data/stop_requested.flag` を作成すると run_monitoring / run_execution が終了処理を始めます。
  - Kill Switch（監視側が検出して書き込む）: `data/kill.flag`（Settings.kill_flag_path）を KillSwitch が生成します。ExecutionEngine はこのフラグを利用して停止する設計です。
- ログ
  - ログは stdout（StreamHandler）と日次ローテートのファイル（logs/<app_name>.log）に出力します。ログディレクトリは環境変数 `LOG_DIR` またはデフォルト `logs/`。
- 優先度
  - 起動スクリプトはプロセス優先度を `high` に設定しようとします（psutil を利用）。許可がない場合は警告が出ますが継続します。
- 自動ロード
  - .env / .env.local の自動ロードはプロジェクトルート検出に依存します（.git または pyproject.toml の存在）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## よく使う環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default http://localhost:18080/kabusapi)
- OPENAI_API_KEY (LLM 機能を使う場合)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- LOG_DIR — default: logs/
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — paper trading のフィルモード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0|1)

---

## ディレクトリ構成（概観）

以下はパッケージ内の主要ファイル・ディレクトリのツリー（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings
    - config_setup.py           — .env 対話ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_monitoring.py         — SystemMonitor ポーリングループ起動
    - run_execution.py          — ExecutionEngine 起動
    - utils/
      - logging_setup.py        — ログ設定ユーティリティ
      - process_priority.py     — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py        — SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
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
    - data/                      — 実行時生成される想定のディレクトリ（DB / flags / pid など）

（上記は主要ファイルの抜粋です。実コードベースを参照してください。）

---

## 開発・デバッグ時のヒント

- 設定検証を頻繁に実行して、必須環境変数やパスの問題を事前に検出してください。
- Paper Trading モードを使えば実際のブローカーに発注せずにエンジンの挙動を確認できます（DB が分離されます）。
- ログは stdout にも出るので、systemd / supervisord / Docker のログ収集と組み合わせると運用しやすいです。
- OpenAI を利用する際は API キーの取り扱いに注意し、.env は絶対にコミットしないでください。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視開始
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```

- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README を拡張して、インストール要件（requirements.txt）、デプロイ手順（systemd ユニット例 / Dockerfile）、API ドキュメントや設定ファイルのテンプレート（config/*.yaml の説明）を追加してください。追加で盛り込みたい内容があれば教えてください。