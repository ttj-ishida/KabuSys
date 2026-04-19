# KabuSys — 日本株自動売買システム

このリポジトリは、シンプルな日本株自動売買（および検証）フレームワークの一部です。
README は本コードベースに含まれる主要スクリプト・ユーティリティの使い方、セットアップ手順、ディレクトリ構成を日本語でまとめたものです。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提・依存パッケージ
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主要項目）
- 運用上のフラグ / PID ファイル
- トラブルシュート / 注意点
- ディレクトリ構成（ファイル一覧と説明）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコンポーネント群です。  
主な目的は以下:

- 売買執行（ExecutionEngine）と発注管理
- システム監視（Monitoring）と Kill Switch（危険時の停止）
- ポートフォリオ構築（候補選定・重み付け・ポジション決定）
- ファクター計算・リサーチ（DuckDB を用いる分析）
- Paper Trading（ペーパートレード）用の分離された DB と検証レポート
- ニュース NLP / レジーム判定（OpenAI API を利用）

安全性を重視しており、本番（live）環境ではデフォルトの DB を共有しない構成や Kill Switch、各種閾値チェックが組み込まれています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine による発注実行ループ（paper_trading 時は MockBroker を使用）
  - Order/Repository/Reconcilier/RiskManager の組立て
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた監視エンジン
  - DB (SQLite) への監視ログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - Kill Switch（しきい値越えで data/kill.flag を作成）
- Portfolio
  - 候補選定、等重・スコア重み、リスク調整（セクター上限）、ポジションサイズ計算
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC 計算、統計サマリ
- AI（オプション: OpenAI）
  - ニュースから銘柄別センチメントスコアを生成（news_nlp）
  - マクロニュース + ETF MA による市場レジーム判定（regime_detector）
- ツール
  - config_setup.py: .env の対話式ウィザード
  - validate_config.py: 起動前の設定検証 CLI
  - tools.paper_verification_report: Paper Trading の検証レポート生成

---

## 前提・依存パッケージ

主に以下が必要になります（バージョンは適宜指定してください）:

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- sqlite3（標準ライブラリ）
- （オプション）PyYAML — validate_config が config/*.yaml をパースする場合に利用

インストール例（pip）:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローン／展開する

2. 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）
   - pip install -r requirements.txt（requirements.txt がある場合）
   - もしくは上記の個別パッケージを pip でインストール

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - KABUSYS_ENV は development / paper_trading / live のいずれか

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     python -m kabusys.validate_config --strict

5. データディレクトリとログディレクトリの確認
   - デフォルト DB / ファイルパスは .env の DUCKDB_PATH / SQLITE_PATH 等
   - ログはデフォルトで logs/ 配下（設定変更可）

6. OpenAI を使う機能を利用する場合
   - 環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に api_key を渡す

---

## 使い方（主要コマンド）

- .env の作成 / 更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBroker を使用し、Paper 用 DB（デフォルト data/paper_trading.db）に記録されます。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は常に本番の sqlite_path を使用します（環境にかかわらず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- ライブラリ・ユーティリティの呼び出し（プログラム的利用）
  - kabusys.portfolio.select_candidates(...)
  - kabusys.research.calc_momentum(conn, target_date)
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - など

---

## 環境変数（主要項目）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨/よく使う:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant / partial / never / reject（paper_trading 時の挙動）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 本番での自動 kill.flag クリア（0/1。デフォルト 0 を推奨）

注意: .env はセキュアに管理し、Git にコミットしないでください（config_setup.py のヘッダにも注意書きあり）。

---

## 運用上のフラグ / PID ファイル

- stop_requested.flag
  - プロジェクト内 data/stop_requested.flag を作成すると、run_monitoring/run_execution のループが検知して安全にシャットダウンします（run_monitoring はこのファイルを見て終了、ExecutionEngine は検知して停止）。
- kill.flag
  - KillSwitch により作成されるファイル。ExecutionEngine に対する停止シグナル（ExecutionEngine は起動時に kill.flag の存在をチェックし、また定期的に KillSwitch を参照します）。
  - パスは Settings.kill_flag_path（デフォルト data/kill.flag）。
- PID ファイル
  - ExecutionEngine は pid ファイルを data/execution.pid に書きます（Settings.pid_file_path で変更可能）。
  - run_execution の _EXECUTION_PID、run_monitoring の pid_file（Settings を経由）を参照します。

---

## トラブルシュート / 注意点

- ログディレクトリ作成失敗
  - 権限などで logs/ の作成に失敗した場合はコンソール出力のみで継続します（警告が出ます）。ログファイル出力を有効にするにはログディレクトリへの書込権限を確認してください。
- validate_config の YAML チェック
  - PyYAML がインストールされていない場合、config/*.yaml の構文検査はスキップされます（警告）。
- Paper Verification レポート
  - DB ファイルが存在しない場合はエラーになります。--db で正しいパスを指定してください。
- OpenAI API 呼び出し
  - OPENAI_API_KEY を設定していない場合、news_nlp / regime_detector の関数は ValueError を投げます。API 利用時はレート制限や料金に注意してください。
- プロセス優先度
  - run_execution / run_monitoring は起動時に set_process_priority("high") を試みます。権限不足等で設定できない場合は警告のみで続行します。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等的にテーブルと必要カラムを作成／追加します。既存 DB に対するマイグレーション処理も含まれます。

---

## 主要ファイル / ディレクトリ構成

（src/kabusys 以下を想定）

- src/kabusys/__init__.py
  - パッケージ初期化、__version__ 定義

- 実行エントリ
  - src/kabusys/run_execution.py
    - ExecutionEngine を立ち上げるスクリプト。paper_trading の場合は paper DB を使用。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔を指定可能。

- 設定関連
  - src/kabusys/config.py
    - 環境変数 / .env 自動読込、Settings クラス
  - src/kabusys/config_setup.py
    - .env の対話式ウィザード
  - src/kabusys/validate_config.py
    - 起動前の設定検証 CLI

- モニタリング
  - src/kabusys/monitoring/monitoring_db.py
    - SQLite のテーブル作成・永続化 API（MonitoringDB クラス）
  - src/kabusys/monitoring/system_monitor.py
  - src/kabusys/monitoring/trade_monitor.py (存在する想定)
  - src/kabusys/monitoring/risk_monitor.py
  - src/kabusys/monitoring/kill_switch.py
  - src/kabusys/monitoring/monitoring_engine.py
  - src/kabusys/monitoring/alert_manager.py (実装想定)

- 実行（Execution）関連
  - src/kabusys/execution/... (OrderManager, ExecutionEngine, BrokerFactory, etc.) — run_execution が組み立てます

- ポートフォリオ構成
  - src/kabusys/portfolio/portfolio_builder.py
  - src/kabusys/portfolio/position_sizing.py
  - src/kabusys/portfolio/risk_adjustment.py

- リサーチ / ファクター
  - src/kabusys/research/factor_research.py
  - src/kabusys/research/feature_exploration.py

- AI（OpenAI 連携）
  - src/kabusys/ai/news_nlp.py
  - src/kabusys/ai/regime_detector.py

- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - logging の統一セットアップ（stdout + 日次ローテーションファイル）
  - src/kabusys/utils/process_priority.py
    - cross-platform のプロセス優先度設定（psutil 利用）

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading のパフォーマンス/安定性検証レポート生成

- その他
  - data/ ディレクトリ（実行時に DB・フラグファイルを配置）
  - logs/ ディレクトリ（ログファイル。デフォルト）

---

必要に応じて README を拡張します（例: 開発向けのテスト実行例、CI 設定、Docker サポート、細かい設定ファイルの説明など）。追加で欲しい項目があれば教えてください。