KabuSys — 日本株自動売買システム (README)
========================================

概要
----
KabuSys は日本株向けの自動売買システムライブラリです。価格データの集計・ファクター計算、ポートフォリオ構築、ポジションサイズ計算、ExecutionEngine（発注ロジック）の起動、監視（Monitoring）・Kill Switch、さらに AI を使ったニュースセン評点付け・市場レジーム判定などを含むフルスタックな実装を目的としています。

主要な設計方針
- DuckDB を解析用 DB、SQLite を監視・トレードログ用 DB として利用
- 設定は .env ファイル（または環境変数）で管理。config_setup による対話式ウィザードあり
- Paper Trading（仮想発注）と Live（実発注）を切り替え可能。paper_trading は本番 DB と分離
- OpenAI を使ったニュース NLP / レジーム判定を組み込み可能（API キー必須）
- 監視は独立したプロセスで定期ポーリングし、条件達成時に kill.flag を書込んで ExecutionEngine を停止可能

機能一覧
--------
- 環境設定ウィザード（config_setup）による .env 生成／更新
- 設定検証ツール（validate_config）で起動前チェック（--strict あり）
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を利用し、paper_trading 用 SQLite に記録
  - 停止フラグ（data/stop_requested.flag / data/kill.flag / data/execution.pid）で制御
- Monitoring 起動スクリプト（run_monitoring.py）
  - SYSTEM / TRADE / RISK の監視をポーリングで実行
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存しない）
- 監視用 DB 層（monitoring_db）: system_status、trade_logs、positions、risk_logs、dashboard
- RiskMonitor（ドローダウン・ポジション上限のモニタリング）
- KillSwitch（kill.flag の作成・クリア）
- MonitoringEngine（各モニタの束ね・アラート発行）
- Portfolio モジュール（候補選定・重み計算・ポジションサイズ決定・セクター制約・レジーム乗数）
- Research モジュール（ファクター計算 / forward return / IC / 統計サマリ）
- AI モジュール
  - news_nlp: raw_news を OpenAI で解析し ai_scores を作成
  - regime_detector: ETF MA 等とマクロニュースを用いた市場レジーム判定
- ユーティリティ：ログ設定（logging_setup）、プロセス優先度／CPU affinity（process_priority）
- ツール: paper_verification_report（Paper Trading の検証レポート生成）

セットアップ手順
----------------
前提
- Python 3.9+（プロジェクトで想定されているバージョンを使用してください）
- 必要な外部ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config/*.yaml のパース検証で使用）
- システムでのファイル作成権限（data/ や logs/ ディレクトリ作成のため）

推奨手順（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - 必要に応じて PyYAML を追加: pip install pyyaml

   ※ requirements.txt があれば pip install -r requirements.txt を使用してください。

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に .env を編集してください。

4. 設定を検証
   - python -m kabusys.validate_config
   - 厳密モード（警告を失敗にしたい場合）:
     - python -m kabusys.validate_config --strict

5. 必要ディレクトリの確認（初回起動時に自動作成されることが多い）
   - data/
   - logs/

使い方
------
主な実行コマンド

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
  - 挙動:
    - Settings に基づき SQLite / DuckDB に接続
    - paper_trading の場合は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止
    - 実行中は data/execution.pid に PID を書く（設定に依存）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（例: export MONITOR_POLL_INTERVAL=30）
  - Monitoring は常に本番 sqlite_path（デフォルト data/monitoring.db）を使用して監視情報を記録

- .env の対話式設定ウィザード
  - python -m kabusys.config_setup

- 起動前設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

AI 関連（news_nlp / regime_detector）
- OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数）
- news_nlp.score_news / regime_detector.score_regime は DuckDB 接続を受け取り、ai_scores / market_regime テーブルへ書き込みます
- 実行はスクリプト化されていないため、必要に応じてスクリプトや定期ジョブから関数を呼び出します

停止・Kill Switch
- Monitoring 側の KillSwitch が条件を満たすと data/kill.flag を書き込み、ExecutionEngine 起動中にこれを検出して停止します
- 手動で停止したい場合は data/stop_requested.flag を作成すると各 run_* スクリプトはループを止めます
- kill.flag は Settings.kill_flag_clear_on_start が 1 の場合、起動時に自動でクリアされる可能性があるため本番では 0 にすることを推奨

ログ
- logging_setup.setup_logging がルートロガーを設定
- デフォルトで logs/<app_name>.log に日次ローテートで出力（30日保持）
- 環境変数 LOG_DIR / LOG_LEVEL で変更可能

環境変数の主要項目（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- LOG_LEVEL（デフォルト INFO）
- OPENAI_API_KEY（AI 機能を使う場合必須）
- MONITOR_POLL_INTERVAL（Monitoring のポーリング間隔秒。デフォルト 60）
- PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject）

ディレクトリ構成
----------------
以下は主要なソースツリー（src/kabusys 以下）の概要です。実際のファイルはこの README 作成時点のものです。

- src/kabusys/
  - __init__.py  — パッケージ定義（__version__ など）
  - config.py  — 環境変数の読み込み・Settings 定義（.env の自動読み込み機能含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（PID / stop flag 管理、paper_trading 対応）
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - ai/
    - news_nlp.py — ニュースを OpenAI で評価して ai_scores を書き込むモジュール
    - regime_detector.py — MA とマクロニュースを使ったレジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視 DB 層（テーブル作成 / CRUD）
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 発注・約定ログの監視（滞留注文・約定異常等）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - kill_switch.py — kill.flag の作成・管理
    - alert_manager.py — （アラート送信の管理。LINE 等）
  - execution/
    - execution_engine.py — 実際の ExecutionEngine（セッション管理）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注関連コンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・集約キャップ処理
    - risk_adjustment.py — セクター上限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — モメンタム・ボラティリティ・バリュー等の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
    - __init__.py
  - utils/
    - logging_setup.py — ロギング初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
    - __init__.py
  - data/ (runtime)
    - monitoring.db / paper_trading.db / kill.flag / stop_requested.flag / execution.pid などが置かれる（デフォルトパス）

開発・運用上の注意
------------------
- .env は機密情報を含むため決してリポジトリにコミットしないでください
- KABUSYS_ENV=live 時は特に設定を慎重に確認してください（validate_config で警告が出ます）
- Paper Trading は実口座と分離するよう実装されていますが、設定ミスに注意してください（PAPER_TRADING_SQLITE_PATH の確認等）
- OpenAI 呼出しにはレート制限やネットワークエラーへのリトライロジックを実装していますが、API キー漏洩や誤課金に注意してください
- psutil の一部機能はプラットフォーム依存（特に優先度設定・cpu_affinity）。権限不足で警告になる可能性があります

貢献
----
バグ報告・改善提案は Issues を通じてお願いします。コード変更はプルリクエストで送ってください。主要なモジュールは純粋関数で分離されているため、単体テストを追加しやすい設計になっています。

ライセンス
---------
（プロジェクト固有のライセンスをここに記載してください）

以上。README に追加して欲しい具体的な項目（例: サンプル .env テンプレート、実行時ログ例、API の詳細仕様等）があれば教えてください。