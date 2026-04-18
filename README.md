README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ用ライブラリ兼起動スクリプト群です。本リポジトリには以下の主要機能を持つコンポーネントが含まれます。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を行う起動スクリプト run_execution.py
- 監視（Monitoring）: システム状態・注文・リスクを定期監視する run_monitoring.py とモニタ群
- ポートフォリオ構築ロジック: 候補選定・重み付け・ポジションサイズ計算・セクター上限などの純関数群
- リサーチ / ファクター計算: momentum / volatility / value などのファクター計算と IC 計算
- AI ユーティリティ: ニュース NLP（OpenAI）を用いたニュースセンチメント評価、市場レジーム判定
- ツール: Paper Trading の検証レポート生成スクリプト等
- 環境管理: .env ウィザード（config_setup.py）と設定検証ツール（validate_config.py）
- ユーティリティ群: logging 設定、プロセス優先度設定、DB 初期化など

主な特徴
--------
- 環境ごとに挙動を切り替え（development / paper_trading / live）
- Paper Trading 時は本番 DB と分離して data/paper_trading.db に記録可能
- DuckDB を使った分析用データ参照（prices_daily / raw_financials など）
- OpenAI を用いたニュースセンチメント & レジーム判定（API キー必須）
- 監視結果を SQLite に永続化しアラート・Kill Switch を提供
- ログはコンソールと日次ローテートされたファイル（logs/<app>.log）に保存

セットアップ
------------

前提
- Python 3.10 以上を推奨
- OS によっては psutil のインストールにビルドツール等が必要になる場合があります

推奨パッケージ（examples）
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の検証に使用）
- その他: 任意でテストフレームワーク等

例: 仮想環境作成、必要パッケージのインストール
- venv 作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- インストール（requirements.txt がある場合はそれを使用）
  - pip install duckdb psutil openai PyYAML

環境変数 / .env
- プロジェクトルートに .env を置くことで設定を読み込みます（.env.local は .env を上書き可）。
- 自動ロードはデフォルトで有効。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 重要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY（AI 機能を使う場合に必須）
  - LOG_LEVEL（DEBUG/INFO/...）

.env の初期作成（ウィザード）
- 対話形式で .env を生成/更新する:
  - python -m kabusys.config_setup

設定検証
- .env と config/*.yaml の簡易検証を行う:
  - python -m kabusys.validate_config
  - strict モード（警告も FAIL として扱う）:
    - python -m kabusys.validate_config --strict

使い方
------

起動スクリプト（CLI モジュールとして実行）
- 監視ループを起動（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で設定可能、デフォルト 60）:
  - python -m kabusys.run_monitoring
  - 停止: data/stop_requested.flag を作成するとループは終了します
- 実行エンジンを起動:
  - KABUSYS_ENV=paper_trading を使うと MockBroker を使い paper DB に記録され、本番 DB と分離されます
  - 例: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在する場合は起動を中止します
  - エンジンは data/execution.pid ファイルを PID 管理に使用します

モニタ / エンジンの挙動（要点）
- run_monitoring.py
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用（環境にかかわらず）
  - process 優先度を "high" にセット（可能な場合）
- run_execution.py
  - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用（paper_trading 用 DB）
  - Broker の選択は BrokerClientFactory が Settings を見て行います
  - エンジンは別スレッドで実行し stop_requested.flag に応じて停止します

AI 機能
- OpenAI を使う機能（ニュース NLP / レジーム判定）は OPENAI_API_KEY 必須
- ニュース NLP: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - バッチで複数銘柄のニュースを送信、レスポンスを ai_scores テーブルに書き込み
- レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 とマクロニュースセンチメントを合成して regime を算出

ツール
- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定

ファイル / フラグの挙動
- data/kill.flag: Kill Switch（監視側が検知すると ExecutionEngine を停止させるために作成）
  - KillSwitch は設定に応じて書き込み、既に存在する場合は上書きしない（冪等）
- data/stop_requested.flag: 外部から監視ループ / 実行ループを停止させるためのフラグ
- data/execution.pid: 実行エンジンの PID を記録（run_execution.py が使用）

ディレクトリ構成
----------------
（src 以下をパッケージとして想定）

- src/kabusys/
  - __init__.py                — パッケージ情報（バージョン等）
  - config.py                  — Settings クラス（.env 読み込み・解決）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前チェック CLI
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 発注株数決定（Lot 単位・リスク制限）
    - risk_adjustment.py        — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py        — momentum / volatility / value ファクター計算
    - feature_exploration.py    — 将来リターン / IC / 統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py               — ニュース NLP（OpenAI）で ai_scores を作成
    - regime_detector.py        — マクロ + MA200 で市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py          — SQLite スキーマ初期化・永続化層（MonitoringDB）
    - system_monitor.py         — システム/データ鮮度チェック
    - trade_monitor.py          — （注文監視ロジック: repo に含まれる）
    - risk_monitor.py           — ドローダウン・ポジション上限チェック
    - kill_switch.py            — Kill Switch（flag 書き込み）
    - monitoring_engine.py      — 複数モニタを束ねるエンジン
  - execution/                  — ExecutionEngine / OrderManager など（発注処理群）
  - data/                       — デフォルトの DB・フラグ・PID 保存場所（リポジトリルート直下の data/）
  - utils/
    - logging_setup.py          — ログ設定ユーティリティ（コンソール + 日次ファイル）
    - process_priority.py       — プロセス優先度 / CPU affinity 設定
    - __init__.py

注意点 / 運用上のヒント
-----------------------
- 本番環境（KABUSYS_ENV=live）では kill_flag_clear_on_start=1 を設定しないでください（安全上の理由）。
- .env は機密情報（API トークン等）を含むため、絶対に Git 等へコミットしないでください。
- OpenAI の呼び出しはレート制限やネットワーク障害に対しリトライとフォールバックを備えていますが、API キー使用量・コストに注意してください。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効になりコンソール出力のみになります（warnings が出ます）。
- psutil による優先度設定や CPU affinity の適用は OS 権限に依存します。AccessDenied が発生する場合は警告を出してスキップします。

開発者向け
------------
- パッケージをモジュールとして実行する (例):
  - python -m kabusys.run_monitoring
  - python -m kabusys.run_execution
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にすると自動 .env ロードを無効化できます。
- DuckDB / SQLite のスキーマ変更は monitoring_db.init_monitoring_db で簡単なマイグレーション処理（カラム追加）を行っています。スキーマ互換性に注意してください。

ライセンス / 貢献
-----------------
（ここにライセンス情報や貢献方法を追記してください）

お問い合わせ
------------
- 実装に関する質問やバグ報告はリポジトリの Issue にてお願いします。

以上。必要であれば README に含める実行例や systemd / supervisor 用のユニットファイルテンプレート、requirements.txt のサンプルなども追記できます。どの情報を追加しますか？