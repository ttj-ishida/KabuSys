KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株自動売買システム「KabuSys」のコアユーティリティ群です。発注エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AIベースのニュース解析など、運用に必要な主要コンポーネントを含みます。

主な目的:
- 本番/ペーパートレード双方で動作する ExecutionEngine と Broker クライアント抽象
- システム稼働性や注文状態を記録・監視する Monitoring
- ポートフォリオ構築（銘柄選定、重み計算、株数決定）用の純粋関数群
- DuckDB を用いたリサーチ/ファクター計算
- OpenAI を用いたニュースセンチメントスコアリング／レジーム判定
- .env の対話式セットアップと起動前検証ツール

機能一覧
--------
- 環境設定ウィザード（python -m kabusys.config_setup）で .env ファイル生成
- 設定検証 CLI（python -m kabusys.validate_config）で必須環境変数や設定ファイルを検証
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のときはペーパートレード専用 DB を使用
  - プロセス優先度を設定し、PID ファイル / stop フラグを監視
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - システム状態、注文・リスク監視、Kill Switch 評価などのポーリング
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を参照（環境に依存しない）
- Paper Trading 検証レポート生成ツール（python -m kabusys.tools.paper_verification_report）
- ポートフォリオ構築モジュール
  - 銘柄選定（select_candidates）
  - 重み計算（calc_equal_weights, calc_score_weights）
  - 単元丸め・リスク制御を伴う株数計算（calc_position_sizes）
  - セクター制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）
- Research モジュール（DuckDB 利用）
  - モメンタム / ボラティリティ / バリューなどの因子計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン・IC・統計サマリー等の分析ユーティリティ
- AI モジュール
  - ニュースを LLM (OpenAI) でスコアリングし ai_scores に書き込む（news_nlp.score_news）
  - マクロニュースと ETF の MA200 を組み合わせたレジーム判定（regime_detector.score_regime）
- ロギングとプロセス優先度ユーティリティ（logs への日次ローテート、プロセス priority / affinity 設定）
- SQLite（監視ログ）向け永続化層（monitoring_db.py）と監視ロジック（risk_monitor, system_monitor, trade_monitor 等）

セットアップ手順
----------------
1. 推奨 Python バージョン
   - Python 3.10+ を想定（typing の一部表記が使われているため）

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージのインストール（最小限）
   - pip install duckdb psutil openai
   - 開発時に YAML 検証を有効にする場合: pip install PyYAML
   - （プロジェクトに requirements.txt がない場合、上記を目安にインストールしてください）

4. プロジェクトルートに移動
   - 本モジュールはプロジェクトルート（pyproject.toml または .git を基準）を自動検出します。

5. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（DEBUG/INFO/...）

6. 設定検証
   - python -m kabusys.validate_config
   - 重大な不足があると exit code が 1 になります。--strict を付けると警告も FAIL 扱いになります。

使い方
-------
- ExecutionEngine（発注エンジン）起動
  - 実行: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のとき、ペーパートレード DB (PAPER_TRADING_SQLITE_PATH) を使用
  - 起動時に data/execution.pid に PID を書き、 data/stop_requested.flag を監視して停止します
  - ExecutionEngine は起動前に kill flag (Settings.kill_flag_path) を確認します

- Monitoring（監視）起動
  - 実行: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視スクリプトは常に Settings.sqlite_path（本番パス）を使用して monitoring のテーブルを初期化します
  - 停止: data/stop_requested.flag を作成すると監視ループは終了します（または Ctrl-C）

- .env 操作
  - 対話式作成: python -m kabusys.config_setup
  - 検証: python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）
  - デフォルト DB: data/paper_trading.db

- AI 機能（プログラム的に呼ぶ）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

- Research / Portfolio（プログラム的に）
  - 例: from kabusys.research import calc_momentum; calc_momentum(duckdb_conn, date)
  - Portfolio 関数は kabusys.portfolio から利用可能:
    - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

運用上の注意
------------
- 監視 DB（Settings.sqlite_path）とペーパートレード DB（PAPER_TRADING_SQLITE_PATH）は分離されています。ペーパートレード時に本番 DB を上書きしないよう注意してください。
- KABUSYS_ENV=live の場合は本番動作となるため、設定（LINE 通知トークン、Kill Switch の設定等）を慎重に確認してください。
- Kill Switch:
  - kabusys.monitoring.kill_switch.KillSwitch は drawdown やポジション上限違反などで data/kill.flag を生成し、ExecutionEngine 側がこれを検知して停止できます。
  - Settings.KILL_FLAG_CLEAR_ON_START=1 を使うと起動時に自動で kill.flag をクリアしますが、本番では 0 を推奨します。
- ロギング:
  - デフォルトは logs/<app_name>.log（TimedRotatingFileHandler、日次ローテート、30日保持）
  - 標準出力は stdout に出力されます（cron 等で stdout を集約しやすくするため）

ディレクトリ構成
----------------
（主要なファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数/設定管理（自動 .env ロード含む）
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py           — ロギング設定ユーティリティ
      - process_priority.py        — プロセス優先度 / CPU affinity 設定
    - monitoring/
      - monitoring_db.py           — SQLite 永続化層（監視用テーブル）
      - monitoring_engine.py       — 各 Monitor を束ねるエンジン
      - system_monitor.py          — システム・データ鮮度監視
      - risk_monitor.py            — ドローダウン・ポジション監視
      - kill_switch.py             — Kill Switch (flag ファイル)
      - ...（trade_monitor, alert_manager 等が存在する想定）
    - execution/
      - execution_engine.py        — 発注エンジン本体（EngineConfig 等）
      - broker_factory.py          — BrokerClient の生成（Mock / 実ブローカー分岐）
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
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
      - news_nlp.py                — ニュース NLP スコアリング
      - regime_detector.py         — レジーム判定
      - __init__.py
    - tools/
      - paper_verification_report.py
    - data/                         — 実行時に使うファイル（デフォルト）
      - monitoring.db (SQLITE_PATH)
      - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
      - kabusys.duckdb (DUCKDB_PATH)
      - execution.pid
      - kill.flag
      - stop_requested.flag

補足: 実装上の注意点
-------------------
- config.py はプロジェクトルートを .git / pyproject.toml で自動検出し、.env/.env.local を自動ロードします。テスト時などに自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- monitoring の初期化関数 init_monitoring_db は冪等的にテーブル・インデックスを作成し、古い DB に対するマイグレーション（カラム追加）も行います。
- AI 部分は OpenAI の API レスポンス失敗に対してフェイルセーフ（スコア 0.0 やスキップ）を採る設計です。API キーは OPENAI_API_KEY を使用します。

ライセンス / 貢献
-----------------
README には載せていませんが、実際の公開リポジトリでは LICENSE と CONTRIBUTING を追加してください。

問題や不明点があれば、どの機能のドキュメントを詳しく書くか（例: ExecutionEngine の起動フロー、DB スキーマ詳細、AI プロンプト形式、テストの方法）を教えてください。必要に応じて追加の使用例やサンプル .env テンプレートも作成します。