# KabuSys

日本株自動売買システム（ライブラリ / 起動スクリプト群）

このリポジトリは、取引エンジン、監視、ポートフォリオ構築、リサーチ（DuckDB ベース）、および LLM を用いたニュース解析／レジーム判定などを含む自動売買プラットフォームの主要コンポーネント群を提供します。

---

## プロジェクト概要

- 目的：日本株の自動売買パイプラインを構築するためのコアロジック（発注管理・リスク管理・監視・ポートフォリオ構築・ファクター計算・AI ニュース解析など）をまとめたモジュール群。
- 設計方針：
  - DuckDB を分析向け DB、SQLite を監視・注文履歴用に使用。
  - 環境変数（.env）で設定管理。対話式ウィザードと検証 CLI を提供。
  - Paper Trading（ペーパートレード）と Live（本番）を明確に分離。
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント / マクロ判定をサポート（API キー必須）。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（Paper Trading 時は MockBroker 使用、paper_trading DB に記録）
  - run_monitoring.py: SystemMonitor のポーリングループを実行（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理
  - config_setup.py: .env の対話式ウィザード生成
  - validate_config.py: 環境設定・config/*.yaml の事前検証
  - config.py: Settings クラス（環境変数ラッパ）
- 監視（Monitoring）
  - monitoring_db.py: 監視用 SQLite スキーマと永続化 API
  - system_monitor.py / trade_monitor.py / risk_monitor.py: 各種監視ロジック
  - monitoring_engine.py: 各 Monitor をまとめて定期実行、KillSwitch と Alert 管理
  - kill_switch.py: フラグファイルによる Execution 停止機構
- ポートフォリオ構築（Portfolio）
  - portfolio_builder.py: 候補選定・重み算出（等金額／スコア加重）
  - position_sizing.py: 株数決定、リスク制約、単元丸め、スケーリング
  - risk_adjustment.py: セクター上限・レジーム乗数
- リサーチ（Research）
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン計算、IC（Spearman）等
- AI（LLM）
  - ai/news_nlp.py: raw_news を LLM に送って銘柄別センチメントを ai_scores に書き込み
  - ai/regime_detector.py: ETF MA とマクロニュースを組み合わせて日次レジーム判定を実行
- ユーティリティ
  - utils/logging_setup.py: 共通ログ設定（コンソール + 日次ファイルローテート）
  - utils/process_priority.py: プロセス優先度 / CPU affinity の簡易設定
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート（期間指定可）

---

## 必要条件（概略）

- Python 3.10+
- pip パッケージ（例）
  - duckdb
  - openai
  - psutil
  - PyYAML（任意、config 検証で使用）
- システムに sqlite3 は標準で付属（Python 標準ライブラリ）

インストール例:
  pip install duckdb openai psutil PyYAML

（プロジェクトで requirements.txt があればそちらを使ってください）

---

## セットアップ手順

1. リポジトリをクローン / 配置
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .\.venv\Scripts\activate）
3. 依存パッケージのインストール
   - pip install duckdb openai psutil PyYAML
4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで必要な値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など）を入力
5. 設定検証
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けて警告も FAIL 扱いにできます
6. データディレクトリの確認
   - デフォルト DB / ファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite（監視）: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログ: logs/
     - Kill flag / stop flag / pid: data/kill.flag, data/stop_requested.flag, data/execution.pid
   - これらの親ディレクトリは必要に応じて作成されますが、権限やパスを確認してください。

---

## 使い方（起動と主なコマンド）

- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ExecutionEngine（発注エンジン）起動
  - 本番（KABUSYS_ENV=live）:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード（MockBroker を使用、paper_trading DB に記録）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 注意点:
    - 起動時に data/stop_requested.flag が既に存在すると起動をスキップします。
    - PID 管理: data/execution.pid にプロセス ID を書きます。
- Monitoring（監視）起動
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定可能（デフォルト 60 秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に Settings.sqlite_path（本番 sqlite_path）を使用して監視 DB に書き込みます（KABUSYS_ENV に依存しない）
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH で SQLite DB を指定（PAPER_TRADING_SQLITE_PATH 環境変数で代替可）
- AI モジュールの利用（プログラム的に）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - conn: duckdb connection（duckdb.connect(...)）
    - target_date: datetime.date（スコアを生成する日付）
    - api_key: OpenAI API キー（None の場合は環境変数 OPENAI_API_KEY を参照）
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に DuckDB 接続と日付、API キーを渡して実行

---

## 環境変数（主なもの）

- 必須 / 重要
  - JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- 環境選択
  - KABUSYS_ENV: execution モード（development / paper_trading / live）
    - paper_trading: 発注は MockBroker、paper DB を使用
    - live: 実際に発注
- DB / ファイルパス
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
- ログ
  - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
  - LOG_DIR: ログディレクトリ（デフォルト logs/）
- AI
  - OPENAI_API_KEY: OpenAI API キー（ai モジュールで参照）
- モニタリング
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（任意、整数）
- その他
  - PAPER_FILL_MODE: paper_trading 時の約定モデル（instant/partial/never/reject）

（詳細は config_setup.py の UI と config.py の Settings を参照してください）

---

## 重要な挙動メモ

- run_monitoring.py は KABUSYS_ENV にかかわらず「監視用 DB（Settings.sqlite_path）」を使用します。監視は本番の監視テーブルに書き込みます。
- run_execution.py は KABUSYS_ENV=paper_trading の場合に paper_trading_db を使用して本番 DB と分離します。
- Kill Switch（data/kill.flag）は KillSwitch クラスで作成され、ExecutionEngine 停止判定に使われます。kill.flag があるとエンジンは停止します。
- stop_requested.flag（data/stop_requested.flag）はプロセス間の停止制御で使用されます。監視ループや実行エンジンはこのファイルを検出して終了します。
- ロギングは logs/<app_name>.log に日次ローテートで保存され、コンソール出力は stdout に出ます。

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定ラッパ
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (存在: 監視のためのモジュール)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (通知管理 ※実装参照)
  - execution/                 — ExecutionEngine / BrokerFactory / OrderManager 等（発注ロジック）
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
  - data/ （実行時に生成する想定）
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (デフォルト)
    - kill.flag, stop_requested.flag, execution.pid
  - logs/ （デフォルトログ出力先）
    - execution.log
    - monitoring.log
    - …（日次ローテート）

（上記は主なファイルの概要です。実際の配布では execution や monitoring 以下にさらに実装ファイルがあります。）

---

## 参考：よく使うコマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動（ペーパー）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動（ポーリング間隔 30 秒）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に書かれている基本的な手順で起動できるはずです。追加で CLI / デプロイ手順や systemd/cron の unit 例、Dockerfile 等が必要であれば、その環境・要件に合わせたドキュメントを作成します。必要があれば教えてください。