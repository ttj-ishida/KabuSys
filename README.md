# KabuSys

日本株向けの自動売買システム用ライブラリ／ツール群です。戦略の研究・ポートフォリオ構築・発注エンジン・監視・AI を使ったニュース評価などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は次を目的としたモジュール群です。

- 戦略の研究・ファクター計算（duckdb を使った時系列計算）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定）
- ExecutionEngine（発注エンジン）と Broker 抽象化（paper_trading モードあり）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）、Kill Switch による自動停止
- ニュースの NLP による銘柄センチメント評価（OpenAI API を使用）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証、レポート生成）

設計方針として、DuckDB/SQLite をデータ層に使い、外部の実口座 API への影響を限定しつつ、paper_trading モードで発注の切り離しが可能です。

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local）
  - 対話式 .env ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 発注・実行
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - paper_trading モード（MockBroker を使用、DB を分離）

- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による安全停止（KillSwitch）
  - 監視データ永続化（SQLite、monitoring_db）

- 研究・特徴量
  - モメンタム/ボラティリティ/バリュー等のファクター計算（research パッケージ）
  - 将来リターンやIC計算などの解析ユーティリティ

- ポートフォリオ構築
  - 候補選定、等配分／スコア配分、リスクベースの株数算出
  - セクターキャップ／レジーム乗数の適用

- AI（OpenAI）
  - ニュース記事のセンチメント評価（gpt-4o-mini 想定）
  - 市場レジーム判定（ETF MA とマクロニュースの組合せ）

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 必要環境 / 依存ライブラリ

- Python 3.10+
  - （コード内での型記法や union 型を利用しているため）
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML を検証する場合）
- 実行例:
  - pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを設置

2. Python 環境を準備
   - Python 3.10+ を用意
   - 仮想環境を作ることを推奨（venv / conda 等）

3. 依存ライブラリをインストール
   - 例: pip install -r requirements.txt
   - requirements.txt が無い場合:
     - pip install duckdb psutil openai pyyaml

4. 初期設定（.env）を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに .env を作成して必要な環境変数を設定する
   - 自動ロードを無効にするには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定の検証
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - デフォルトでは `data/` と `logs/` を使用します。起動時に自動作成されますが、必要に応じて手動で作成してください。

---

## 主な環境変数（抜粋）とデフォルト値

（詳細は kabusys.config.Settings を参照してください）

- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- KABUSYS_ENV — デフォルト: development（有効値: development, paper_trading, live）
- LOG_LEVEL — デフォルト: INFO
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 任意（アラート送信に使用）
- OPENAI_API_KEY — OpenAI を使う機能に必須
- PAPER_FILL_MODE — paper_trading の約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — 監視ループ間隔（秒、run_monitoring で使用、デフォルト 60）

注意: .env は絶対にリポジトリにコミットしないでください（機密情報を含むため）。

---

## 使い方（実行例）

- .env の作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - 本番/通常:
    - python -m kabusys.run_execution
  - paper_trading モードにするには .env で KABUSYS_ENV=paper_trading を設定
    - paper_trading 時は専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され本番 DB と分離されます
  - 停止制御:
    - data/stop_requested.flag があると起動スクリプトは停止します
    - KillSwitch は data/kill.flag を書き込んで ExecutionEngine 停止を指示します

- Monitoring を起動（ループで定期実行）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db 、--db で上書き可能

- AI 関連（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは OPENAI_API_KEY 環境変数か関数引数で与えてください

- ログ
  - ログは stdout に出力され、さらに logs/<app_name>.log に日次ローテーションで保存されます
  - ログの出力先は LOG_DIR 環境変数または setup_logging の引数で変更可能

---

## 停止・安全装置

- stop_requested.flag
  - run_execution.py / run_monitoring.py はプロジェクト直下の data/stop_requested.flag を監視しており、存在すると起動ループを終了します（外部からの安全停止用）。

- kill.flag
  - KillSwitch が条件（例: ドローダウン超過等）を満たすと data/kill.flag を書き込み、ExecutionEngine に停止信号を与えます。
  - Settings.kill_flag_clear_on_start=1 を設定すると起動時に自動クリアされますが、本番では 0 を推奨します。

---

## ディレクトリ構成（主要ファイル）

概略（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - monitoring/
    - monitoring_db.py      — SQLite の永続化層（監視ログ）
    - system_monitor.py
    - trade_monitor.py      — （存在：監視用ロジック）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py      — （アラート送信ロジック、存在）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
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
  - monitoring/ (上記)
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

（各サブパッケージにさらに細かい実装ファイルがあります。上は主要ファイルの抜粋です。）

---

## 実運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では設定を慎重に確認してください。validate_config でいくつかのガード（LINE 設定、KILL_FLAG_CLEAR_ON_START 等）があります。
- 機密情報（API トークン／パスワード）は .env に保存しますが、絶対に Git にコミットしないでください。
- OpenAI API を使う機能は API 利用料金が発生します。API キーは安全に管理してください。
- logs/ と data/ はバックアップ方針に応じて管理してください（監視ログや約定ログを保持します）。
- Paper trading を行う場合、PAPER_TRADING_SQLITE_PATH による DB 分離を活用してください。
- プロセス優先度設定（set_process_priority）は実行ユーザーの権限に依存します。失敗時は警告を出して継続します。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README は開発や運用に役立つ要点をまとめています。さらに詳細な API や内部仕様は各モジュールの docstring（ソース内コメント）を参照してください。ご要望があれば各モジュールごとの詳しいドキュメント（関数一覧・引数説明・例）を生成します。