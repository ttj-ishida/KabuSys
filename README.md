# KabuSys

日本株自動売買システムのライブラリ／ツール群。  
取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュースNLP / レジーム判定などの主要コンポーネントを含みます。

---

## 概要

このリポジトリは以下の機能群を持つモジュール群で構成されています。

- Execution：発注ロジック、注文管理、リスク管理、ブローカークライアントの抽象化
- Monitoring：システム状態・注文状況・リスク監視、Kill Switch（停止フラグ）機能、監視ログ保存（SQLite）
- Portfolio：銘柄選定・重み付け・ポジションサイズ計算・セクター制限
- Research：ファクター計算（モメンタム・ボラティリティ・バリュー）、特徴量解析（IC 等）
- AI：ニュースの NLP 評価（OpenAI を利用）、市場レジーム判定
- Utils：ログ設定、プロセス優先度制御、設定読み込み・ウィザード、設定検証
- Tools：Paper Trading 検証レポート生成 等

設計方針の一例：
- 本番 DB と Paper Trading DB を分離（KABUSYS_ENV により切替）
- .env ファイルによる設定、config_setup による対話的作成
- validate_config による事前チェック
- DuckDB を分析用 DB、SQLite を監視・注文ログ用に利用
- OpenAI API は外部依存（環境変数でキー指定）

---

## 主な機能一覧

- run_execution.py：ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading DB を使用
  - 停止フラグ（data/stop_requested.flag）で安全停止
- run_monitoring.py：SystemMonitor のポーリング起動スクリプト
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）
  - 監視ログは常に本番用 sqlite_path に書き込む（環境に関わらず）
- config_setup.py：.env 作成/更新の対話式ウィザード
- validate_config.py：.env や config/*.yaml の検証 CLI
- tools/paper_verification_report.py：Paper Trading の検証レポート生成
- ai/news_nlp.py：ニュース記事をまとめて OpenAI に送信し株ごとのセンチメントを ai_scores テーブルへ書き込み
- ai/regime_detector.py：ETF の MA とマクロニュースを組み合わせて市場レジーム判定・保存
- monitoring/*：MonitoringDB（SQLite ベース）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager、MonitoringEngine 等
- portfolio/*：候補選定 / 重み算出 / ポジションサイズ / セクターキャップ / レジーム乗数

---

## セットアップ手順

※ 環境に合わせて Python 仮想環境を用意してください（推奨: Python 3.10+）。

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール  
   （requirements.txt がない場合は下記の主要依存をインストール）
   ```
   pip install duckdb psutil openai
   # 任意: PyYAML があると validate_config の YAML 検証が有効化されます
   pip install pyyaml
   ```

4. 対話式で .env を作成
   ```
   python -m kabusys.config_setup
   ```
   - J-Quants / kabu API のトークン等の必須項目を入力してください。
   - `.env` を絶対にリポジトリにコミットしないでください。

5. 設定検証（必須項目等のチェック）
   ```
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合（--strict）
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ等の準備（必要なら）  
   デフォルトは `data/`、ログは `logs/`。設定でパスを上書きできます。

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（SQLite）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- その他：LOG_DIR / KILL_FLAG_CLEAR_ON_START / PAPER_FILL_MODE など

---

## 使い方（起動例）

- ExecutionEngine（取引実行）を起動：
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は paper_trading DB を使い、MockBrokerClient による擬似発注になります。
  - 停止はプロセス終了（Ctrl+C）か、別プロセスで kill.flag（data/kill.flag）を書き込むことで行えます。
  - 実行中は PID を data/execution.pid に書きます。

- SystemMonitor（監視ループ）を起動：
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で変更：
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 停止は data/stop_requested.flag を作成するか Ctrl+C。

- Paper Trading 検証レポート生成：
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI 関連（プログラム内部 API）：
  - ニューススコアリング：
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
  - レジーム判定：
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

（これらは DuckDB 接続を受け取り DB のテーブルを更新します。OpenAI API キーが必要です）

---

## 停止 / Kill Switch

- Kill Switch（監視が検出した深刻なリスクで ExecutionEngine を停止）：
  - 監視側で条件が満たされると `data/kill.flag` に理由を書き込みます（冪等）。
  - ExecutionEngine は起動時に `KILL_FLAG_CLEAR_ON_START` 環境変数で自動クリア設定が有効でない限り、kill.flag を検知すると起動しないか停止します。

- 強制停止フラグ（ランタイム中に監視を止める）：
  - `data/stop_requested.flag` を作成すると run_monitoring や run_execution のループが気づいて安全に終了します。

---

## ログと DB の場所

- DuckDB（分析用）: デフォルト `data/kabusys.duckdb`（Settings.duckdb_path）
- SQLite（監視ログ）: デフォルト `data/monitoring.db`（Settings.sqlite_path）
- Paper Trading SQLite: デフォルト `data/paper_trading.db`（Settings.paper_sqlite_path）
- ログ出力: `logs/<app_name>.log`（setup_logging が自動セットアップ）

ログの設定は `kabusys.utils.logging_setup.setup_logging(app_name=...)` を通じて統一的に行われます。

---

## ディレクトリ構成

以下は主要ファイル／モジュールの一覧（src/kabusys 配下）：

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/
    - (Engine, OrderManager, BrokerFactory, RiskManager 等 想定)
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
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

（上記は主要なファイルを抜粋したツリーです。実際のモジュールはさらに細分化されています）

---

## 開発・運用上の注意

- 本番環境（KABUSYS_ENV=live）では設定ミスが重大な損失に直結します。`validate_config` を利用して事前チェックを徹底してください。
- `.env` に機密情報（API トークン等）を格納する場合、絶対に Git にコミットしないでください。
- OpenAI を利用する機能は API 呼び出しにより課金が発生します。API キーの管理とレート制限に注意してください。
- run_execution は Paper Trading と Live の DB を分離しています。Paper Trading 実行時は `PAPER_TRADING_SQLITE_PATH` を用いて安全に検証できます。
- 依存ライブラリ（duckdb / psutil / openai / pyyaml 等）は環境に合わせてインストールしてください。

---

## 追加情報 / 参考コマンド

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 実行ログは `logs/` 配下に出力されます。ログローテーションは日次＋30世代保持です。

---

必要であれば、README に環境変数のサンプル (.env.example) を追加したり、詳しい実行手順（Systemd ユニット、コンテナ化、CI/CD のサンプル）を追記します。どの情報を補足しますか？