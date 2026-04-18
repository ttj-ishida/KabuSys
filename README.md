KabuSys
=======

日本株向け自動売買 / リサーチ基盤（モジュール群）です。  
このリポジトリは取引エンジン（Execution）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、LLM を使ったニュース NLP 等のユーティリティを含むモジュール群で構成されています。

主な特徴
--------
- 実行エンジン（ExecutionEngine）と監視ループ（Monitoring）を別プロセスで実行可能
- Paper Trading（モックブローカー）と Live（実ブローカー）を環境変数で切替え可能
- DuckDB / SQLite を用いたデータ格納・ファクター計算（research）機能
- ニュースの LLM（OpenAI）を用いたセンチメントスコアリングおよび市場レジーム判定
- ログ設定・プロセス優先度設定などの運用ユーティリティ
- 設定ウィザード（.env）と設定検証 CLI を備え、起動前チェックをサポート

機能一覧
--------
- run_execution.py — ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録
  - 停止フラグ（data/stop_requested.flag）による停止監視
  - PID ファイル管理（data/execution.pid）
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き（デフォルト 60 秒）
  - 監視ログは monitoring 用 SQLite に永続化（init_monitoring_db）
  - 停止フラグ（data/stop_requested.flag）でループ終了
- config_setup.py — .env 対話式作成ウィザード
- validate_config.py — .env と config/*.yaml の起動前検証 CLI
- tools/paper_verification_report.py — Paper Trading の検証レポート生成
- monitoring/* — 監視用コンポーネント
  - monitoring_db: SQLite スキーマ作成 / CRUD
  - system_monitor: システムリソース・データ鮮度・実行プロセス監視
  - risk_monitor: ドローダウン・ポジション上限の監視
  - kill_switch: 条件により data/kill.flag を書き込み ExecutionEngine に停止シグナル
  - monitoring_engine: 監視コンポーネントの統合
- portfolio/* — 銘柄選定・重み付け・ポジションサイズ計算（純粋関数）
- research/* — DuckDB を用いたファクター計算・特徴量解析
- ai/*
  - news_nlp: OpenAI を使った銘柄単位ニュースセンチメント（ai_scores へ書き込み）
  - regime_detector: ETF + マクロ記事を組み合わせた市場レジーム判定
- utils/*
  - logging_setup: 統一的なログ設定（stdout と 日次ローテーションファイル）
  - process_priority: プラットフォーム対応のプロセス優先度 / CPU affinity 設定

セットアップ手順
----------------

1) Python 仮想環境の作成（推奨）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2) 依存パッケージのインストール
   - 明示的な requirements.txt は提供していませんが、主に以下が必要です:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（設定ファイル検証を行う場合、validate_config の YAML 検証用）
   - 例:
     - pip install duckdb psutil openai pyyaml

3) プロジェクトルートで .env を準備
   - 対話式生成:
     - python -m kabusys.config_setup
   - 生成後、設定確認:
     - python -m kabusys.validate_config
     - 警告を全てエラー扱いにしたい場合: python -m kabusys.validate_config --strict

4) データディレクトリ作成（必要に応じて）
   - デフォルトで下記ファイルが期待されます（.env で上書き可能）
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (SQLite 監視 DB)
     - data/paper_trading.db (Paper Trading 用 SQLite)
     - logs/ （ログディレクトリは自動作成されますが権限等の理由で失敗する場合あり）
   - 初回起動時に init_monitoring_db() がテーブルを作成します。

5) OpenAI を使う場合
   - 環境変数 OPENAI_API_KEY を設定してください（ai/news_nlp.py, ai/regime_detector.py が参照）

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — デフォルト: INFO
- OPENAI_API_KEY — LLM 機能利用時に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート（任意）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- PID_FILE_PATH / KILL_FLAG_PATH — デフォルトパスは Settings で定義

使い方（よく使うコマンド）
-------------------------

- 設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定するとモックブローカーを使用し paper_trading DB に記録されます。
  - 実行中に data/stop_requested.flag を作成するとエンジンを停止します（run_execution は定期的にそのフラグを監視）。

- Monitoring 起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  （ポーリング 30 秒）
  - 監視は Settings.sqlite_path（本番 sqlite）を使用してログを永続化します（KABUSYS_ENV に依らず本番 DB を参照する点に注意）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- ログ設定
  - すべての起動スクリプトは内部で kabusys.utils.logging_setup.setup_logging を呼び出します。デフォルトは logs/<app_name>.log（日次ローテーション）と stdout。

停止・Kill スイッチ
-------------------
- 実行プロセスの停止指示:
  - 管理者が「kill switch」を発動する場合、KillSwitch が data/kill.flag を書き込みます。ExecutionEngine は kill.flag の存在を検知して停止できます（kill.flag は Settings.kill_flag_path で指定可能）。
  - 監視停止指示（run_monitoring / run_execution のループ停止）:
    - data/stop_requested.flag を作成すると両スクリプトはループを抜けて終了します。

注意点・運用メモ
----------------
- run_monitoring は MONITOR_POLL_INTERVAL によるポーリング間隔の制御をサポート（環境変数で上書き可能）。不正な値はデフォルト 60 秒にフォールバックします。
- Monitoring は環境に関わらず Settings.sqlite_path（本番用 monitoring.db）を使用します。Paper Trading 実行の DB は run_execution が切り替える設計です（settings.is_paper 判定で paper_sqlite_path を使用）。
- AI（OpenAI）を使う機能は API 呼び出しに失敗した場合にフォールバックする設計（例：macro_sentiment=0.0、部分的失敗でも他コードのデータは保護）になっていますが、API コストとエラーを考慮して運用してください。
- validate_config は .env だけでなく config/*.yaml の存在と（PyYAML があれば）パースの検証も行います。

ディレクトリ構成
----------------
以下は主要ファイル・ディレクトリの概略です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - config.py                  — Settings クラス（環境変数ラッパー）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポートツール
  - ai/
    - __init__.py
    - news_nlp.py               — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py        — 市場レジーム判定（ETF + LLM）
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ / DB 操作ラッパー
    - system_monitor.py        — システム状態・データ鮮度監視
    - risk_monitor.py          — ドローダウン / ポジション監視
    - trade_monitor.py         — （発注ログ監視。コードベースに実装あり）
    - kill_switch.py           — kill.flag 書き込みユーティリティ
    - monitoring_engine.py     — 各 Monitor を束ねる実行エンジン
    - alert_manager.py         — （アラート送信ロジック）
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み付け
    - position_sizing.py       — 株数決定・スケーリング
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - research/
    - factor_research.py       — Momentum/Value/Volatility 等の計算（DuckDB）
    - feature_exploration.py   — IC / forward returns / 統計サマリー
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - monitoring/... (上記の通り)

補足
----
- 各モジュールはドキュメント文字列とコメントで振る舞いや設計方針が説明されています。実運用前に config_setup + validate_config を実行して設定を確認してください。
- 本 README はリポジトリに含まれるコードから主要点を抜粋した導入ガイドです。細かい動作は各モジュールの docstring や実装コメントを参照してください。

質問や追加してほしい説明（例: ExecutionEngine の詳細な起動フロー、テスト方法、CI 設定例など）があれば教えてください。必要に応じて README を拡張します。