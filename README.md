# KabuSys

日本株向け自動売買システムのパッケージ（ドキュメント README）。  
この README はリポジトリに含まれる主要モジュールの使い方、セットアップ、実行方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究パイプラインを構成するライブラリ兼実行スクリプト群です。主な機能は以下を含みます。

- 注文実行エンジン（ExecutionEngine） — 実際の発注 / ペーパートレードモード
- 監視（Monitoring） — システム稼働状況、注文ログ、リスク監視
- ポートフォリオ構築（選定、重み付け、ポジションサイジング、リスク調整）
- 研究用モジュール（ファクター計算、特徴量探索）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント解析）
- 各種ユーティリティ（ロギング設定、プロセス優先度設定、.env ウィザード、設定検証）
- ツール：Paper Trading 検証レポート生成 等

設計上、データストアに DuckDB / SQLite を使用し、OpenAI を用いる機能は API キーの設定が必要です。

---

## 主な機能一覧

- Execution
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - Risk 管理（最大ポジション比率、利用率、ドローダウン監視 など）
  - OrderManager / Reconciler などのコンポーネント群

- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク）とデータ鮮度検査
  - TradeMonitor（滞留注文、約定異常検知 等）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（リスクトリガで Execution を停止するためのフラグ）
  - Monitoring DB（SQLite）への永続化 + マイグレーション

- Portfolio
  - 候補選定、等配分 / スコア重み、ポジションサイズ決定、セクターキャップ適用、レジーム乗数

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC（Spearman）計算、統計サマリ

- AI（OpenAI）
  - news_nlp: ニュースを LLM で評価して ai_scores 書き込み
  - regime_detector: ETF とマクロニュースを組合せて market_regime 判定

- Tools
  - ペーパートレードの検証レポート生成スクリプト（paper_verification_report）

---

## 要件（主な依存ライブラリ）

- Python 3.9+（型のヒントや一部機能に依存）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- （任意）PyYAML — `python -m kabusys.validate_config` が config YAML の中身を検証する場合に必要

パッケージインストール例（pip）:
```
pip install duckdb psutil openai
# config 検証で PyYAML を使いたければ:
pip install PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを取得

2. 必要な Python パッケージをインストール（上記参照）。

3. 環境変数の設定（.env を作成）
   - 推奨: 対話式ウィザードで .env を作成
     ```
     python -m kabusys.config_setup
     ```
     ウィザードに従って J-Quants トークン、kabuステーションパスワード、DB パス、KABUSYS_ENV などを設定します。

   - 手動で作る場合はプロジェクトルートに `.env` を配置。主要なキーの例（.env のサンプル）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_station_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development    # development | paper_trading | live
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```
     - Paper Trading 専用 DB: `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）
     - Paper trading の fill 動作: `PAPER_FILL_MODE`（instant | partial | never | reject）

4. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告もエラー扱い
   ```

5. 初回起動時はデータディレクトリ（`data/`）やログディレクトリ（`logs/`）が自動作成されます。`LOG_DIR` を指定することでログ出力先を変更できます。

---

## 環境変数一覧（重要なもの）

主要な Settings プロパティは以下に対応します（デフォルトは括弧内）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN (任意)
- LINE_USER_ID (任意)
- DUCKDB_PATH (data/kabusys.duckdb)
- SQLITE_PATH (data/monitoring.db) — Monitoring が使用する SQLite（monitoring は環境に関わらず本番 sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
- PAPER_FILL_MODE (instant / partial / never / reject) — デフォルト "instant"
- PID_FILE_PATH (data/execution.pid)
- KILL_FLAG_PATH (data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視閾値）
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- OPENAI_API_KEY（AI 機能で必要）
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒。デフォルト: 60）

注意:
- run_monitoring は KABUSYS_ENV にかかわらず本番の `SQLITE_PATH` を使います（監視用 DB）。
- run_execution は KABUSYS_ENV=paper_trading の場合 `PAPER_TRADING_SQLITE_PATH` を使い、本番 DB と分離します。

---

## 実行方法（主要スクリプト）

プロジェクトをパッケージとして使う前提で、モジュールをモジュールパス経由で実行します。プロジェクトルートで以下を実行してください。

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine を起動（実行環境によって動作が異なる）
  - 本番（KABUSYS_ENV=live）
    ```
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - ペーパートレード
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    ペーパートレード時は MockBrokerClient を使い、`PAPER_TRADING_SQLITE_PATH` に記録されます。

  実行中は `data/execution.pid`（デフォルト）に PID が書き込まれ、停止の監視に `data/stop_requested.flag` をチェックします。停止するには stop フラグを作るか、プロセスに SIGINT を送る（Ctrl+C）。

- Monitoring を起動
  ```
  # ポーリング間隔を環境変数で上書き可能（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  Monitoring は SQLite (`SQLITE_PATH`) および DuckDB (`DUCKDB_PATH`) に接続し、SystemMonitor / TradeMonitor / RiskMonitor を定期的にポーリングします。監視プロセスも `data/stop_requested.flag` を見て停止します。

- Paper Trading 検証レポート生成ツール
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（ニューススコア、レジーム判定）
  - `OPENAI_API_KEY` を環境変数か関数引数で指定して利用します（例: `kabusys.ai.news_nlp.score_news`）。
  - コマンドラインラッパーは用意されていないため、スクリプトやジョブから該当関数を呼び出してください。

---

## 停止 / キルスイッチ

- 停止フラグ（両スクリプトで使用）
  - 実行/監視プロセスを外部から安全に止めたいときはプロジェクトの data ディレクトリに `stop_requested.flag` を作成します。
    - run_execution / run_monitoring は起動ループ内で `data/stop_requested.flag` の存在をチェックして終了します。

- Kill Switch（運用上の自動停止）
  - リスクイベント（ドローダウンやポジション数上限）により ExecutionEngine を停止したい場合、`KillSwitch` が `data/kill.flag` に理由を書き込むことで ExecutionEngine に停止を促します。
  - `KILL_FLAG_CLEAR_ON_START=1` にすると起動時に kill.flag を自動クリアする設定になります（本番では 0 を推奨）。

---

## ログ

- ログは `kabusys.utils.logging_setup.setup_logging` で統一設定されます。
- デフォルトは stdout と `logs/<app_name>.log`（日次ローテーション、30日分保持）に出力されます。
- 環境変数: `LOG_LEVEL`, `LOG_DIR` を使って調整できます。

---

## DB とマイグレーション

- DuckDB: 分析用（`DUCKDB_PATH`、デフォルト data/kabusys.duckdb）
- SQLite: 監視用（`SQLITE_PATH`、デフォルト data/monitoring.db）
- Paper Trading 用 SQLite: `PAPER_TRADING_SQLITE_PATH`（ペーパートレード専用 DB）
- `init_monitoring_db` はテーブル作成と簡易マイグレーション（カラム追加）を行い冪等に実行されます。スクリプト起動時に自動で呼ばれます。

---

## 開発者向けメモ / 実装上の注意点

- Monitoring は監視専用 DB（SQLITE_PATH）を使用します。Execution の paper_trading モードは paper_trading.db を使用して本番 DB と分離します。
- Process Priority: run_execution/run_monitoring 起動時に `set_process_priority("high")` が呼ばれます（OS に依存）。
- `kabusys.config` はプロジェクトルート（.git または pyproject.toml）を探索して `.env` を自動ロードします。テスト等では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。
- `validate_config` は .env と `config/*.yaml` の存在/基本構文をチェックします。PyYAML がない場合は YAML 内容検証をスキップします。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要ファイル／ディレクトリの一覧（抜粋）です：

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py         (提示コードの一部)
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py         (提示コードの一部)
  - execution/                 (発注実装群: broker_factory, execution_engine, order_manager 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記はリポジトリ内の主なモジュールを抜粋したものです。細かなファイルは実装により追加されています。）

---

## よくある運用操作

- モニタリングをバックグラウンドで実行する際はログのローテーションと data/ ディレクトリのパーミッションに注意してください。
- 本番運用前に `python -m kabusys.validate_config --strict` で設定を厳密にチェックすることを推奨します。
- OpenAI 使用部分は API キーに課金が発生するため、運用では呼び出し頻度・チャンクサイズ・リトライ設定を慎重に管理してください。

---

## サポート / 変更履歴

- 現在のパッケージバージョンは `kabusys.__version__ = "0.1.0"` です。
- 仕様変更や設計ドキュメント（PortfolioConstruction.md 等）に基づく実装が存在します。詳細はリポジトリ内の関連ドキュメントを参照してください。

---

README に記載の内容で不明点や実行時エラーが出た場合は、エラーログと環境変数（.env）設定のスクリーンショット／内容を添えてご相談ください。必要であれば .env のサンプルや具体的な起動/デバッグ手順を追記します。