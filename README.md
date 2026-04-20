# KabuSys

日本株自動売買システム — モジュール群の README。  
このドキュメントはリポジトリ内の主要スクリプト・設定・ユーティリティの使い方と構成を簡潔にまとめたものです。

> バージョン: 0.1.0 (src/kabusys/__init__.py に準拠)

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的としたPythonパッケージ群です。  
主な役割は以下の通りです。

- 市場データを使ったファクター計算・研究（research）
- 銘柄選定・配分・ポジションサイズ計算（portfolio）
- 実際の発注実行エンジン（ExecutionEngine）と発注管理（execution）
- 監視・アラート・Kill Switch（monitoring）
- AI を使ったニュースセンチメント・レジーム判定（ai）
- 補助ツール（tools）や設定ウィザード（config_setup）など

設計方針として、ルックアヘッドバイアスを避けること、DBや外部API呼び出しを明確に分離すること、失敗耐性（フェイルセーフ）を重視しています。

---

## 機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルートに基づく）
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行（Execution）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClient 抽象化（本番／Mock）
  - RiskManager / OrderManager / Reconciler / ExecutionEngine
- 監視（Monitoring）
  - SystemMonitor, TradeMonitor, RiskMonitor を束ねる MonitoringEngine
  - SQLite 監視DB（monitoring_db）によるログ永続化
  - KillSwitch（条件により data/kill.flag を作成）
  - ポーリングループ起動スクリプト（run_monitoring.py）
- 研究・分析
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、統計サマリ
  - DuckDB を使った高速集計
- AI
  - ニュースの LLM（OpenAI）によるセンチメントスコア化（news_nlp）
  - マクロニュースと ETF MA を用いたレジーム判定（regime_detector）
- ユーティリティ
  - ログ設定ユーティリティ（統一ログ出力／ローテーション）
  - プロセス優先度・CPU affinity 設定ユーティリティ
  - ペーパートレード検証レポート生成（tools.paper_verification_report）

---

## 必要条件（主要依存パッケージ）

最低限インストールが想定されるパッケージ（pipでインストール）:

- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config YAML 検証をしたい場合）
- （標準ライブラリ以外の追加ユーティリティがあれば requirements.txt を参照）

例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。

2. 仮想環境を作成・有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール:
   - pip install duckdb psutil openai PyYAML

4. .env を作成:
   - 対話式ウィザードを推奨:
     ```
     python -m kabusys.config_setup
     ```
     生成後、`.env` ファイルをプロジェクトルートに保存します（絶対に Git にコミットしないでください）。

5. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   警告も失敗扱いにする場合:
   ```
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリの確認:
   - デフォルト DB / ファイルパスは `data/` 以下:
     - SQLite 監視 DB: data/monitoring.db
     - ペーパートレード DB: data/paper_trading.db
     - DuckDB: data/kabusys.duckdb
     - ログ: logs/
   - 必要に応じて `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH`, `LOG_DIR` 等を .env で指定します。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH（例: data/kabusys.duckdb）
- SQLITE_PATH（監視DB、例: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB）
- LOG_LEVEL（DEBUG/INFO/...）
- LOG_DIR（ログ出力先ディレクトリ）
- OPENAI_API_KEY（AI 機能利用時に必要）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時の kill.flag 自動クリア 0/1）

設定は .env（自動ロードあり）か OS 環境変数で行ってください。自動ロードはプロジェクトルートに `.env` / `.env.local` がある場合に動作します。テストで無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（主要コマンド／スクリプト）

- 環境設定ウィザード（対話式 .env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（メイン発注プロセス）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` を利用（本番 DB と分離）。
  - プロセスは data/execution.pid を書きます。停止要求は data/stop_requested.flag を作ることで受け付けます。

- Monitoring ポーリングループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 注: Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path（Settings.sqlite_path）を使用します（監視ログは本番 DB に記録）。
  - 停止はプロジェクトの data/stop_requested.flag を作成します。

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db PATH` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI 機能
  - OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定してください。
  - プログラム的に `kabusys.ai.score_news` / `kabusys.ai.regime_detector.score_regime` を呼び出して使用します。

- ログ設定
  - 共通のログ初期化: `kabusys.utils.logging_setup.setup_logging(app_name="execution")`
  - ログはルートロガーに stdout とファイル（logs/<app_name>.log 日次ローテーション）をセットします。

- Kill Switch / 停止の仕組み
  - KillSwitch は監視やリスク監視結果に基づいて `data/kill.flag` を作成します（ExecutionEngine はこのフラグを見て安全停止する設計）。
  - run_monitoring/run_execution は `data/stop_requested.flag` を監視し、存在する場合はループを終了します（手動停止用のフラグ）。

---

## 開発者向け：プログラミング API（代表的なもの）

- Settings クラス（kabusys.config）
  - settings = Settings()
  - settings.env, settings.is_paper, settings.sqlite_path, settings.duckdb_path, settings.paper_sqlite_path, etc.

- ポートフォリオやポジション計算（kabusys.portfolio）
  - select_candidates(buy_signals, max_positions)
  - calc_equal_weights(candidates)
  - calc_score_weights(candidates)
  - calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices, ...)

- Research（kabusys.research）
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date)
  - calc_ic(factor_records, forward_records, factor_col, return_col)

- AI（kabusys.ai）
  - score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)

- Monitoring DB（kabusys.monitoring.monitoring_db.MonitoringDB）
  - init_monitoring_db(conn)
  - MonitoringDB(conn).log_system_status(...)
  - MonitoringDB(conn).log_trade_event(...)
  - MonitoringDB(conn).upsert_dashboard(...)

---

## よくある運用注意点

- MONITOR_POLL_INTERVAL は正の整数で指定してください。不正な値はデフォルト 60 秒にフォールバックします。
- ペーパートレードと本番 DB は分離する（Settings.is_paper 判定で paper_sqlite_path を利用）。
- OpenAI を利用する機能はネットワーク・料金リスクがあるため、本番での自動実行は慎重に。APIキーは .env で管理。
- .env は決して Git にコミットしないこと。
- ログディレクトリ作成に失敗した場合はコンソールログのみで継続します（ログディレクトリの権限等を確認してください）。
- 実行中の停止は data/stop_requested.flag を作成（監視ループと ExecutionEngine の両方で使用される止めフラグ）。KillSwitch は条件に応じて data/kill.flag を書き込み、これを ExecutionEngine が検出して停止します。

---

## ディレクトリ構成 (主要ファイル)

リポジトリ内の `src/kabusys` を中心とした概観:

- src/kabusys/
  - __init__.py
  - config.py                    — Settings / .env 自動ロード
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                         (通常は runtime に生成される)
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (存在する場合)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
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

（実際のツリーはプロジェクト内での差分あり。上記は主要モジュールの一覧です）

---

## ライセンス・貢献

この README はコードベースの主要機能・運用手順の概要です。テスト・CI、詳細な設計ドキュメントや実装仕様（PortfolioConstruction.md 等）は別途参照してください。  
貢献やバグ報告はリポジトリの Issue を利用してください。

---

必要であれば、この README をベースに「サービス化（systemd/unit）」や「Docker コンテナ化手順」「CI 用 linters/formatters の設定」「より詳細な環境変数リファレンス」など追記します。どの情報を優先して拡張しますか？