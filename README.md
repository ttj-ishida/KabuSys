KabuSys — 日本株自動売買システム
===========================

このリポジトリは日本株向けの自動売買システム（プロトタイプ）です。  
モジュールは取引実行、監視、ポートフォリオ構築、リサーチ、AI（ニュース解析／レジーム判定）などの機能を分離して実装しています。

主な特徴
--------
- 実行エンジン（ExecutionEngine）: 実際の発注（kabuステーション）またはペーパートレード用の MockBroker に対応
- 監視（Monitoring）: システム状態、注文状況、リスク（ドローダウン・ポジション上限）を定期チェックしてログ化／アラート／Kill Switch を実行
- ポートフォリオ構築: 候補選定、重み付け、単元株丸め、リスク調整（セクターキャップ、レジーム乗数）
- リサーチ: ファクター計算（モメンタム／ボラティリティ／バリュー）、特徴量解析（IC、統計サマリ）
- AI モジュール: OpenAI を用いたニュースセンチメント集約（銘柄別）および市場レジーム判定
- ツール: ペーパー取引の検証レポート生成など

セットアップ
-----------
1. Python 環境（推奨: 3.10+）を用意し、依存パッケージをインストールしてください。
   必須依存（主なもの）:
   - duckdb
   - psutil
   - openai
   - (任意) PyYAML — config/*.yaml の検証に使用

   例:
   pip install -r requirements.txt
   （requirements.txt がない場合は上記パッケージを個別にインストールしてください）

2. プロジェクトルートに移動すると .env 自動読み込み機能が有効になります。
   自動読み込みは Settings モジュールで .env / .env.local をプロジェクトルートから読み込みます。
   自動ロードを無効化するには環境変数を設定します:
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

3. 環境変数（.env）を用意します。対話形式ウィザードで作成できます:
   python -m kabusys.config_setup
   ウィザードで作成後、設定検証を実行:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

必須環境変数（代表）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — AI モジュールを使う場合（news_nlp / regime_detector）
- KABUSYS_ENV — 実行環境: development / paper_trading / live
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH — 各 DB ファイルパス（デフォルトあり）

主要ファイル・実行方法
---------------------

- 実行エンジン（ExecutionEngine）
  - スクリプト: src/kabusys/run_execution.py
  - 実行:
    - 本番／開発（環境変数で制御）:
      KABUSYS_ENV=live python -m kabusys.run_execution
    - ペーパートレード:
      KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 特記事項:
    - paper_trading 環境では MockBrokerClient を使用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト: data/paper_trading.db）に記録します。
    - 起動時に data/stop_requested.flag が既に存在すると起動をスキップします。
    - 実行中の停止は data/stop_requested.flag を作成することで実現（監視側や管理者ツールからの停止シグナル）。

- 監視プロセス（SystemMonitor 単体起動）
  - スクリプト: src/kabusys/run_monitoring.py
  - 実行:
    python -m kabusys.run_monitoring
  - 特記事項:
    - ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で秒数を指定（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用し、監視ログを永続化します。
    - 停止はプロジェクトルート/data/stop_requested.flag を作成すると検知して終了します。

- 設定ウィザード / 検証
  - .env 作成: python -m kabusys.config_setup
  - 検証: python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - スクリプト: src/kabusys/tools/paper_verification_report.py
  - 実行例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 引数:
    --from / --to : レポート期間（YYYY-MM-DD）
    --db : SQLite DB パス（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

注意点 / 運用関連
----------------
- ログ:
  - ログは kabusys.utils.logging_setup.setup_logging で統一的に設定され、デフォルトで logs/<app_name>.log に日次ローテーションで出力されます。
  - LOG_DIR / LOG_LEVEL でカスタマイズ可能。

- Kill Switch / 停止フラグ:
  - KillSwitch（kabusys.monitoring.kill_switch）はリスクトリガー（ドローダウン／ポジション上限）で data/kill.flag を書き込み、ExecutionEngine に停止指示を出します。
  - ExecutionEngine や Monitoring の手動停止は data/stop_requested.flag を作ることで行います。停止フラグはファイルの存在チェックで行われます。

- DB 初期化:
  - monitoring_db.init_monitoring_db() で必要なテーブル・インデックスが（冪等に）作成されます。run_* スクリプトは起動時に自動で実行します。

- 環境に応じた DB:
  - monitoring 系では常に settings.sqlite_path（監視 DB）を使用します。
  - ExecutionEngine は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使って本番 DB と完全分離します。

- OpenAI（AI モジュール）:
  - news_nlp.score_news / regime_detector.score_regime は OPENAI_API_KEY（引数でも指定可）が必要です。
  - API 呼び出しはリトライやフォールバック（失敗時は安全値で継続）を行う設計です。

ディレクトリ構成（主要）
----------------------
src/kabusys/
- __init__.py                    — パッケージ定義、バージョン
- config.py                      — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 起動前の設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト

パッケージ群
- ai/
  - news_nlp.py                  — ニュースを LLM で評価して ai_scores に書き込む
  - regime_detector.py           — マクロ + MA200 による市場レジーム判定
- monitoring/
  - monitoring_db.py             — SQLite による監視データ永続化層
  - system_monitor.py            — システム状態・データ鮮度チェック
  - trade_monitor.py             — （滞留注文など）注文監視ロジック
  - risk_monitor.py              — ドローダウン・ポジション数監視
  - kill_switch.py               — kill.flag の作成・管理
  - monitoring_engine.py         — 複数モニタの統合ポーリングエンジン
  - alert_manager.py             — アラート送信管理（LINE 等）
- execution/
  - execution_engine.py          — 実行エンジン本体
  - broker_factory.py            — ブローカークライアント生成（本番 / mock 切替）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
- portfolio/
  - portfolio_builder.py         — 候補選定、重み計算
  - position_sizing.py           — 株数決定、単元丸め、集約制限
  - risk_adjustment.py           — セクターキャップ、レジーム乗数
- research/
  - factor_research.py           — ファクター計算（momentum/volatility/value）
  - feature_exploration.py       — forward returns, IC, 統計サマリ
- utils/
  - logging_setup.py             — ログ設定ユーティリティ
  - process_priority.py          — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

よく使うコマンドまとめ
---------------------
- .env を作る（ウィザード）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution Engine 起動:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動:
  python -m kabusys.run_monitoring
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足 / 注意
-----------
- KABUSYS_ENV=live を使用する場合は設定（APIキー、LINE通知、KILL_SWITCH 設定等）を十分確認してください。validate_config は live 環境での追加警告を出します。
- セキュリティ: .env は決して Git にコミットしないでください（config_setup のヘッダにも注意書きがあります）。
- 自動ロード: config.py はプロジェクトルートを .git や pyproject.toml で探索し、.env/.env.local を自動で読み込みます。テストや CI などで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

貢献 / 問い合わせ
------------------
バグ報告や提案は Issue を作成してください。各モジュールは責務を分離しているため、ユニットテスト追加や個別改善が比較的容易です。