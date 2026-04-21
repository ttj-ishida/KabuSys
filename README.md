KabuSys
=======

日本株自動売買システム（KabuSys）の簡易ドキュメントです。本リポジトリはトレーディング実行エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）等のコンポーネントで構成されています。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買/リサーチフレームワークです。主要な設計方針は次の通りです。

- 実行エンジン（ExecutionEngine）で発注・リスク管理を行う（本番 / ペーパートレード対応）。
- 監視（Monitoring）でシステム稼働・注文状況・リスクをポーリングし、必要に応じて Kill Switch を発動。
- ポートフォリオ構築/ポジションサイジングは純粋関数群として実装（DB 参照なし）。
- DuckDB を用いたリサーチ・ファクター計算、OpenAI を用いたニュースセンチメント評価（オプション）。
- .env ベースで設定を管理し、対話式ウィザード・検証ツールを付属。

主な機能一覧
-------------
- Execution
  - 実際のブローカークライアントまたは MockBrokerClient（KABUSYS_ENV=paper_trading）で動作
  - リスク管理（max position, utilization, drawdown など）
  - 発注履歴の永続化（SQLite / DuckDB）
- Monitoring
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（prices_daily 等）
  - 注文滞留・約定異常・ドローダウン監視
  - Kill Switch（data/kill.flag）による ExecutionEngine 停止
- Portfolio（銘柄選定・ウェイト計算・株数決定）
  - 等金額 / スコア加重 / リスクベースのポジション決定
  - セクターキャップ・レジーム乗数適用
- Research
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン、IC 計算、統計サマリー
- AI（任意）
  - ニュース NLP（OpenAI）で銘柄別センチメントを ai_scores に格納
  - レジーム判定（ma200 + マクロニュースの LLM センチメント）
- ツール
  - 設定ウィザード（.env 作成）: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------

1. Python 環境（3.9+ 推奨）準備

2. 依存パッケージをインストール（例）
   - duckdb
   - psutil
   - openai（ニュース/レジーム機能を使う場合）
   - PyYAML（config/*.yaml の検証を行う場合）
   例:
   pip install duckdb psutil openai PyYAML

3. .env の作成（対話式ウィザード推奨）
   リポジトリルートで:
   python -m kabusys.config_setup
   ウィザードは .env を生成します。生成後、設定検証を行うことを推奨します:
   python -m kabusys.validate_config

4. 必須環境変数（.env に設定）
   - JQUANTS_REFRESH_TOKEN : J-Quants API 用（必須）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
   任意 / デフォルト:
   - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
   - DUCKDB_PATH : data/kabusys.duckdb
   - SQLITE_PATH : data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH : data/paper_trading.db（paper_trading 用）
   - LOG_LEVEL : INFO / DEBUG / ...
   - OPENAI_API_KEY : OpenAI を使用する場合

5. ログディレクトリ
   - デフォルトは logs/。必要に応じて LOG_DIR 環境変数で変更可能。
   - ログは日次ローテート（30日分保持）。

主要な環境変数の説明（抜粋）
--------------------------------
- KABUSYS_ENV: 実行モード。development / paper_trading / live
  - paper_trading の場合、MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
- SQLITE_PATH: 監視 DB（monitoring.db）パス（Monitoring は環境にかかわらず sqlite_path を使用します）。
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading 時に使用）。
- DUCKDB_PATH: 分析用 DuckDB ファイルパス。
- LOG_LEVEL / LOG_DIR: ログ出力設定。
- OPENAI_API_KEY: ニュース NLP / レジーム判定 のための OpenAI API キー。
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）。run_monitoring.py で利用。
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject）

使い方（CLI・スクリプト）
------------------------

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  --strict を付けると警告も失敗扱い（exit(1)）になります。

- 実行エンジン起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使います。
  - 起動時に data/execution.pid を書き、停止は data/stop_requested.flag の作成で行えます。
  - 起動前に kill.flag（data/kill.flag）がある場合、エンジンは起動しません（Kill Switch の保護）。

- 監視ループ起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を上書き可能（デフォルト 60 秒）。
  - 監視は環境に依らず Settings.sqlite_path（本番監視 DB）を使用します。
  - 停止は data/stop_requested.flag を作成するか Ctrl+C。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db で指定可能。

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定してください。モジュールは kabusys.ai.news_nlp.score_news や kabusys.ai.regime_detector.score_regime を提供します。
  - API 呼び出しではリトライやフェイルセーフ（失敗時はスコア 0 でフォールバック等）が実装されています。

停止 / Kill Switch
-------------------
- Kill Switch を手動で発動する場合は data/kill.flag に理由テキストを書き込むことで、ExecutionEngine の起動を阻止したり実行中のエンジンに停止シグナルを送る仕組みがあります（kill_switch.py）。
- 監視サブシステムは条件（ドローダウン超過・ポジション上限超過等）で kill.flag を書き込みます。
- run_execution/run_monitoring が終了するための一時停止フラグは data/stop_requested.flag を使用します。

ディレクトリ構成
-----------------
以下は src/kabusys 以下の主要ファイルと説明（抜粋）です。

- __init__.py
  - パッケージ定義、バージョン番号

- config.py
  - Settings クラス: 環境変数 / .env の読み込み・検証ロジック
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを抑止可能

- config_setup.py
  - .env を対話式に生成・更新するウィザード

- validate_config.py
  - .env と config/*.yaml を起動前に検証する CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（pid / stop フラグの管理、paper_trading 分離）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）

- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化・読み書きラッパー
  - system_monitor.py: システムリソース・データ鮮度チェック
  - trade_monitor.py: 注文滞留・約定異常チェック（省略ファイルは多数存在）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 管理
  - monitoring_engine.py: 各 Monitor を束ねるエンジン

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py など
  - ExecutionEngine のコアロジックとブローカーインタフェース

- portfolio/
  - portfolio_builder.py: 候補選定・ウェイト計算
  - position_sizing.py: 株数決定・スケーリング
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: モメンタム／ボラティリティ／バリュー等の計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC・統計サマリー

- ai/
  - news_nlp.py: ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py: ma200 + LLM マクロセンチメントでレジーム判定

- utils/
  - logging_setup.py: 共通ロギング設定（stdout + 日次ローテートファイル）
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成スクリプト

簡易ファイルツリー（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/
    - monitoring/
    - portfolio/
    - research/
    - ai/
    - utils/
    - tools/

追加の注意点 / ベストプラクティス
---------------------------------
- .env は絶対にバージョン管理しないでください（config_setup のヘッダに注意文有り）。
- 本番（KABUSYS_ENV=live）では kill.flag 周り・LINE 通知等を十分に設定・確認してください。
- Monitoring は監視 DB（SQLITE_PATH）を常に使用します。paper_trading の場合でも監視 DB は切り替わりません（設計上の注意）。
- OpenAI を使う機能は API コスト・レートリミットを考慮してください。デフォルトでリトライとバッチ処理を実装していますが、キー管理は慎重に。

その他
-----
- さらに詳しい設計ノート（PortfolioConstruction.md、StrategyModel.md 等）が別途ある前提の実装コメントが多く含まれています。必要に応じて設計資料を参照してください。
- ご不明点があれば、どの機能（実行エンジン / 監視 / AI 等）について知りたいか指定して質問してください。設計意図や運用上の注意点について詳しく補足します。