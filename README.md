README — KabuSys（日本株自動売買システム）
=====================================

概要
----
KabuSys は日本株の自動売買フレームワークのコードベースです。  
トレード実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）や AI ベースのニュース解析など、取引と運用に必要な主要コンポーネントを備えています。

主な特徴
--------
- 実行エンジン（ExecutionEngine）
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - ブローカークライアントは環境に応じて実装を切替（MockBroker 用意）
  - リスク管理（RiskManager）、注文管理（OrderManager）、整合性処理（Reconciler）を搭載
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による外部からの強制停止（KillSwitch）
  - SQLite ベースの監視ログ保持（monitoring.db）
- ポートフォリオ構築
  - 候補選定、重み計算（等金額・スコア重み）
  - セクター上限適用、レジームベースの資金乗数
  - 発注株数決定（単元丸め、リスクベース配分、aggregate cap）
- リサーチ（Research）
  - DuckDB を利用したファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）などの分析ユーティリティ
- AI モジュール
  - ニュースのセンチメント解析（OpenAI を使用）
  - 市場レジーム判定（ETF MA とマクロニュースの LLM 評価を組合せ）
- 運用ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

前提条件
--------
- Python 3.10+
- DB:
  - SQLite: 標準ライブラリ
  - DuckDB: duckdb Python パッケージ
- 推奨パッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合）
- 環境変数（最低限必須）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - （その他は .env を参照／設定）

インストール
------------
1. 仮想環境を作成・アクティベート（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt があればそれを利用してください）

環境設定 (.env)
---------------
プロジェクトルート（pyproject.toml または .git がある場所）に .env を配置します。対話式ウィザードで作成できます。

- 対話式ウィザード実行:
  - python -m kabusys.config_setup
- 生成される主な環境変数（例）
  - KABUSYS_ENV: development | paper_trading | live
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - DUCKDB_PATH, SQLITE_PATH
  - LOG_LEVEL
  - KILL_FLAG_CLEAR_ON_START

設定検証
--------
- 設定の事前検証:
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

使い方（主要 CLI / スクリプト）
------------------------------
- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に結果を記録（本番 DB と分離）
    - 実行は別スレッドで行われ、data/stop_requested.flag を検知すると安全終了
    - 実行中は data/execution.pid に PID を書き込む

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト: 60）
  - 監視は常に本番 sqlite_path（設定に依らず）を使用して監視ログを記録
  - 停止フラグ file: data/stop_requested.flag を検知するとループを終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプションで期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定できる（デフォルト: data/paper_trading.db）

補助スクリプト / 機能
- .env の自動読み込み:
  - kabusys.config モジュールはプロジェクトルートの .env/.env.local を自動でロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
- ロギング:
  - kabusys.utils.logging_setup.setup_logging() を通じて stdout と日次ローテートファイル（logs/<app_name>.log）へ出力
- プロセス優先度設定:
  - kabusys.utils.process_priority.set_process_priority("high"|"normal"|"low")
- AI 機能:
  - OpenAI API キーは OPENAI_API_KEY 環境変数または関数引数で指定

運用上の注意
------------
- 本番運用時は KABUSYS_ENV=live を設定し、LINE 通知や kill flag の設定を十分確認してください（validate_config で警告あり）。
- kill.flag（Settings.kill_flag_path）により ExecutionEngine を停止できます。KillSwitch はリスクイベント（ドローダウン・ポジション上限等）で書き込まれます。
- logs/ ディレクトリの作成権限がない場合はファイル出力が無効化され stdout のみになります。
- Paper Trading 時は必ず PAPER_TRADING_SQLITE_PATH を確認して、本番 DB と分離されていることを確認してください。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数管理（.env 読み込み、Settings）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py  — Paper Trading 検証レポート生成
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）で ai_scores を生成
  - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py        — SQLite 監視 DB スキーマ + アクセス
  - system_monitor.py       — システム状態・データ鮮度監視
  - risk_monitor.py         — ドローダウン／ポジション上限監視
  - trade_monitor.py        — （※トレード監視ロジック）
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - kill_switch.py          — kill.flag 管理
  - alert_manager.py        — （※通知管理）
- execution/
  - execution_engine.py     — 実行エンジン本体
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
- utils/
  - logging_setup.py
  - process_priority.py

（注）一部ファイルは上の抜粋に含まれていない場合があります。実際のリポジトリを参照してください。

開発者向けメモ
----------------
- DuckDB を利用したリサーチ系は prices_daily / raw_financials / raw_news 等のテーブル構造に依存します。テーブル準備やデータロードは別スクリプトで行ってください。
- OpenAI 呼び出しはレート制限や一時エラーに対してリトライ実装が入っています。テスト時は外部呼び出しをモックしてください（関数単体を patch する設計）。
- config モジュールは .env の自動ロードを行います。ユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化してください。

よくある操作例
---------------
- .env を初期作成:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- ローカルでペーパートレードを実行:
  - (.env で KABUSYS_ENV=paper_trading を設定)
  - python -m kabusys.run_execution
- 監視プロセスを起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ で確認できます（デフォルト "0.1.0"）。

問い合わせ
--------
コードの理解や導入に関する質問は README を更新するか、リポジトリの issue に記載してください。

---  
上記はコードベースの主要部分からまとめた README です。実運用前に各環境変数や DB パス、OpenAI API キーの取り扱い等を必ず確認してください。