README
======

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。本リポジトリには、以下の主要サブ機能が含まれます。

- 発注実行エンジン（ExecutionEngine）
- 監視（Monitoring）コンポーネント（システム状態・約定・リスク監視・Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・株数計算）
- リサーチ（ファクター計算・特徴量解析）
- AI 補助（ニュースのセンチメント評価、レジーム判定）
- ユーティリティ（設定ウィザード・設定検証・ログ設定 等）
- 運用用スクリプト（起動スクリプト・検証レポート生成ツール）

設計方針の要点
- 本番/ペーパートレードを分離（PAPER_TRADING は専用 SQLite を使用）
- ルックアヘッドバイアス防止（日付・時間の扱いに注意）
- フェイルセーフ：API 失敗時はスキップ / フォールバックして継続
- ロギングは統一的に設定（logs/<app>.log、日次ローテーション）

機能一覧
--------
主な機能（抜粋）:

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db を使用。
  - 停止フラグ（data/stop_requested.flag）検出で安全に停止。
  - PID ファイル（data/execution.pid）を管理。

- run_monitoring.py
  - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL で間隔を変更可能（デフォルト 60 秒）。
  - 監視ログは monitoring.db（Settings.sqlite_path）に書き込み。

- monitoring/*
  - SystemMonitor: CPU/メモリ/Disk/データ鮮度/プロセス存在を監視。
  - TradeMonitor: 約定・滞留注文・レイテンシなどを検査（trade_logs を参照）。
  - RiskMonitor: ドローダウンやポジション上限の監視、リスクイベント記録。
  - KillSwitch: リスク閾値超過時に data/kill.flag を作成して ExecutionEngine に停止シグナルを送出。
  - MonitoringDB: SQLite による永続化層（テーブル作成・マイグレーション含む）。

- portfolio/*
  - 銘柄選定（スコア順、上位 N）、重み付け（等分・スコア比率）、ポジションサイズ計算、セクター上限、レジーム乗数。

- research/*
  - ファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン、IC 計算、統計サマリ。

- ai/*
  - news_nlp: OpenAI を用いたニュースセンチメント分析（ai_scores への書込み）
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM スコアを合成して市場レジームを判定

- utils/*
  - logging_setup: ログ設定ユーティリティ（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
  - config / config_setup / validate_config: 環境設定の自動読み込み、対話式 .env 生成、検証 CLI

セットアップ手順
----------------

前提
- Python 3.10 以上（型ヒントで | を用いているため）
- SQLite は標準ライブラリで利用可能
- 主要外部依存パッケージ（最低限）:
  - duckdb
  - psutil
  - openai（AI 機能利用時）
  - PyYAML（config/*.yaml の検証を行いたい場合）

インストール例
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

   （リポジトリに requirements.txt があれば: pip install -r requirements.txt）

環境変数設定
1. 対話式ウィザードで .env を作成:
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークン、kabuAPI パスワード、KABUSYS_ENV などを入力します。

2. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告を FAIL 扱いにできます（exit code 1）。

主要環境変数（代表）
- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合必須）
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、default: data/paper_trading.db）
- LOG_LEVEL（default: INFO）
- LOG_DIR（default: logs/）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒、default: 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか。production では 0 推奨）

使い方
------

起動スクリプト（運用）
- ExecutionEngine を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading 用 DB に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動をせず終了します。
  - 実行中は data/execution.pid が使われます。

- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path（通常 data/monitoring.db）にログを書き込みます。
  - stop_requested.flag を検知するとループを抜けてクリーン終了します。

設定関連
- .env を対話式で作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

ツール
- Paper Trading 検証レポートを生成:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）

AI 機能
- OpenAI を使う機能（ニューススコアリング、レジーム判定）は OPENAI_API_KEY を環境変数または各関数の引数で渡す必要があります。
- AI 呼び出しはリトライやフォールバック（失敗時は 0 等）を備えていますが、API キーと課金設定を確認してください。

停止・Kill Switch
- 管理用フラグ:
  - data/stop_requested.flag: 起動中のスクリプト（run_execution/run_monitoring）はこのファイルの存在を検出して終了します。
  - data/kill.flag: KillSwitch が作成するフラグ。ExecutionEngine は起動時にこれを検出すると起動を中止します。
- Kill Switch は RiskMonitor の判定（ドローダウン閾値超過、ポジション上限等）により自動的に書き込まれます。

ロギング
- setup_logging により stdout と logs/<app_name>.log に出力されます（TimedRotatingFileHandler、日次ローテーション、30 日保持）。
- デフォルトログディレクトリ: logs/

ディレクトリ構成（主要ファイル）
--------------------------------
以下はソースツリー（src/kabusys 以下）の要約です。実際のファイル数は増える可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・Settings 定義（自動 .env ロード含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — 優先度 / CPU affinity 設定
    - __init__.py

  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル作成・API）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 約定 / 滞留注文監視（ファイル一覧に実装あり）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — Kill Switch 実装
    - monitoring_engine.py    — 各モニタを束ねる

  - execution/                — Execution 関連（broker, engine, order_manager 等）
    - (broker_factory.py, execution_engine.py, order_manager.py, ...)

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
    - news_nlp.py             — ニュースセンチメント評価（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA200 + LLM）
    - __init__.py

  - tools/
    - paper_verification_report.py

設計上の注意点・運用メモ
-----------------------
- 本番運用時は KABUSYS_ENV=live を設定し、LINE 通知等の設定を確実に行ってください（validate_config によるガードあり）。
- KILL_FLAG_CLEAR_ON_START は production では 0 を推奨。1 にすると起動時に既存の kill.flag を消去してしまいます。
- PAPER_TRADING は実口座と完全に分離するよう設計されています（別 SQLite）。
- OpenAI API を利用する処理は外部 API 呼び出しで費用が発生します。rate limit / エラー処理は実装されていますが注意してください。
- ログディレクトリが作れない場合はファイルログが無効化され、標準出力のみになります。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス表記はリポジトリの LICENSE を参照してください（存在する場合）。

問い合わせ・開発
----------------
- 開発時は Python の型チェック、ユニットテスト、静的解析を併用してください。
- 設定変更やテーブルスキーマ変更はマイグレーションの影響を確認のこと（monitoring_db.py は簡易マイグレーションロジックあり）。

以上。README に記載のない具体的な運用フローや追加のユーティリティが必要であれば、目的に応じて追補します。