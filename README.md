KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的としたパッケージ群です。本コードベースは以下の主要機能を備えます。

- 注文実行エンジン（ExecutionEngine）：実際の発注・ペーパートレードの両対応
- 監視（Monitoring）：システム状態・注文状況・リスクをポーリングしてログ/アラート出力
- ポートフォリオ構築ユーティリティ（選定、重み付け、ポジションサイジング）
- 研究用モジュール（ファクター計算・将来リターン・IC計算）
- AI 支援モジュール（ニュースセンチメント評価、レジーム判定）
- 各種 CLI ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

主要な設計方針の抜粋
- Paper Trading は本番データベースと完全に分離（デフォルト: data/paper_trading.db）。
- Logging は統一的に設定（logs/<app>.log、日次ローテーション）。
- 外部 API 呼び出し（OpenAI 等）はフェイルセーフ設計（失敗時にフォールバック）。
- ルックアヘッドバイアス対策：日付参照は明示的な target_date を使う実装が基本。

機能一覧
--------
- 実行関連
  - run_execution.py：ExecutionEngine を起動。KABUSYS_ENV=paper_trading のときは MockBroker を使用。
  - 発注履歴・取引ログの永続化（SQLite）。
  - RiskManager / OrderManager / Reconciler 等のコンポーネントで安全制御。

- 監視関連
  - run_monitoring.py：SystemMonitor を定期実行するシンプルなポーリングループ（デフォルト 60 秒）。
  - MonitoringEngine：SystemMonitor, TradeMonitor, RiskMonitor の束ね処理。Kill Switch 評価、アラート通知。
  - MonitoringDB：SQLite に監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）を管理。

- ポートフォリオ構築（純粋関数群・副作用なし）
  - 候補選定、等金額/スコア加重配分、スコアベースの位置サイズ計算、セクター上限適用、レジーム乗数。

- 研究（DuckDB ベース）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー

- AI（OpenAI 連携）
  - news_nlp.score_news：ニュース記事を集約し LLM でセンチメント評価、ai_scores に書き込み
  - regime_detector.score_regime：ETF MA とマクロニュースを合成して市場レジーム判定

- ツール
  - config_setup.py：対話式 .env 作成ウィザード
  - validate_config.py：環境変数 / config/*.yaml の事前検証 CLI
  - tools.paper_verification_report：ペーパートレードの検証レポート出力

セットアップ手順
----------------
以下は推奨のローカルセットアップ手順（例）。実運用時は環境に合わせて調整してください。

1. Python 環境の準備
   - Python 3.10+ を推奨
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール（requirements.txt がない場合は必要な主要パッケージを個別に）
   - pip install duckdb psutil openai
   - (オプション) PyYAML があると config/*.yaml の検証を行える: pip install PyYAML

3. リポジトリルートで初期ディレクトリを用意
   - data/ と logs/ ディレクトリは自動作成されることが多いですが、必要なら手動で作成:
     - mkdir -p data logs

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を作成（本リポジトリに example がない場合は下の「重要な環境変数」を参照）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになる

6. DB 初期化
   - 実行スクリプトが起動時に monitoring DB 初期化を行います（init_monitoring_db が冪等でテーブル作成・マイグレーションを実施）。

重要な環境変数（主要）
---------------------
必須（最低限設定が必要なもの）
- JQUANTS_REFRESH_TOKEN：J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD：kabuステーション API パスワード

運用上重要
- KABUSYS_ENV：実行環境（development | paper_trading | live）。デフォルトは development
  - paper_trading の場合、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- OPENAI_API_KEY：OpenAI 呼び出しに必要（AI 機能使用時）
- PAPER_FILL_MODE：ペーパートレードの約定挙動（instant|partial|never|reject）。デフォルト instant

DB / ログ関連
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH：ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL：ログレベル（DEBUG/INFO/...）
- LOG_DIR：ログ保存ディレクトリ（デフォルト logs/）

監視・制御フラグ
- data/kill.flag：Kill Switch が書き込む停止フラグ（ExecutionEngine 側で検知）
- data/stop_requested.flag：run_monitoring/run_execution が参照する停止フラグ（手動で置いてプロセスを止める）
- data/execution.pid：ExecutionEngine の PID ファイル

使い方（実行例）
----------------

- 環境作成（.env ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - 本番/開発/ペーパートレードは KABUSYS_ENV で切り替え
  - 例（通常）:
    - python -m kabusys.run_execution
  - ペーパートレード用 DB を指定する場合は環境変数:
    - export KABUSYS_ENV=paper_trading
    - export PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
    - python -m kabusys.run_execution

- Monitoring を起動（SystemMonitor の単体ループ）
  - MONITOR_POLL_INTERVAL で間隔秒を上書き可能（デフォルト 60）
  - 例:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite path 上書き可能（環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）

- AI 機能の呼び出し（プログラム内 API）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")

ファイル・ディレクトリ構成（主なファイル）
---------------------------------------
（src/kabusys 以下を想定）

- __init__.py
- config.py
  - Settings クラス：環境変数読み込み・自動 .env ロードロジック
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前チェック CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- tools/
  - paper_verification_report.py
- portfolio/
  - portfolio_builder.py（select_candidates, calc_equal_weights, calc_score_weights）
  - position_sizing.py（calc_position_sizes）
  - risk_adjustment.py（apply_sector_cap, calc_regime_multiplier）
- research/
  - factor_research.py（calc_momentum, calc_volatility, calc_value）
  - feature_exploration.py（calc_forward_returns, calc_ic, factor_summary）
- ai/
  - news_nlp.py（score_news）
  - regime_detector.py（score_regime）
- monitoring/
  - monitoring_db.py（SQLite テーブル定義, MonitoringDB クラス）
  - system_monitor.py（SystemMonitor, SystemCheckResult）
  - risk_monitor.py（RiskMonitor）
  - kill_switch.py（KillSwitch）
  - monitoring_engine.py（MonitoringEngine）
  - trade_monitor.py（TradeMonitor — 参照あり）
- execution/
  - order_manager.py, order_repository.py, execution_engine.py 等（実行時のコアロジック）
- utils/
  - logging_setup.py（setup_logging）
  - process_priority.py（プロセス優先度 / CPU affinity 設定）
- data/ （ランタイム生成想定）
  - monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid など
- logs/
  - execution.log, monitoring.log, ...（日次ローテーション）

運用上の注意点
--------------
- KABUSYS_ENV=live の場合は特に注意して .env の内容・LINE 通知設定・Kill Switch 設定を確認してください（validate_config の live チェックが警告を出します）。
- run_execution は起動時に stop flag を確認します。停止時は data/stop_requested.flag を作成するか、Kill Switch（data/kill.flag）を使用してください。
- Logging はデフォルトで logs/<app>.log に日次ローテーションで出力します。ログディレクトリ作成に失敗するとコンソール出力のみになります。
- OpenAI を用いる機能（news_nlp, regime_detector）は API_KEY が必要です。リトライやフェイルセーフは備えていますが、API 利用時のコスト・レイテンシは考慮してください。
- DuckDB / SQLite のパスは Settings で指定可能。環境に合わせてバックアップ／パーミッション管理を行ってください。

開発者向けメモ
---------------
- Settings は .env 自動読み込みを行いますが、テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- monitoring_db.init_monitoring_db は冪等でテーブル作成と簡易マイグレーションを行います（カラム追加など）。
- utils.process_priority.set_process_priority は OS に依存した実装です。権限がない場合は警告でスキップされます。
- research モジュールは DuckDB 接続を受け取り、SQL と Python を組み合わせて計算します。ユニットテストは DuckDB のメモリ・テスト DB で簡単に実行できます。

サポートライブラリ（参考）
- duckdb
- psutil
- openai（AI 機能）
- PyYAML（config 検証をする場合に任意）

最後に
-----
この README はコードベースの主要箇所に基づいて作成しています。実運用前に python -m kabusys.validate_config で確認し、特に KABUSYS_ENV=live のときは .env の中身と Kill Switch の動作を十分にテストしてください。質問や補足があれば、必要な箇所を指定していただければ README を拡張します。