# KabuSys

バージョン: 0.1.0

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。  
このリポジトリはトレード実行エンジン、監視/アラート、ファクター計算、ポートフォリオ構築、ニュースNLP などのコンポーネントを含みます。

## 概要

KabuSys は以下の目的で設計されたモジュール群です。

- 株価データ（DuckDB）を用いたリサーチ／ファクター計算
- 発注ロジック（ExecutionEngine）による注文作成・送信（本番 / ペーパー両対応）
- 監視サブシステム（System / Trade / Risk）と Kill Switch による安全停止
- ニュースを LLM（OpenAI）でスコアリングし、レジーム判定やシグナル補助に利用
- ペーパートレードの検証・レポート生成ツール

設計方針として、可能な限り「フェイルセーフ」「ルックアヘッドバイアス回避」「DB・API への読取/書込の分離」を重視しています。

## 主な機能一覧

- Execution
  - ExecutionEngine（本番/ペーパートレード対応）
  - BrokerClientFactory で実環境 or MockBroker を切替
  - 発注ログ・ポジション管理（SQLite / MonitoringDB）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・プロセス死活・データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常検知（ソース内に実装）
  - RiskMonitor：ドローダウン / ポジション数監視と alert ログ記録
  - KillSwitch：条件に応じて data/kill.flag を書き込み Execution を停止
  - MonitoringEngine：定期ポーリングで各 Monitor を統合
- Research / Portfolio
  - ファクター計算（momentum / volatility / value）
  - 特徴量解析（forward returns / IC / summary）
  - ポートフォリオ候補選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数
- AI
  - news_nlp：OpenAI を使ったニュースセンチメント（ai_scores テーブルへ書込）
  - regime_detector：ETF MA とマクロニュースを合成した市場レジーム判定
- Utilities / Tools
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report）
  - logging_setup、process_priority ユーティリティ

## セットアップ手順

前提:
- Python 3.9+（パッケージの互換性に応じて調整してください）
- SQLite は Python に同梱
- DuckDB を使用するのでシステムに duckdb パッケージが必要

推奨手順（Unix 系の例）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb openai psutil
   - 任意: pip install pyyaml （validate_config が YAML 検証を行う場合に必要）

   例:
   ```
   pip install duckdb openai psutil pyyaml
   ```

3. .env 作成（推奨）
   - 対話式ウィザードで作る:
     ```
     python -m kabusys.config_setup
     ```
   - 手動で作る場合はリポジトリルートに `.env` を置き、`.env.example` を参考に必要な値を設定してください。

4. 設定検証（起動前に実行推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの確認
   - デフォルトで以下ファイル / ディレクトリが使用されます（必要に応じて .env で上書き）
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログ: logs/
     - フラグ / PID: data/kill.flag, data/stop_requested.flag, data/execution.pid

## 必須環境変数（最小）

- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

その他、主要な環境変数（代表例）:
- KABUSYS_ENV: development | paper_trading | live（挙動切替）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB）
- OPENAI_API_KEY（news_nlp / regime_detector で使用）
- LOG_LEVEL（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、デフォルト 60）

## 使い方

起動スクリプト（パッケージモジュール経由）:

- 実行エンジン（ExecutionEngine）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 実行中に data/stop_requested.flag が作成されると安全に停止します。
  - 実行時に data/execution.pid を書きます。

- 監視ループを起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（デフォルト 60）。
  - 監視は monitoring DB（SQLite）を使用し、KABUSYS_ENV に関係なく本番 sqlite_path を参照します。
  - 停止は data/stop_requested.flag を置くことで行います（または KeyboardInterrupt）。

ツール:
- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で別 DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定できます。

AI / リサーチ呼び出し（ライブラリ関数）:
- ニューススコアリング:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- ファクター計算:
  - kabusys.research.calc_momentum(conn, date)
  - kabusys.research.calc_volatility(conn, date)
  - kabusys.research.calc_value(conn, date)

注意事項:
- OpenAI API を使う処理は APIキーが必要です。API失敗時はフェイルセーフ挙動（スコア0やスキップ）を取る実装です。
- KABUSYS_ENV=development は「発注なし（ローカル開発）」を想定。設定により発注の有無が変わります。必ず実行前に validate_config で確認してください。
- kill.flag / stop_requested.flag / kill_flag_clear_on_start の設定に注意してください（本番環境で自動クリアは危険です）。

ログ:
- logs/<app_name>.log （起動時に setup_logging で設定）
- コンソール出力は stdout に出ます（stderr ではない点に注意）

停止フロー:
- 実行エンジンを安全に停止させるには監視側（KillSwitch）で data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります。
- 即時停止（テスト用など）には data/stop_requested.flag を作成することで run_* スクリプトは起動直後に検出して終了します。

## ディレクトリ構成（主要ファイル・モジュール）

ルート: src/kabusys 以下の主要ファイルを示します（一部抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス、自動 .env 読込ロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成・読み書きユーティリティ）
    - system_monitor.py
    - trade_monitor.py       (存在: ロジックを参照)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       (存在: アラート送信ロジック)
  - execution/
    - execution_engine.py    (Engine 本体)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
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
  - data/                    — デフォルトの DB / フラグファイル配置（実行時に作成される）
  - logs/                    — デフォルトログ保存先（起動時に作成）

（上記に記載のない補助モジュールやファイルが他にもあります。詳細はコードベースを参照してください。）

## よくある操作例

- .env を作成して検証まで行う:
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- ペーパートレードでエンジンを起動:
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- 監視プロセスをデフォルト 60s で起動:
  ```
  python -m kabusys.run_monitoring
  ```

- ポーリング間隔を 30 秒に変更:
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- Paper Trading レポートを生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

## 開発メモ / 注意点

- DuckDB 接続は research / ai モジュールで多用します。大容量データ処理では DuckDB のパフォーマンスを活かしてください。
- Logging は全体で統一的に setup_logging を使ってください（ファイルローテーション / stdout 出力の制御を統一するため）。
- process_priority.set_process_priority はプラットフォーム依存の差分を吸収しますが、権限不足で失敗することがあるため警告扱いになります。
- OpenAI 呼び出し部分はリトライ・バックオフ・パース保護などのフェイルセーフを備えていますが、API コストとレート制限に注意してください。
- 本番環境（KABUSYS_ENV=live）では kill_flag_clear_on_start を 0 にしてください（自動クリアは危険）。

---

README に記載のない詳細な API 仕様や内部ロジック（ExecutionEngine の仕様、OrderRepository、アラート送信の実装など）は各モジュールの docstring を参照してください。質問やドキュメント補足が必要であれば教えてください。