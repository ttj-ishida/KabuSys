# KabuSys

日本株向け自動売買システムのコアライブラリ群です。本リポジトリは取引実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ用ファクター計算、ニュースNLP（LLM）連携などの主要コンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 実際の発注/ペーパートレードを切り替え可能な ExecutionEngine
- システム稼働率・データ鮮度・注文状態・リスク（ドローダウン・ポジション数）監視
- Kill Switch（条件に応じて実行エンジン停止フラグを書き込む仕組み）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定、セクター上限等）
- DuckDB を用いたファクター計算 / リサーチ機能
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価・市場レジーム判定
- CLI ツール: 環境設定ウィザード、設定検証、Paper Trading レポート生成 等

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading と Live を環境で切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカー抽象化（MockBroker を含む）
  - 注文履歴、ポジション永続化（SQLite）

- Monitoring / Risk
  - SystemMonitor：CPU/メモリ/ディスク、実行プロセス存在、データ鮮度監視
  - TradeMonitor：滞留（stale）注文や約定異常の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch：条件により data/kill.flag を書き込んで ExecutionEngine 停止
  - MonitoringEngine：複数モニタの統合ポーリングループ（run_monitoring.py）

- Portfolio
  - 銘柄選定・スコア順ソート（select_candidates）
  - 等金額・スコア加重の重み付け（calc_equal_weights / calc_score_weights）
  - ポジションサイズ算出（リスクベース／等配分）と lot 単位丸め
  - セクター制約・レジーム乗数適用

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（情報係数）計算、ファクター統計

- AI（LLM）
  - ニュース記事の銘柄別センチメントを LLM で評価し ai_scores へ格納（news_nlp）
  - マクロニュース + ETF MA を用いた市場レジーム判定（regime_detector）

- ユーティリティ
  - 環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
  - 統一ロギング設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）

---

## 必要条件 / 推奨環境

- Python 3.10+
- 必要なパッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML の中身検証を行う場合）
- 標準ライブラリ: sqlite3, threading, logging, datetime 等

（実運用時は依存関係を requirements.txt にまとめてください）

インストール例:
```bash
python -m pip install "duckdb" "psutil" "openai" "PyYAML"
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン / 展開
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb psutil openai PyYAML
   ```
4. 環境変数設定
   - 対話式ウィザードを使って .env を生成
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは .env を手動で作成（.env.example を参照してください）

5. 設定検証（必須項目が揃っているか確認）
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 主要環境変数（抜粋）

- 必須（稼働に必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading 時は MockBrokerClient を使い、data/paper_trading.db に記録
- DB パス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OpenAI
  - OPENAI_API_KEY（news_nlp / regime_detector で使用）
- ログ
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
- Monitoring
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、デフォルト 60）
- その他
  - PAPER_FILL_MODE（paper_trading の注文約定挙動: instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか。1=クリア, 0=そのまま）

注意: Settings モジュールは自動で .env / .env.local を読み込みます（OS 環境変数 > .env.local > .env）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（起動・操作例）

- 環境ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine を起動（本番 / paper_trading の挙動は KABUSYS_ENV に依存）
  ```bash
  python -m kabusys.run_execution
  ```
  - 起動時に data/stop_requested.flag が存在する場合は起動をスキップします。
  - 実行中は data/execution.pid に PID を出力します。
  - 停止は data/stop_requested.flag を作成する（Monitoring などが行う）か、プロセスに SIGINT。

- Monitoring（監視ループ）を起動
  ```bash
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）。
  - 監視は Settings.sqlite_path（本番監視 DB）を常に使用します（env に依存しない）。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # デフォルト DB は data/paper_trading.db。--db で指定可能。
  ```

---

## Kill Switch / 停止フロー概略

- RiskMonitor や MonitoringEngine の判定により KillSwitch.evaluate() がトリガーされると、data/kill.flag に理由を書き込みます。
- ExecutionEngine は起動時に kill.flag のクリア設定（KILL_FLAG_CLEAR_ON_START）を確認し、起動中に kill.flag の存在を検知すると安全に停止する仕組みになっています。
- data/stop_requested.flag は run_execution/run_monitoring の停止トリガーとして使われます（監視ループと実行スレッドの停止制御）。

---

## ログ

- 共通のログ設定ユーティリティ（kabusys.utils.logging_setup）を通じて、
  - コンソール（stdout）出力
  - 日次ローテーションファイル（logs/<app_name>.log、30日保持）
- LOG_DIR 環境変数でディレクトリを変更可能。
- 各起動スクリプトは setup_logging(app_name=...) を呼び出してログを統一します。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリの主要モジュール / ファイル構成の概観です。

- src/kabusys/
  - __init__.py
  - config.py                        # 環境変数 / .env 読み込み・Settings
  - config_setup.py                  # 対話式 .env ウィザード
  - validate_config.py               # 設定検証 CLI
  - run_execution.py                 # ExecutionEngine 起動スクリプト
  - run_monitoring.py                # SystemMonitor ポーリング起動スクリプト

  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py

  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py

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

  - utils/
    - logging_setup.py
    - process_priority.py

- data/                              # 実行時に使うファイル群（DB, pid, flags 等）
  - monitoring.db (デフォルト)       # SQLite 監視 DB
  - paper_trading.db (paper_trading)
  - kabusys.duckdb (DuckDB)
  - execution.pid
  - kill.flag
  - stop_requested.flag

- logs/                              # ログ出力先（LOG_DIR）

---

## 開発メモ / 注意点

- DB マイグレーション: monitoring_db.init_monitoring_db() は冪等にテーブル・カラムを作成・追加します。既存 DB からのマイグレーション処理が一部含まれます（例: trade_logs.latency_ms, dashboard.peak_value の追加）。
- DuckDB は分析処理（research、ai のテーブル読み込み）に使います。高負荷なクエリの実行や LLM 呼び出しの前処理に適しています。
- OpenAI API 呼び出しは外部ネットワークに依存するため、API エラーに対するリトライ（指数バックオフ）やフェイルセーフ（失敗時はスキップ or 0 フォールバック）を組み込んでいます。
- process_priority.set_process_priority() により起動スクリプトはなるべく高優先度で実行されますが、環境によっては権限不足で失敗する場合があります（警告ログが出ます）。
- Python バージョンは 3.10 以上を推奨（型注釈に | を使用）。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Execution 起動
  ```bash
  python -m kabusys.run_execution
  ```

- Monitoring 起動
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースの主要機能と使い方の導入を目的としています。より詳細なドキュメント（設計文書、マニュアル、運用手順、config/*.yaml の仕様など）は別途参照してください。必要であれば、運用チェックリストやデプロイ手順を追加で作成します。