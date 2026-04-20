# KabuSys

日本株向け自動売買・リサーチ基盤のモジュール群です。  
このリポジトリはトレード実行、監視、ポートフォリオ構築、ファクター計算、ニュース NLP、各種ユーティリティを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- 実際の発注（kabuステーション API）およびペーパートレードの実行エンジン
- システム稼働・発注・リスクの監視（kill switch を含む）
- ポートフォリオ構築（銘柄選定・重み算出・サイズ決定）
- 研究用ファクター計算・特徴量探索（DuckDB を使用）
- ニュースの LLM ベースセンチメント（OpenAI）を用いたスコアリング
- 環境設定ウィザード、設定検証ツール、ペーパートレード検証レポート等の補助ツール

設計方針の一例：
- 本番とペーパートレード用 DB を分離
- ルックアヘッドバイアスを避ける実装（date/datetime の扱いに注意）
- 外部 API 呼び出し（OpenAI 等）は明示的にキーを要求し、安全にリトライ・フォールバックする

---

## 主な機能一覧

- run_execution.py: ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に記録。
- run_monitoring.py: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL で間隔を変更可能。
- monitoring/*: 監視用ロジック（system, trade, risk, kill_switch, monitoring_engine, DB 永続化）。
- portfolio/*: 候補選定、重み計算、セクター制限、リスク調整、株数決定ロジック。
- research/*: ファクター計算（momentum/value/volatility）、特徴量探索、IC 計算等（DuckDB を利用）。
- ai/*: ニュース NLP（OpenAI）による銘柄別スコアリング、レジーム検出（MA + LLM 合成）。
- tools/paper_verification_report.py: ペーパートレード検証レポート生成（期間指定可）。
- config_setup.py: .env を対話式に生成・更新するウィザード。
- validate_config.py: .env と config/*.yaml の整合性チェック CLI。
- utils/*: ロギング設定、プロセス優先度 / CPU affinity 設定など共通ユーティリティ。

---

## セットアップ手順

前提: Python 3.9+（パッケージの typing 等に依存）。DuckDB, psutil, openai などが必要な機能に応じてインストールしてください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（任意）と依存インストール
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -e .            # setup.py / pyproject.toml がある場合
   # 必要に応じて個別に:
   pip install duckdb psutil openai PyYAML
   ```

3. 環境変数（.env）を作成
   - 対話式ウィザードを使う（推奨）:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードはデフォルトや既存 .env を読み込み、.env を生成します。
   - 自動読み込みについて:
     - デフォルトではプロジェクトルートの `.env` および `.env.local` を自動で読み込みます。
     - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合
   python -m kabusys.validate_config --strict
   ```

5. ログディレクトリ
   - デフォルトは `logs/`。`LOG_DIR` 環境変数で変更可。
   - ログは日次ローテーション（30日保持）されます。

---

## 主な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 本番で誤って kill.flag を自動クリアすることを防ぐためデフォルト 0

注意: `.env` は絶対にリポジトリにコミットしないでください（config_setup もその旨を警告します）。

---

## 使い方（主要コマンド）

- 実行エンジン（ExecutionEngine）を起動
  - 本番 / 開発 / ペーパートレードの挙動は `KABUSYS_ENV` に依存します。
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` を使用します。

- 監視プロセスを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します。
  - 停止: プロジェクトルート `data/stop_requested.flag` を作成すると、ループが検知して終了します。

- .env ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール（プログラムから呼び出す）
  - ニュース NLP スコアリング:
    - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - `OPENAI_API_KEY` または引数 `api_key` が必要
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 停止 / Kill switch

- stop_requested.flag (data/stop_requested.flag)
  - run_monitoring.py / run_execution.py のループはこのファイルの存在を監視しており、存在すれば安全に終了します。
- kill.flag (Settings.kill_flag_path / data/kill.flag)
  - KillSwitch がトリガー条件になった場合に作成され、ExecutionEngine に停止シグナルを送ります（ExecutionEngine 側は kill.flag を検知して停止処理を行います）。
  - 本番での誤操作を防ぐため `KILL_FLAG_CLEAR_ON_START` をデフォルト 0 にして自動クリアを抑止することが推奨されます。

---

## ロギング / デバッグ

- ロギングの初期化は各スクリプトで `setup_logging(app_name=...)` を呼び出します。
- デフォルトログディレクトリ: `logs/`。個別アプリは `logs/execution.log` / `logs/monitoring.log` 等を生成します。
- `LOG_LEVEL` 環境変数でログ出力レベルを制御できます。

---

## 注意事項 / 運用上のポイント

- Paper trading と本番 DB を分離しているため、KABUSYS_ENV=paper_trading の際はデータが本番 DB を汚染しません。
- AI（OpenAI）呼び出しはネットワーク障害やレート制限を考慮してリトライ・フォールバックが入っていますが、API キー管理は運用側で厳重に行ってください。
- MonitoringDB （SQLite）は起動時に必要なテーブルの作成・マイグレーションを行います。既存 DB に column が足りない場合は自動追加処理が走ります（例: trade_logs.latency_ms, dashboard.peak_value）。
- process priority 設定: 起動時に `set_process_priority("high")` を呼びます。OS によっては権限不足で設定が失敗する場合があります（警告でスキップ）。

---

## ディレクトリ構成

パッケージ内の主要ファイル・ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数読み込み・Settings
    - config_setup.py          # .env 対話式ウィザード
    - validate_config.py       # 設定検証 CLI
    - run_execution.py         # ExecutionEngine 起動スクリプト
    - run_monitoring.py        # SystemMonitor ポーリング起動スクリプト
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
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
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/ (実行時に使用／作成されることが多い)
      - monitoring.db (デフォルト SQLite)
      - paper_trading.db
      - stop_requested.flag
      - execution.pid
    - logs/ (ロギング出力先)

config ディレクトリ（リポジトリルート /config）:
- system_config.yaml
- data_config.yaml
- strategy_config.yaml
- risk_config.yaml
- execution_config.yaml
- monitoring_config.yaml

（validate_config はこれら YAML の存在・パースもチェックします。PyYAML 未インストール時はパースチェックをスキップします）

---

## 開発・テストに関する補足

- 環境自動ロードを無効化する場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- テスト時に外部 API 呼び出しをモックする場合、モジュール内の `_call_openai_api` 等を patch して差し替える設計になっています。
- DuckDB 接続（research / ai モジュール）は明示的に渡す形（依存注入）になっており、テスト時はメモリ DB を作って渡せます。

---

README に書かれていない詳細や、特定モジュールの API ドキュメント（関数引数や戻り値の詳細）が必要でしたら、どのモジュールについて深掘りするか教えてください。必要に応じてサンプルコードや運用手順（サービス化 / systemd / supervisor など）も作成します。