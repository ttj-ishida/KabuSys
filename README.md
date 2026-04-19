KabuSys
=======

日本株自動売買システム（ライブラリ/実行スクリプト群）の簡易ドキュメントです。  
本リポジトリはトレード実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AIベースのニュース評価などを含むモジュール群で構成されています。

概要
----
KabuSys は日本株向けの自動売買システム基盤です。主な責務は以下の通りです。

- 発注実行（ExecutionEngine） — 実口座／ペーパートレードを切替可能
- 監視（Monitoring） — システム状態、注文状態、リスク（ドローダウン・ポジション上限）をポーリングしてログ・アラートを生成
- ポートフォリオ構築（Portfolio） — 候補選定・重み付け・ポジションサイズ決定等の純関数群
- リサーチ（Research） — DuckDB を用いたファクター算出・特徴量探索
- AI モジュール（AI） — OpenAI を用いたニュースセンチメント評価 / レジーム判定
- ユーティリティ — ログ設定、プロセス優先度設定、設定ウィザード、設定検証ツール 等

主な機能一覧
-------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードを使用）
  - run_monitoring.py: SystemMonitor をポーリング起動（監視ループ）
- 設定関連
  - config_setup.py: .env を対話式に作成・更新するウィザード
  - validate_config.py: 環境変数・config/*.yaml の事前検証 CLI（--strict あり）
  - config.Settings: 環境変数ラッパー（多くのデフォルト値と検証ロジックを含む）
- 監視（monitoring）
  - system_monitor: CPU/メモリ/ディスク・プロセスの監視とデータ鮮度チェック
  - trade_monitor: 注文滞留・約定異常検出（コード中に該当モジュールあり）
  - risk_monitor: ドローダウン・ポジション上限チェック、リスクイベントの記録
  - kill_switch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止させる
  - monitoring_engine: 各 Monitor を束ねてポーリング・アラート送出
  - monitoring_db: SQLite を使った監視ログ永続化層（テーブル作成・マイグレーション含む）
- ポートフォリオ（portfolio）
  - 銘柄候補選定、等金額/スコア重み、リスク調整（セクター上限・レジーム乗数）、ポジションサイズ算出
- リサーチ（research）
  - ファクター計算（momentum/value/volatility）、将来リターン計算、IC 計算、統計サマリ
- AI（ai）
  - news_nlp: raw_news を LLM（gpt-4o-mini）でセンチメント評価して ai_scores に保存
  - regime_detector: ma200 とマクロニュースの LLM 評価を合成して日次の market_regime を判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成（期間指定可）

セットアップ手順
----------------
前提
- Python 3.10+ が必要（型注釈で | を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- 仮想環境作成例:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

インストール例
- 必要なパッケージをインストール:
  - pip install duckdb psutil openai pyyaml

環境変数（.env）
- プロジェクトルートに .env を置くか、config_setup.py を使って作成します:
  - python -m kabusys.config_setup
- 主要な環境変数（抜粋とデフォルト）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV: development | paper_trading | live (default: development)
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用 DB)
  - LOG_LEVEL: INFO
  - OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能使用時）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用、既定 60）

設定検証
- 作成後に validate_config を実行してチェック:
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

使い方（起動・操作）
--------------------

1) 監視ループの開始
- デフォルトでは MONITOR_POLL_INTERVAL=60 秒
- 起動:
  - python -m kabusys.run_monitoring
- 停止:
  - プロジェクト data ディレクトリ内に stop_requested.flag を作成すると安全にループが終了します（run_monitoring/run_execution 両方がこれを参照）。
  - または Ctrl+C。

2) ExecutionEngine の起動
- paper_trading モード:
  - KABUSYS_ENV=paper_trading に設定すると、MockBrokerClient（BrokerClientFactory 経由）と paper_trading.db を使用し本番 DB と分離されます。
- 起動:
  - python -m kabusys.run_execution
- 停止:
  - data/stop_requested.flag を作成するか、kill.flag（KabuSys の KillSwitch が書き込む）により停止されます。
- PID ファイル:
  - 実行時、PID ファイル（デフォルト data/execution.pid）を使用します。

3) Paper Trading 検証レポート生成
- 期間を指定してペーパートレード DB を解析・レポートを出力:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定: --db /path/to/paper_trading.db
- 確認する指標: 稼働率、注文成功率（fill rate）、送信率、P95 レイテンシ 等

4) AI 機能（ニューススコア・レジーム判定）
- OPENAI_API_KEY を設定して使用します（env または引数で渡せる関数もあります）。
- news_nlp.score_news / regime_detector.score_regime といった関数を呼び出して DuckDB 上の raw_news などを処理します。

重要挙動メモ
- run_monitoring は KABUSYS_ENV にかかわらず常に Settings.sqlite_path（本番 monitoring DB）を使用します（監視は本番 DB を観測するため）。
- run_execution は KABUSYS_ENV=paper_trading の場合、Paper Trading 用の専用 SQLite DB を使用して本番 DB と完全分離します。
- run_* スクリプトは起動時に set_process_priority("high") を呼び出してプロセス優先度を上げようとします（権限がない場合は警告）。
- kill_switch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側で検出して停止します。kill.flag の自動クリア設定は KILL_FLAG_CLEAR_ON_START で制御しますが、本番では無効(0)推奨です。
- run_monitoring の MONITOR_POLL_INTERVAL は環境変数で上書き可能。整数かつ 1 以上である必要があります。不正な値はデフォルト 60 秒にフォールバックします。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                 — 環境変数 / Settings ラッパー（自動 .env ロード機能含む）
  - config_setup.py           — .env 作成ウィザード（CLI）
  - validate_config.py        — 簡易設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py        — ログ初期化（Stream + TimedRotatingFileHandler）
    - process_priority.py     — プロセス優先度・CPU affinity 設定ヘルパ
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ初期化 / DB 操作ラッパ
    - system_monitor.py       — CPU/メモリ/ディスク・プロセス・データ鮮度チェック
    - trade_monitor.py        — 発注ログ監視（滞留・価格異常検出）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — 条件により kill.flag を書き込み ExecutionEngine 停止
    - alert_manager.py        — （アラート送信の抽象。LINE 送信等を想定）
    - monitoring_engine.py    — 各 Monitor を束ねるポーリングエンジン
  - execution/
    - execution_engine.py     — 実行エンジン（EngineConfig など）
    - broker_factory.py       — BrokerClient の生成（実口座 or Mock）
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
    - news_nlp.py             — OpenAI を用いたニュースセンチメント評価
    - regime_detector.py      — マーケットレジーム判定
  - data/                     — runtime に作成される想定フォルダ
    - monitoring.db (デフォルト SQLITE_PATH)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - paper_trading.db (ペーパートレード用)
    - execution.pid
    - kill.flag / stop_requested.flag

ログ
----
- デフォルトログディレクトリ: logs/
- ログファイル:
  - logs/execution.log
  - logs/monitoring.log
  - など（アプリ名を prefix として日次ローテート、30日保持）
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行います。

トラブルシューティングのヒント
------------------------------
- .env を作成後は validate_config で簡易チェックを実行してください。
- AI 機能を使うときは OPENAI_API_KEY を設定してください。API エラー時はフォールバック処理が入りますが、期待する結果は得られません。
- DB パスやログディレクトリの親ディレクトリが存在しない場合、validate_config は警告を出します（起動時に自動作成される場合があります）。
- run_monitoring は監視ログ用 SQLite を初期化（テーブル作成 / マイグレーション）します。既存 DB がある場合でも冪等に動作します。

ライセンス / バージョン
---------------------
- パッケージ内 __version__ は src/kabusys/__init__.py に定義されています（現状: 0.1.0）。

最後に
-----
この README はコードベースの主要機能と運用に必要な情報を要約したものです。各モジュールに詳細な docstring（日本語コメント）が含まれているため、実装を確認することでより細かい挙動・設定項目を把握できます。必要であれば、起動手順や config のサンプル .env を追加で生成します。