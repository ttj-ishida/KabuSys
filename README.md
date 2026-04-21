KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株向け自動売買システム「KabuSys」のコアライブラリと起動スクリプト群を含みます。
以下はコードベース（src/kabusys 以下）の README です。起動手順、主要機能、ディレクトリ構成などを日本語でまとめています。

プロジェクト概要
----------------
KabuSys は日本株の自動売買を目的としたモジュール群です。主な責務は以下の通りです。
- 注文実行エンジン（ExecutionEngine）の起動・運用（本番 / ペーパートレード対応）
- システム監視・アラート・Kill Switch（監視コンポーネント）
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイジング）
- リサーチ用ファクター・特徴量計算（DuckDB を用いた分析）
- ニュース NLP（OpenAI を使ったニュースセンチメント評価）および市場レジーム判定
- 各種ユーティリティ（ログ設定、プロセス優先度、設定ウィザード、設定検証、レポート生成）

主な特徴（機能一覧）
------------------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / paper_trading を切り替え可能。paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db に出力して本番 DB と分離。
  - 起動時にプロセス優先度を high に設定。
  - ストップは data/stop_requested.flag や kill.flag（Kill Switch）で制御。

- Monitoring（run_monitoring.py, monitoring/*）
  - SystemMonitor, TradeMonitor, RiskMonitor を組み合わせた MonitoringEngine を提供。
  - システム（CPU/メモリ/ディスク）やデータ鮮度、ポジション状況、ドローダウン監視。
  - KillSwitch により閾値超過時に data/kill.flag を作成して ExecutionEngine に停止信号を発行。
  - 監視ログは SQLite（デフォルト: data/monitoring.db）へ永続化。

- ポートフォリオ構築（portfolio/*）
  - 銘柄選定（スコアソート）、等配分 / スコア比率配分、リスク調整（セクターキャップ、レジーム乗数）、単元株丸めを含むポジションサイズ計算。

- リサーチ（research/*）
  - DuckDB 接続を受けてファクター（モメンタム、ボラティリティ、バリュー）、将来リターン、IC 計算、統計サマリーを実行。
  - 外部 API に依存せず分析処理を行う設計。

- AI（ai/*）
  - news_nlp: OpenAI を用いたニュース記事のセンチメント評価（ai_scores テーブルへ書込）。
  - regime_detector: ETF（1321）とマクロニュースを合成して市場レジームを判定し DB に保存。
  - API 呼び出しは堅牢に設計され、リトライ・タイムアウト・フォールバックが実装。

- ユーティリティ
  - 設定ウィザード（config_setup.py）: 対話式で .env を生成・更新
  - 設定検証 CLI（validate_config.py）: .env と config/*.yaml の簡易チェック
  - ログ設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度と CPU affinity 設定（utils/process_priority.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

セットアップ手順
----------------
前提
- Python 3.10 以上（型ヒントで | を使用しているため）
- SQLite（標準ライブラリ）
- DuckDB、psutil、openai などの外部パッケージ

推奨インストール手順（例）
1. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - pip install duckdb psutil openai
   - optional: pip install pyyaml （validate_config の YAML 検証を有効にする場合）

   （requirements.txt がある場合は pip install -r requirements.txt を使用してください）

3. プロジェクトルートに .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動で .env をプロジェクトルートに配置（.env.example を参考に記述）

4. 設定の検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使用する場合に必要
- LOG_LEVEL: ログレベル（例: INFO）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject）

使い方（代表的なコマンド）
------------------------

- 設定ウィザード（.env を生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine（注文実行エンジン）起動
  - 簡単起動: python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading のときはペーパートレード DB を使用（data/paper_trading.db）
    - 起動時に data/stop_requested.flag が存在する場合は自動終了
    - 終了方法: data/stop_requested.flag を作成すると実行中スレッドが検出して停止します

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - Monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を使って監視ログを記録します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI スコアリング / レジーム判定（プログラムから呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)
  - これらは DuckDB 接続を受け取り、結果をテーブルへ保存します。OPENAI_API_KEY が必要です。

停止・Kill フラグについて
- 実行中のエンジンやモニタはプロジェクト内の data/stop_requested.flag を監視して安全に停止します（run_execution/run_monitoring）。
- KillSwitch（監視側）が危険条件を検出すると data/kill.flag を作成します。ExecutionEngine はこれを検知して停止する仕組みです。
- 実運用では KILL_FLAG_CLEAR_ON_START の設定に注意してください（本番では 0 推奨）。

ログについて
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリに出力）。
- コンソール（stdout）にも出力されます。LOG_DIR 環境変数でログ保存先を変更できます。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 以下の主なファイル・ディレクトリ（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード機能あり）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル定義・MonitoringDB クラス）
    - system_monitor.py      — システム / データ鮮度チェック
    - trade_monitor.py       — （省略）取引監視ロジック
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — Kill Switch（data/kill.flag 書込）
    - monitoring_engine.py   — 各 Monitor 組合せとポーリング管理
    - alert_manager.py       — （省略）アラート送信管理
  - execution/
    - execution_engine.py    — ExecutionEngine（エンジン本体）
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文永続化
    - reconciler.py          — 発注状態整合
    - risk_manager.py        — 発注前リスクチェック
  - portfolio/
    - portfolio_builder.py   — 銘柄選定・スコアソート
    - position_sizing.py     — 株数決定・集計キャップ
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC /統計サマリ
  - data/                    — （実行時に使用されるデータ・DB ファイル等を配置）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py            — ニュースのセンチメント評価（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + ETF 指標）

補足・運用上の注意
------------------
- .env は機密情報を含むため Git へコミットしないでください（config_setup.py のヘッダでも注意喚起あり）。
- OpenAI を利用する機能は API 使用料が発生します。API キーの管理に注意してください。
- 実運用（KABUSYS_ENV=live）の場合は validate_config で警告・必須項目を確認してください（LINE 通知の設定など）。
- DuckDB/SQLite のファイルパスは Settings 経由でカスタマイズ可能です。デフォルトは data/ 配下です。
- psutil によるプロセス優先度設定は権限によって失敗する可能性があります（ログに warning が出ます）。

ライセンス・貢献
----------------
- この README ではライセンス・貢献フローは記載していません。必要に応じてプロジェクトルートに LICENSE、CONTRIBUTING を追加してください。

以上がコードベースの概観と使い方のまとめです。必要ならば README をさらに拡張してインストール要件ファイル（requirements.txt）や具体的な運用手順（systemd/cron のサービス定義、ログローテーション設定、バックアップ方針等）を追記できます。どの項目を詳しく追加しますか？