README
=====

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。本リポジトリは以下の主要機能を含みます。
- 発注エンジン（ExecutionEngine）と発注管理
- 監視サブシステム（System / Trade / Risk の監視、Kill Switch）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ）
- ファクター計算・リサーチ用ユーティリティ（DuckDB を利用した計算）
- OpenAI を使ったニュース NLP / 市場レジーム判定
- 各種 CLI ツール（環境設定ウィザード、設定検証、紙トレ検証レポート等）

主な設計方針
- 環境依存設定は環境変数（.env）で管理。プロジェクトルートの .env/.env.local を自動で読み込みます（無効化可）。
- DuckDB / SQLite をデータ格納に使用。paper_trading 実行時は paper_trading 用 DB に分離されます。
- OpenAI の呼び出し部は堅牢に実装（リトライ、バリデーション、部分失敗の保護）。
- ロギング、プロセス優先度、CPU affinity 等の OS 差分はユーティリティで吸収。

主な機能一覧
- Execution
  - 実取引（live）／ペーパートレード（paper_trading）モード対応
  - BrokerClientFactory によるブローカークライアント生成
  - OrderManager / RiskManager / Reconciler / ExecutionEngine による発注制御
- Monitoring
  - SystemMonitor（CPU/MEM/DISK、プロセス死活、データ鮮度）
  - TradeMonitor（滞留注文・約定異常など）
  - RiskMonitor（ドローダウン・ポジション数監視）
  - KillSwitch（条件に応じて data/kill.flag を生成して Execution を停止）
  - MonitoringEngine（各 Monitor を統合してポーリング、アラート連携）
  - monitoring.db（SQLite）へのログ保存（system_status, trade_logs, positions, risk_logs, dashboard）
- Portfolio
  - 候補選定、等金額／スコア加重、リスクベース配分、単元丸め、セクター制約、レジーム乗数
- Research
  - DuckDB 上でのファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC 計算、統計サマリー
- AI
  - news_nlp: ニュース記事を OpenAI で解析し ai_scores を作成
  - regime_detector: ma200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ツール
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

前提 / 必要パッケージ
- Python 3.10+
- 主要依存（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml 検証時に必要）
実際の依存はプロジェクトの requirements.txt や pyproject.toml を参照してください。

セットアップ手順
----------------
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows は .venv\Scripts\activate

2. パッケージインストール
   - pip install -r requirements.txt
   （requirements.txt が無い場合は上記の主要依存を個別に pip install してください）

3. .env の作成（推奨）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに .env を作成してください。
   - 自動ロード: デフォルトで .env/.env.local をプロジェクトルートから読み込みます。
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. 設定の検証
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合:
     - python -m kabusys.validate_config --strict

代表的な環境変数（.env に含める主なキー）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- オプション／推奨
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - DUCKDB_PATH — デフォルト data/kabusys.duckdb
  - SQLITE_PATH — 監視用 DB（本番）デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — ペーパー用 SQLite（paper_trading モード）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR
  - LOG_DIR — ログ保存先（デフォルト logs/）
  - OPENAI_API_KEY — news_nlp / regime_detector が必要な場合
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番時のアラート通知用

使い方（主要コマンド）
--------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話で生成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit 1）扱いになります。

- ExecutionEngine を起動（本番 or paper_trading）
  - デフォルト（KABUSYS_ENV に応じて動作）
    - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録して本番 DB と分離します。
    - 実行中は data/execution.pid（デフォルト）に PID を書きます。
    - data/stop_requested.flag を作成すると起動済みの run_execution は停止を受け付けます。
    - Kill Switch は data/kill.flag を書き込み ExecutionEngine に停止を促します。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 仕様:
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。
    - data/stop_requested.flag を検知するとループを終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD（レポート期間）
    - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）
  - 主要指標: 稼働率、注文成功率、送信率、P95 レイテンシ など。閾値に基づき PASS/FAIL を判定。

ログ・データ
------------
- ログ:
  - デフォルト logs/<app_name>.log に日次ローテーションで出力（30日保持）。
  - 標準出力にもログを出力（cron 等での扱いを想定して stdout を使用）。
  - LOG_DIR および LOG_LEVEL は環境変数で上書き可。

- データディレクトリ（defaults）
  - data/kabusys.duckdb  — DuckDB（分析用）
  - data/monitoring.db   — 監視用 SQLite（system_status, trade_logs, ...）
  - data/paper_trading.db — ペーパートレード用 SQLite（paper_trading モード）
  - data/kill.flag       — Kill Switch フラグ（監視側が書き込み、Execution 側が検出）
  - data/stop_requested.flag — 起動スクリプトの停止フラグ
  - data/execution.pid   — ExecutionEngine の PID（実行時書き込み）

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py                — 設定読み込み・Settings クラス（.env 自動ロード含む）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）による ai_scores 書き込み
  - regime_detector.py     — 市場レジーム判定（ma200 + LLM）
- monitoring/
  - monitoring_db.py       — SQLite テーブル定義・永続化レイヤ
  - system_monitor.py      — CPU/MEM/DISK・プロセス・データ鮮度監視
  - trade_monitor.py       — （滞留注文等の監視）※詳細はコード参照
  - risk_monitor.py        — ドローダウン／ポジション数監視
  - kill_switch.py         — kill.flag の作成・管理
  - monitoring_engine.py   — 各 Monitor の統合ポーリング
  - alert_manager.py       — （通知管理）※詳細はコード参照
- execution/
  - execution_engine.py    — 実行エンジン本体（セッション管理）
  - order_manager.py       — 注文管理
  - order_repository.py    — 発注履歴格納
  - broker_factory.py      — BrokerClient の生成
  - reconciler.py, risk_manager.py ...
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数決定・スケーリング・単元丸め
  - risk_adjustment.py     — セクター上限・レジーム乗数
- research/
  - factor_research.py     — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- utils/
  - logging_setup.py       — 一貫したログ設定ユーティリティ
  - process_priority.py    — プロセス優先度・CPU affinity 設定ユーティリティ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

運用上の注意
-------------
- KABUSYS_ENV=live の場合は本番動作となり、外部ブローカーへ発注が行われます。設定（API キー、LINE 通知等）を慎重に確認してください。
- validate_config のチェックや config_setup による .env 作成を必ず実行し、KILL_FLAG_CLEAR_ON_START 等の本番向けフラグに注意してください。
- OpenAI を利用する機能（news_nlp / regime_detector）は API キーが必要です。呼び出しは料金・レート制限に注意してください。
- monitoring と execution の DB は設計上分離されています（paper_trading 用 DB も別ファイル）。運用時にパス設定を間違えないよう注意してください。
- ログディレクトリ／データディレクトリの書き込み権限を確認してください。

開発者向けメモ
---------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行います。特殊な配置の場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動管理してください。
- DuckDB クエリは大きなデータセットを想定しています。クエリチューニングやインデックスは必要に応じて実施してください。
- OpenAI 呼び出し部分はテストしやすいよう内部呼び出し関数を分離してあり、unit test でモック可能です（例: kabusys.ai.news_nlp._call_openai_api をパッチ）。
- DB マイグレーションは monitoring_db.init_monitoring_db 内に軽微な ALTER ロジックを含んでいます。大きなスキーマ変更は migration スクリプトで管理することを推奨します。

お問い合わせ / 貢献
------------------
バグ報告・改善提案は issue を作成してください。Pull Request は歓迎します。コードの意図やドキュメントに関して質問があればリポジトリ内の doc/ またはソースコードの docstring を参照してください。

以上。