# KabuSys

日本株自動売買システム用のライブラリ兼起動スクリプト群です。  
このリポジトリは戦略・ポートフォリオ構築、発注実行（ExecutionEngine）周り、監視（Monitoring）、研究用ファクター計算、そして一部 AI を使ったニュース解析などの機能を提供します。

---

## プロジェクト概要

- Python モジュール群として設計されており、ライブラリとして利用できる関数群（ポートフォリオ構築、ファクター計算、レポート生成など）と、実運用向けの起動スクリプト（Execution / Monitoring / 設定ウィザード / 検証 CLI 等）を含みます。
- 永続化は主に SQLite（監視用）および DuckDB（分析用）を想定しています。ペーパートレード時は実際の発注 DB と分離して専用の SQLite を利用できます。
- OpenAI（gpt-4o-mini）を使ったニュースのセンチメント評価や、市場レジーム判定の機能を備えています（API キー必須、任意機能）。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine の起動（本番 / ペーパートレード切替）
  - run_monitoring.py — SystemMonitor のポーリングループ起動
  - config_setup.py — .env を対話的に作成・更新するウィザード
  - validate_config.py — 環境変数 / config/*.yaml の検証 CLI
  - tools.paper_verification_report — Paper Trading 検証レポート生成

- モジュール（ライブラリ）
  - portfolio: 候補選定・重み計算・ポジションサイズ計算・セクター制限・レジーム乗数
  - research: ファクター計算（momentum / value / volatility）、特徴量解析（IC 等）
  - ai:
    - news_nlp: ニュースを LLM でスコアリングして ai_scores に保存
    - regime_detector: ETF とマクロニュースを組み合わせた市場レジーム判定
  - monitoring:
    - MonitoringDB: 監視用 SQLite テーブルの初期化 / 読み書き
    - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch 等
  - utils:
    - logging_setup: 統一的なログ設定（コンソール + 日次ローテーション）
    - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（開発 / ローカル実行向け）

1. Python バージョン
   - Python 3.10 以上を推奨（型アノテーションの union 演算子などを使用）

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（概ね以下が必要）
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証を完全に行いたい場合）
   - その他標準ライブラリ（sqlite3 などは標準）

   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

   ※ requirements.txt は本リポジトリに含まれていない場合があるため、環境に合わせて必要なパッケージをインストールしてください。

4. .env の初期作成（推奨）
   - 対話式ウィザードで .env を作成:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env を手動で作成（.env.example を参照）

5. 設定検証
   - 設定・ファイルパス・YAML ファイルの整合性をチェック:
     ```
     python -m kabusys.validate_config
     ```
   - 警告を厳密に扱う（--strict）:
     ```
     python -m kabusys.validate_config --strict
     ```

6. データディレクトリ
   - デフォルトの DB / PID / フラグファイルは `data/` 下に作られます。必要に応じてディレクトリの作成や権限を調整してください。
   - デフォルトパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / kill flags: data/execution.pid, data/kill.flag, data/stop_requested.flag

---

## 環境変数（主なもの）

- 必須（実行に必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境 / 動作制御
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60 秒）

- DB / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）

- OpenAI / AI 関連
  - OPENAI_API_KEY（news_nlp や regime_detector を利用する場合に必要）

- Paper Trading 設定
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

---

## 使い方（主なコマンド例）

- 実行エンジン（ExecutionEngine）を起動
  - 通常（開発）:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード（環境変数で切替）:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - run_execution は KABUSYS_ENV が `paper_trading` の場合 MockBroker を使用し、paper_trading 用の SQLite に記録します。

- 監視ループを起動
  - ポーリングで SystemMonitor を回す:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔を変更したい場合:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- 設定ウィザード（.env の生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポートを生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB を直接指定:
  ```
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- ライブラリ関数（Python から呼び出し）
  - ポートフォリオ構築:
    ```
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
    ```
  - 研究系 / ファクター:
    ```
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    ```
  - AI ニューススコアリング:
    ```
    from kabusys.ai import score_news
    # 使用例: score_news(conn, target_date, api_key="...")
    ```

---

## 停止 / Kill Switch の仕組み

- マニュアル停止
  - 実行中のプロセスは `data/stop_requested.flag`（run scripts 用）や `data/kill.flag`（ExecutionEngine 停止用）で制御されます。
  - run_monitoring / run_execution は stop_requested.flag を検知すると安全に終了します。
  - KillSwitch（監視側）はリスク条件を満たした際に `data/kill.flag` を書き込み、ExecutionEngine 停止を促します。`KILL_FLAG_CLEAR_ON_START` で起動時に自動クリアするかどうか制御できます（本番では自動クリアしないことを推奨）。

---

## ログ

- ログは `kabusys.utils.logging_setup.setup_logging` を通じて統一的に設定されます。
- デフォルトは標準出力（stdout）と日次ローテーションするファイル（logs/<app_name>.log）への出力。
- ログレベルは `LOG_LEVEL` 環境変数または `setup_logging` の引数で制御可能。

---

## ディレクトリ構成（主要ファイル・モジュール）

（ソースは `src/kabusys/` 以下を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / .env 自動ロード
    - config_setup.py          — .env 対話ウィザード（CLI）
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - utils/
      - logging_setup.py       — ログの統一設定
      - process_priority.py    — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py       — SQLite の初期化 / 永続化層
      - system_monitor.py      — システム・データ鮮度監視
      - risk_monitor.py        — ドローダウン・ポジション数監視
      - trade_monitor.py       — 発注関連監視（滞留・約定異常 等）
      - monitoring_engine.py   — 各 Monitor を束ねる実行エンジン
      - kill_switch.py         — kill.flag の書き込み・評価
      - alert_manager.py       — （通知送信）※実装に依存
    - execution/
      - execution_engine.py    — ExecutionEngine（エンジン本体）
      - broker_factory.py      — Broker クライアント生成（実ブローカ/Mock）
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
      - news_nlp.py            — ニュースの LLM スコアリング
      - regime_detector.py     — 市場レジーム判定
    - tools/
      - paper_verification_report.py
    - data/                     — 実行時に利用する DB / pid / flag 等（デフォルト）

---

## 備考 / 注意点

- 本プロジェクトは実際の発注処理に関わるため、`KABUSYS_ENV=live` の設定時は十分に注意してください。validate_config の警告を必ず確認してください。
- .env ファイルは機密情報を含むため、絶対に Git にコミットしないでください。
- OpenAI API を使う機能は API キーが必要で、コストやレート制限に注意してください。API 呼び出し部はリトライやクリップ等の安全策を実装していますが、本番運用前に十分にテストしてください。
- 必須環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）は起動前に設定必須です。

---

この README はソースコードの公開インターフェースと主要な運用ワークフローをまとめたものです。細かい挙動や内部ロジックは各モジュールの docstring や実装コメントを参照してください。必要であれば別途各コンポーネントの詳細ドキュメント（API 使用例や設定サンプル）を作成します。