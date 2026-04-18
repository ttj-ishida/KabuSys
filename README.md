# KabuSys

日本株自動売買システム KabuSys の簡易 README（日本語）

概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。開発用に配布される Python パッケージのソース（src/kabusys）を想定しています。

注意: 各種コマンドはパッケージルート（pyproject.toml / .git が存在するプロジェクトルート）で実行してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。主な責務は以下です。

- ExecutionEngine：注文発行・注文管理・リスク管理を行う実行エンジン
- Monitoring：システム状態・注文状況・リスク監視、アラート発行・Kill Switch
- Portfolio construction：銘柄選定、重み算出、ポジションサイズ計算、セクター制限など
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI（OpenAI 経由）：ニュースの NLP スコアリング、レジーム判定
- Tools：ペーパートレード検証レポート等のユーティリティ

設計方針の一部：
- DuckDB / SQLite を利用し、分析 DB と監視/取引ログを分離
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離
- 外部 API 呼び出し（OpenAI 等）は明示的に API キーを与えて使用
- .env による設定、対話式ウィザードと設定検証ツールを提供

---

## 機能一覧（主なモジュール）

- kabusys.run_execution
  - ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し `data/paper_trading.db` に記録
  - 停止はプロジェクトルート/data/stop_requested.flag によるフラグ読み取り
- kabusys.run_monitoring
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- kabusys.config_setup
  - .env を対話式で初期作成/更新するウィザード
- kabusys.validate_config
  - .env と config/*.yaml の基本チェックを行う CLI（--strict オプションあり）
- kabusys.tools.paper_verification_report
  - Paper Trading の検証レポートを生成する CLI（期間指定可）
- kabusys.portfolio.*
  - 銘柄選定、配分計算、セクター制限、ポジションサイズ決定等の純粋関数
- kabusys.research.*
  - ファクター計算（Momentum/Volatility/Value）、将来リターン、IC、統計サマリー
- kabusys.ai.*
  - news_nlp: ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector: ETF とマクロ記事を用いて市場レジーム（bull/neutral/bear）判定
- kabusys.monitoring.*
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db 等
- kabusys.utils.*
  - logging_setup（統一ログ設定）、process_priority（プロセス優先度設定）などのユーティリティ

---

## 必須 / 主要な環境変数

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（よく使うもの）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を利用する場合必須（AI モジュール）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存先ディレクトリ（デフォルト: logs/）

監視・制御に関するファイル:
- data/kill.flag: Kill Switch（監視から ExecutionEngine 停止を命令）
- data/stop_requested.flag: run_execution / run_monitoring の外部停止用フラグ
- data/execution.pid: ExecutionEngine の PID（実行時に使用）

Paper Trading 固有:
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

詳細は `kabusys.config.Settings` のプロパティを参照してください。

---

## セットアップ手順（ローカル）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python 3.10+（Union types, typing 機能を利用）を推奨

2. 依存ライブラリをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（config yaml 検証機能のため任意）
   - 例:
     ```bash
     python -m pip install --upgrade pip
     python -m pip install duckdb psutil openai PyYAML
     ```
   - もし requirements.txt が用意されている場合:
     ```bash
     python -m pip install -r requirements.txt
     ```

3. .env を作成
   - 対話式で作成:
     ```bash
     python -m kabusys.config_setup
     ```
   - 生成された .env は絶対に Git にコミットしないでください。

4. 設定検証
   - 基本チェック:
     ```bash
     python -m kabusys.validate_config
     ```
   - 警告を FAIL 扱いにする（CI 等で使用）:
     ```bash
     python -m kabusys.validate_config --strict
     ```

5. ディレクトリの準備
   - 必要に応じて data/ や logs/ を作成します（logging_setup が自動で作成する場合あり）。
   - kill.flag の自動クリアの設定を行う場合は .env の KILL_FLAG_CLEAR_ON_START を確認。

---

## 使い方（起動例）

- ExecutionEngine を起動（本番 / 紙両対応）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い paper_trading DB に書き込みます。
  - 起動中、プロセス優先度が "high" に設定されます。
  - プロセス停止: プロジェクトルート/data/stop_requested.flag を作成するか、実行プロセスに SIGINT（Ctrl-C）を送る。

- Monitoring を起動（SystemMonitor のポーリング）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
    0 や負の値は無視され、デフォルト 60 秒にフォールバックします。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスはオプション `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能

- AI モジュール（プログラムから利用）
  - ニューススコア算出:
    ```python
    from kabusys.ai import score_news
    # duckdb_conn: duckdb connection, target_date: datetime.date, api_key optional
    score_news(duckdb_conn, target_date, api_key="...") 
    ```
  - レジーム判定:
    - 関数名はモジュール内にあり、duckdb 接続と API キーを渡して呼び出します（詳細はソース参照）。

---

## 運用上の注意点

- Paper Trading と Live は DB が分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH / SQLITE_PATH）。
- Kill Switch（kabusys.monitoring.kill_switch）は drawdown やポジション上限を検出すると data/kill.flag を書き込み、ExecutionEngine に停止指示を送ります。Kill Flag の自動クリアは .env の KILL_FLAG_CLEAR_ON_START で制御できますが、本番では 0（クリアしない）を推奨します。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）が必須です。API 呼び出しに失敗した場合、フェイルセーフ（0.0 等）で継続する設計の箇所が多くありますが、運用上の監視は必要です。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR で変更可能。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定読み込みロジック
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py
  - regime_detector.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (参照: alert 周りの実装がある想定)
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - risk_manager.py
- data/ (想定されるディレクトリ: DB、マスタ等を配置)
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

（上はソースに含まれる主要ファイルを抜粋したものです。実際のリポジトリにより若干差分がある可能性があります。）

---

## 開発・テストについて（補足）

- .env の自動読み込み機能はデフォルトで有効です。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途）。
- DuckDB を使った研究モジュールはローカルの DuckDB ファイル（DUCKDB_PATH）を前提にしています。prices_daily / raw_financials / raw_news 等のテーブルが必要です。
- ユニットテストはモジュールごとに小さな純粋関数として実装されている部分が多く、モックが容易です（OpenAI 呼び出し等は差し替え可能）。

---

README は以上です。必要であればサンプル .env テンプレート、起動/デバッグの詳細手順や各モジュールの API 使用例（関数シグネチャと戻り値例）を追記できます。どの情報を追加希望か教えてください。