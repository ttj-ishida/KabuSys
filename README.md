README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ基盤を想定した Python パッケージです。本リポジトリには以下の主要機能が含まれます。
- 発注エンジン（ExecutionEngine）とブローカ抽象化（本番 / ペーパートレードの切替）
- 監視・アラート基盤（System / Trade / Risk Monitor、Kill Switch）
- ポートフォリオ構築（候補選定・配分・リスク調整・株数決定）
- リサーチ機能（ファクター計算、特徴量探索、IC 計算）
- ニュース NLP / レジーム判定（OpenAI を使ったセンチメント評価）
- 運用補助ツール（.env ウィザード、設定検証、Paper Trading 検証レポート等）

主な設計方針
- DB（監視用 SQLite / 分析用 DuckDB）はファイルベースでローカルに保存
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離（data/paper_trading.db）
- OpenAI 等の外部 API はキーを環境変数で与え、失敗時はフォールバックやスキップでフェイルセーフを採用
- 多くのユーティリティはプラットフォーム差分（Windows/Linux）を吸収する実装

機能一覧
--------
- 実行（run_execution.py）
  - ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使い paper_trading DB に記録
  - PID ファイル作成 / 停止フラグ検知（data/stop_requested.flag）
- 監視（run_monitoring.py）
  - SystemMonitor をポーリングして system_status 等を永続化
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視永続化（monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを定義／マイグレーション
- リスク監視（risk_monitor.py）
  - ドローダウン監視・ポジション上限監視とリスクログ記録
- Kill Switch（kill_switch.py）
  - 条件により data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る
- ポートフォリオ（portfolio/）
  - 候補選定、等ウェイト/スコア加重、セクター上限適用、ポジションサイズ計算（単元丸め、利用キャッシュ制御）
- リサーチ（research/）
  - momentum/volatility/value ファクター計算（DuckDB を直接参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI（ai/）
  - news_nlp: raw_news をまとめて OpenAI に投げ、銘柄ごとのスコアを ai_scores に書き込み
  - regime_detector: ETF MA とマクロニュースで市場レジーム（bull/neutral/bear）を判定
- ユーティリティ（utils/）
  - logging_setup: 統一ログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度・CPU affinity の簡易設定
- ツール（tools/）
  - paper_verification_report: Paper Trading DB から運用検証レポートを生成

必要条件
--------
- Python 3.10+（pipe 型注釈や from __future__ の使用を踏まえ推奨）
- 主な依存パッケージ:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config ファイル検証を行う場合に任意）
- SQLite は標準ライブラリで利用

セットアップ手順
--------------
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install -U pip
   - pip install duckdb psutil openai
   - （オプション）pip install pyyaml

3. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成。
     主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_password_here
     - KABUSYS_ENV=development|paper_trading|live  (default: development)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=sk-...

   - 自動ロード: Settings モジュールはプロジェクトルートの .env/.env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - エラーがあると exit(1)。--strict を付与すると警告も FAIL 扱いになります。

使い方（主なコマンド）
--------------------
- ExecutionEngine を起動（デーモン管理は別途）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは PAPER_TRADING_SQLITE_PATH の DB を使用（本番 DB と分離）
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了
    - 停止は data/stop_requested.flag を作成、または ExecutionEngine 側の停止処理を呼ぶ

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を制御（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使ってログを残します

- .env の作成・更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニューススコア／レジーム判定）
  - 関数呼び出しベース（ライブラリ利用）:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY（または引数 api_key）が必須

停止方法・フラグ
----------------
- stop_requested.flag
  - 実行スクリプト（run_execution/run_monitoring）は data/stop_requested.flag の存在を監視してループを終了します。手で作成すると安全に停止できます。
- kill.flag（Kill Switch）
  - kill_switch は条件に応じて data/kill.flag を書き込みます。ExecutionEngine 起動前にこのフラグがあると起動を停止します。
- PID ファイル
  - 実行時に PID ファイル（デフォルト data/execution.pid）を生成しているコンポーネントがあります。プロセス管理で参照できます。
- 起動時の自動クリア
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

ディレクトリ構成
---------------
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py            — パッケージ定義（__version__ 等）
  - config.py              — Settings クラス（環境変数 / .env 読み込み）
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 起動前設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - utils/
    - logging_setup.py     — 統一ロギング設定
    - process_priority.py  — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py     — SQLite テーブル定義と MonitoringDB ラッパ
    - system_monitor.py     — システム・データ鮮度監視
    - trade_monitor.py      — （trade 監視ロジック）
    - risk_monitor.py       — ドローダウン / ポジション上限監視
    - kill_switch.py        — Kill Switch ロジック
    - monitoring_engine.py  — 各モニタを束ねるエンジン
    - alert_manager.py      — （アラート送信ロジック）
  - execution/
    - execution_engine.py   — ExecutionEngine（発注ループ）
    - broker_factory.py     — BrokerClient の生成（本番 / mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py  — 候補選定 / スコアソート
    - position_sizing.py    — 株数計算・aggregate cap
    - risk_adjustment.py    — セクター上限・レジーム乗数
  - research/
    - factor_research.py    — momentum/value/volatility 計算（DuckDB）
    - feature_exploration.py— 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py           — ニュースの OpenAI スコアリング
    - regime_detector.py    — 市場レジーム判定（MA + マクロニュース）
  - data/                   — データファイル（ログ / DB / フラグ等。Git 管理外推奨）
  - config/                 — YAML テンプレート（system_config.yaml 等）

補足 / 運用メモ
---------------
- DB マイグレーション
  - monitoring_db.init_monitoring_db() は idempotent（何度でも安全に実行可）で、既存 DB に対する簡易マイグレーション（カラム追加）を行います。
- ロギング
  - setup_logging() を各起動スクリプトの最初で呼び、stdout と logs/<app>.log（日次ローテート）に出力します。LOG_DIR 環境変数でログ保存先を変更可能。
- Paper Trading
  - KABUSYS_ENV=paper_trading にすると発注は MockBrokerClient（外部 API に影響しない）になり、paper_trading 用 SQLite に記録されます（PAPER_TRADING_SQLITE_PATH で上書き可）。
- OpenAI
  - AI 機能を使うには OPENAI_API_KEY を設定してください。API の呼び出しは冪等性・リトライ・レスポンス検証を考慮して実装されていますが、コストとレート制限の管理は運用側で行ってください。

ライセンス・注意点
-----------------
- .env や API キー、シークレットは絶対に Git にコミットしないでください。
- 本リポジトリのコードは設計サンプルであり、本番運用に移す場合は十分なテスト・監査を実施してください。

以上がプロジェクトの概要・セットアップ・使い方・構成の説明です。必要であれば、README に追記したい具体的なコマンド例や .env のサンプルテンプレートを作成します。どの情報をさらに詳しく出力しますか？