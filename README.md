README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のライブラリ兼実行スクリプト群です。
主な責務は以下の通りです。

- 戦略・ポートフォリオ構築ロジック（ファクター計算、ポジションサイジング等）
- 実行エンジン（ExecutionEngine）とブローカークライアントのラッパー
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- AI を使ったニュース NLP / 市場レジーム判定（OpenAI を利用）
- Paper Trading の検証レポート生成ツール

このリポジトリはライブラリとしての関数群と、実運用／検証に使う CLI スクリプトを含みます。

主な機能一覧
--------------
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 環境設定
  - config_setup.py: 対話式ウィザードで .env を初期作成／更新
  - validate_config.py: .env と config/*.yaml の妥当性チェック
- 監視系
  - monitoring/monitoring_engine.py: 各 Monitor を束ねるエンジン
  - monitoring/system_monitor.py: CPU・メモリ・ディスク・データ鮮度・プロセス存在チェック
  - monitoring/risk_monitor.py: ドローダウン・ポジション上限チェック、ダッシュボード更新、リスクログ
  - monitoring/kill_switch.py: kill.flag により ExecutionEngine を停止させる仕組み
  - monitoring/monitoring_db.py: SQLite による永続層（schema と読み書きユーティリティ）
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定・重み計算（等配分・スコア配分）
  - portfolio/position_sizing.py: 発注株数・リスクベース配分、単元丸め、キャップ適用
  - portfolio/risk_adjustment.py: セクターキャップ・レジーム乗数
- リサーチ / ファクター
  - research/factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
  - research/feature_exploration.py: 将来リターン計算、IC 計算、統計サマリー
- AI
  - ai/news_nlp.py: raw_news を集約して OpenAI に投げ、銘柄毎にセンチメントを ai_scores へ書き込み
  - ai/regime_detector.py: ETF とマクロニュースを組み合わせて market_regime を算出・書き込み
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定（Windows/Linux 抽象化）
- ツール
  - tools/paper_verification_report.py: Paper Trading DB を解析して検証レポートを生成

セットアップ手順
----------------
1. Python バージョン
   - Python 3.10+ を推奨（typing の演算子や型ヒントを使用）

2. 依存パッケージ（最低限）
   - duckdb
   - psutil
   - openai (AI 機能利用時)
   - PyYAML (validate_config の YAML 検証を行う場合)
   インストール例:
     pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそちらを使用してください）

3. プロジェクトルート配置
   - リポジトリ直下に置いた状態でスクリプトは .env / data / logs 等をルート相対で参照します。

4. .env の準備
   - 対話式で .env を作るには:
       python -m kabusys.config_setup
   - 必須環境変数:
       JQUANTS_REFRESH_TOKEN
       KABU_API_PASSWORD
   - 推奨設定（例）:
       KABUSYS_ENV=development
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       LOG_LEVEL=INFO
       KILL_FLAG_CLEAR_ON_START=0

   - 自動ロード: デフォルトでプロジェクトルートの .env と .env.local を自動読み込みします（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

5. データディレクトリ作成
   - デフォルトは data/（monitoring DB・paper trading DB・pid/flag ファイル）と logs/（ログ）を使用します。起動時にディレクトリ作成処理が入る箇所もありますが、手動で作成して権限等を確認しておくと良いです。

使い方（主なコマンド）
--------------------
- 設定ウィザード（.env 作成）
    python -m kabusys.config_setup

- 設定検証（起動前チェック）
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict   # 警告も失敗扱いにする

- 実行エンジン起動
    python -m kabusys.run_execution
  補足:
    - KABUSYS_ENV=paper_trading のとき、MockBrokerClient を使用し paper_trading 用 DB（デフォルト: data/paper_trading.db）に記録します。
    - 実行中に data/stop_requested.flag を作成するとエンジンが停止します。
    - 実行中は data/execution.pid に PID を書きます（PID ファイルパスは Settings で変更可）。

- 監視（SystemMonitor）起動
    python -m kabusys.run_monitoring
  補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用します（監視専用 DB）。
    - data/stop_requested.flag を置くと監視ループを終了します。

- Paper Trading 検証レポート出力
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  補足:
    - DB パスは引数 --db または環境変数 PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）

重要なファイル／フラグの挙動
----------------------------
- data/kill.flag
  - KillSwitch が書き込む停止フラグ。ExecutionEngine はこのファイルの存在を検知して安全停止します。
  - KillSwitch はリスク条件（ドローダウンやポジション上限）で作成されることがあります。
- data/stop_requested.flag
  - run_monitoring / run_execution の簡易停止フラグ。存在を検知すると各ループが終了します。
- PID ファイル (デフォルト data/execution.pid)
  - run_execution が PID を書き込みます。プロセス管理やデバッグで参照します。
- DB
  - 監視用 SQLite: デフォルト data/monitoring.db（monitoring_db.init_monitoring_db がスキーマを作成）
  - DuckDB: デフォルト data/kabusys.duckdb（リサーチ・AI 用の分析ストア）
  - Paper Trading DB: data/paper_trading.db（KABUSYS_ENV=paper_trading の場合に利用）

環境変数（主要）
----------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード:
  - KABUSYS_ENV ＝ development | paper_trading | live
- ログ／ファイル:
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- AI（OpenAI）:
  - OPENAI_API_KEY（ai/news_nlp.py や ai/regime_detector.py を使用する場合）
- 監視設定:
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数）

ディレクトリ構成（抜粋）
-----------------------
（src/kabusys 以下）

- __init__.py
- config.py                — 環境変数読み込み・Settings クラス（.env 自動ロード含む）
- config_setup.py          — .env 作成ウィザード
- validate_config.py       — 起動前検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

- ai/
  - news_nlp.py            — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py     — マクロ + ETF MA で市場レジーム判定

- monitoring/
  - monitoring_db.py       — SQLite スキーマと DB 操作ユーティリティ
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - system_monitor.py      — システム状態・データ鮮度監視
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — Kill Switch（kill.flag 操作）
  - ...（trade_monitor, alert_manager 等が想定される）

- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 発注株数計算・資金配分
  - risk_adjustment.py     — セクターキャップ・レジーム乗数

- research/
  - factor_research.py     — Momentum / Value / Volatility 等の計算（DuckDB）
  - feature_exploration.py — IC / forward returns / 統計サマリ

- utils/
  - logging_setup.py       — 共通ログ設定（stdout + ローテートファイル）
  - process_priority.py    — プロセス優先度設定（クロスプラットフォーム）

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート

追加ノート / ベストプラクティス
------------------------------
- 本番運用（KABUSYS_ENV=live）の場合、LINE 通知や kill flag の設定を確認してください（validate_config に本番チェックがあります）。
- OpenAI を使用する機能は API キーとコストが必要です。開発時は無効化またはモックして動作確認してください。news_nlp._call_openai_api / regime_detector._call_openai_api はテストでパッチしやすい設計にしています。
- logs/ ディレクトリはデフォルトで使用されます。ログローテーションは utils/logging_setup.py により日次で行われます。
- .env は決して公開リポジトリにコミットしないでください（config_setup.py のヘッダに警告あり）。

サポート / 開発
----------------
- 設定や実行に関する簡易チェックは validate_config.py を使ってください。
- 単体テストや CI を追加する場合、KABUSYS_DISABLE_AUTO_ENV_LOAD を有効化して環境依存を切り離すことを検討してください。
- DuckDB のテーブルスキーマ（prices_daily, raw_financials, raw_news 等）はリサーチ / AI モジュールで想定されるため、実際に使う場合はデータ準備スクリプトを別途用意してください。

以上。必要であれば README にサンプル .env 内容、起動例（systemd ユニットや supervisord の例）、さらに詳しい DB スキーマの説明を追加できます。どの情報を優先して追加しますか？