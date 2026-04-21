KabuSys — 日本株自動売買システム（簡易 README）
================================

概要
---
KabuSys は日本株の自動売買 / 研究用ツール群です。本リポジトリは以下の主要機能を備えます。

- 発注・実行エンジン（ExecutionEngine）
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
- ポートフォリオ構築・ポジションサイズ計算モジュール（純粋関数群）
- リサーチ用ファクター計算・特徴量探索モジュール（DuckDB ベース）
- OpenAI を使ったニュース NLP・市場レジーム判定
- ペーパートレード検証用レポート生成ツール

本 README は開発者 / 運用担当者向けに、セットアップ・起動方法、主要機能、ディレクトリ構成を日本語でまとめたものです。

主な機能一覧
---
- Execution
  - 実取引（live）／ペーパートレード（paper_trading）の切替
  - BrokerClientFactory により実ブローカー or MockBroker を選択
  - RiskManager / OrderManager / Reconciler 等を組み合わせたセッション実行
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor / RiskMonitor と合わせて総合監視
  - KillSwitch: 条件（ドローダウン超過など）で実行エンジン停止フラグ（data/kill.flag）を書き込み
  - MonitoringEngine: ポーリングループで定期実行
- Portfolio（純粋関数）
  - 候補選定、等金額/スコア加重、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- Research（DuckDB）
  - Momentum / Volatility / Value 等のファクター計算
  - Forward returns / IC / 基本統計量計算
- AI（OpenAI）
  - ニュース記事のセンチメントスコア付与（ai_scores テーブルへ書込み）
  - 市場レジーム判定（regime_detector）
- ツール
  - .env 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

要件（概略）
---
- Python 3.10 以上（型記法や union operator(|) を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の検証に使用）
- SQLite は標準ライブラリで利用
- ローカル実行では kabuステーション等の外部 API が別途必要（実運用時）

セットアップ手順
---
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必須パッケージをインストール
   - pip install duckdb psutil openai
   - （開発用）pip install PyYAML

   ※ requirements.txt は本リポジトリに含まれていないため、実際の運用ではプロジェクトの要件に合わせて requirements を用意してください。

3. プロジェクトルートに .env を作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して手動で作成
   - 自動読み込み:
     - config.Settings はプロジェクトルート（.git または pyproject.toml）から .env/.env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。

4. 必須の環境変数（例）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）

5. ディレクトリと初期 DB
   - data/ および logs/ は自動作成されますが、必要に応じて事前に作成して権限を確認してください。

設定検証
---
- .env や config/*.yaml の検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

主要コマンド・使い方
---
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（実行エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading とすると MockBrokerClient が使われ、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録します。
  - 実行中の停止:
    - data/stop_requested.flag を作成すると起動スクリプトが検知して順次停止します。
    - Kill Switch（data/kill.flag）はモニタ側から書き込まれ、ExecutionEngine が起動時・稼働中に停止される仕組みです。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - デフォルトは 60 秒間隔でポーリング。MONITOR_POLL_INTERVAL 環境変数で秒数を上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は常に本番の sqlite_path（Settings.sqlite_path: data/monitoring.db）を使用します（環境に依らず）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能
  - ニュースセンチメント付与（news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
  - どちらも OPENAI_API_KEY（または api_key 引数）の設定が必要です。API 呼び出しは retry/backoff を備え、失敗時は安全側のフォールバックを行います。

重要な環境変数（抜粋）
---
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- OPENAI_API_KEY — OpenAI API（AI 機能に必要）
- LOG_LEVEL / LOG_DIR — ログ関連（logging_setup を介して使用）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で使用）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant / partial / never / reject）

ログ・運用ノート
---
- ロギングは kabusys.utils.logging_setup.setup_logging を利用。デフォルトは logs/<app_name>.log に日次ローテーションで出力（30日保持）。
- stdout（コンソール）にも出力します（StreamHandler）。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- プロセス優先度設定:
  - 起動スクリプトは set_process_priority("high") を試みます（psutil 必須）。権限や OS によっては警告を出してスキップします。
- 停止フラグ:
  - data/stop_requested.flag — run_* スクリプトがポーリングごとにチェックし、あればループを抜けます（優雅な終了）。
  - data/kill.flag — KillSwitch が書き込むファイル。ExecutionEngine の停止トリガーとして運用されます。
  - data/execution.pid — ExecutionEngine が PID を書く (監視用)。

ディレクトリ構成（概要）
---
以下は主要ファイル/モジュールのツリー（src/kabusys を起点とした抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring ポーリング起動スクリプト

  - utils/
    - logging_setup.py             — ログ初期化ユーティリティ
    - process_priority.py          — プロセス優先度・CPU affinity 設定
    - __init__.py

  - monitoring/
    - monitoring_db.py             — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py              — （コードベースに存在）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py              — （アラート送信ロジック等）

  - execution/
    - execution_engine.py          — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py            — Broker クライアント生成
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
    - news_nlp.py                   — ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py            — 市場レジーム判定（OpenAI と MA 合成）
    - __init__.py

  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
    - __init__.py

補足 / 運用上の注意
---
- KABUSYS_ENV=live での起動は実際に発注が行われるため、設定値（API パスワード・LINE 通知設定・Kill Flag 設定など）を十分確認してください。validate_config は live 時に追加警告を出します。
- AI（OpenAI）利用部分は API コストが発生します。頻度・バッチサイズに注意してください（news_nlp はバッチ処理・リトライロジックあり）。
- DuckDB を使ったリサーチ機能は prices_daily / raw_financials / raw_news などのテーブル依存があります。データ投入は別スクリプトや ETL による準備が前提です。
- DB マイグレーションは簡易に実装されています（monitoring_db.init_monitoring_db は必要カラム追加のための ALTER を行います）。運用ではバックアップを推奨します。

FAQ（短）
---
Q: ペーパートレードを実行するには？
A: .env の KABUSYS_ENV=paper_trading を設定してから python -m kabusys.run_execution を実行します。データは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）に保存されます。

Q: 監視のポーリング間隔を変えたい
A: MONITOR_POLL_INTERVAL 環境変数（秒）を設定してください（例: export MONITOR_POLL_INTERVAL=30）。

Q: .env を自動で読み込まないようにするには？
A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（主にテスト用）。

最後に
---
この README はコードベースから主要な動作・運用情報を抜粋してまとめたものです。詳細な設計仕様（PortfolioConstruction.md、StrategyModel.md 等）や実運用手順は別途ドキュメントを参照してください。質問や補足があれば教えてください。