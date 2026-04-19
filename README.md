KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / モニタリングを目的とした Python コードベースです。本リポジトリは以下の役割を持つ主要コンポーネントを含みます。

- ExecutionEngine：発注処理・注文管理・リスク管理（本番 / ペーパートレード切替対応）
- Monitoring：システム稼働状況・注文状況・リスクの定期チェックとアラート / Kill Switch
- Research：DuckDB を使ったファクター計算・特徴量解析
- AI モジュール：OpenAI API を使ったニュースセンチメント / レジーム判定
- Tools：ペーパートレード検証レポート生成などのユーティリティ
- 設定管理：.env の対話的作成（config_setup）および事前検証（validate_config）

主な特徴
--------
- 環境切替（development / paper_trading / live）に対応。KABUSYS_ENV で制御。
- paper_trading モードでは MockBroker を使用し、本番 DB と分離された paper_trading 用 SQLite を利用。
- DuckDB を分析用 DB として使用（デフォルト: data/kabusys.duckdb）。
- 監視機能（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch により重大リスクで自動停止可能。
- OpenAI を用いたニュースセンチメントスコアリング（ai.news_nlp）および市場レジーム判定（ai.regime_detector）。
- ログは stdout と日次ローテートファイル（logs/<app_name>.log）に出力（kabusys.utils.logging_setup）。
- 環境変数 .env の自動読み込み（プロジェクトルートが検出できる場合）と対話式ウィザードでの作成支援。

セットアップ手順
----------------
1. リポジトリをクローン / 展開
   - プロジェクトルートに移動してください（pyproject.toml / .git を基準に自動検出されます）。

2. Python 環境の準備
   - Python 3.9+ を推奨。
   - 仮想環境を作成して有効化してください。
     例:
       python -m venv .venv
       source .venv/bin/activate  # Linux/macOS
       .venv\Scripts\activate     # Windows

3. 依存関係をインストール
   - 必要ライブラリ（代表例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config/*.yaml の内容検証を行う場合）
   - requirements.txt がない場合は手動でインストール:
       pip install duckdb psutil openai pyyaml

4. .env の作成
   - 対話式ウィザードを使って .env を生成できます:
       python -m kabusys.config_setup
   - 生成後、設定を検証:
       python -m kabusys.validate_config
     --strict を付けると警告も失敗扱いになります。

5. データディレクトリの準備
   - デフォルトの DB / PID / フラグファイルは data/ 配下に置かれます。実行時に自動作成されることもありますが、手動で作成しておくと安全です。
     - デフォルト DuckDB: data/kabusys.duckdb
     - デフォルト SQLite (monitoring): data/monitoring.db
     - ペーパートレード SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading）
     - PID / kill / stop フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

主な環境変数（代表）
--------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB (SQLite) のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）。デフォルト: instant
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）デフォルト: INFO
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒）。run_monitoring はこの環境変数で上書き可能（デフォルト 60）

基本的な使い方
--------------
1. .env の作成・検証
   - 対話式:
       python -m kabusys.config_setup
   - 検証:
       python -m kabusys.validate_config
       python -m kabusys.validate_config --strict

2. ExecutionEngine を起動（本番 / ペーパートレード切替は KABUSYS_ENV）
   - 実行:
       python -m kabusys.run_execution
   - ペーパートレード例:
       KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     ペーパートレード時は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。

3. Monitoring を起動
   - 実行:
       python -m kabusys.run_monitoring
   - ポーリング間隔を変更する場合:
       MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視は .env の設定にかかわらず monitoring は本番 sqlite_path を使用します（単一の監視 DB に記録）。

4. Kill Switch / stop フラグ
   - KillSwitch は一定条件（ドローダウンやポジション上限など）で data/kill.flag を作成し、ExecutionEngine に停止信号を送ります。
   - 監視ループや実行エンジンを外部で停止するためのファイル:
     - data/stop_requested.flag: run_monitoring/run_execution 起動ループが存在チェックしている停止フラグ
     - data/kill.flag: KillSwitch が書き込む停止フラグ
     - data/execution.pid: ExecutionEngine が PID を書き込むファイル

5. Paper Trading 検証レポート
   - SQLite（paper_trading）から集計して検証レポートを出力します:
       python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスは --db で指定可能（または PAPER_TRADING_SQLITE_PATH 環境変数を使用）。

6. AI モジュールの利用
   - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数で指定）。
   - ニューススコアリング:
       from kabusys.ai.news_nlp import score_news
       score_news(duckdb_conn, target_date, api_key=<your_key>)
   - レジームスコア:
       from kabusys.ai.regime_detector import score_regime
       score_regime(duckdb_conn, target_date, api_key=<your_key>)

ディレクトリ構成（主なファイル・モジュール）
--------------------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / .env の読み込み・Settings 定義
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py             — ニュースを LLM でスコアリングして ai_scores に書き込む処理
  - regime_detector.py      — ETF MA とニュースを組み合わせて市場レジーム判定
- monitoring/
  - monitoring_db.py        — SQLite のスキーマ初期化・簡易 DB ラッパ
  - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py        — （注文ログ監視: ファイルで定義）※詳細はコード参照
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - kill_switch.py          — Kill Switch 実装
  - alert_manager.py        — （アラート送信: LINE 等）※詳細はコード参照
- execution/
  - execution_engine.py     — ExecutionEngine 実装（セッション管理）
  - order_manager.py
  - order_repository.py
  - risk_manager.py
  - reconciler.py
  - broker_factory.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py  — 将来リターン・IC 等の統計解析
- monitoring/ (上記)
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py        — ログ設定ユーティリティ
  - process_priority.py     — プロセス優先度・CPU affinity ユーティリティ

運用上の注意
------------
- 本番運用（KABUSYS_ENV=live）の際は環境変数・シークレット（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / OPENAI_API_KEY 等）を適切に管理してください。.env を絶対にリポジトリにコミットしないでください。
- validate_config.py を用いて設定やパスの事前チェックを行ってください。--strict オプションで警告も失敗扱いにできます。
- Monitoring と Execution の両方を稼働させる場合、監視は本番 sqlite_path を参照して実行プロセス等を監視します。ペーパートレードは Execution 側で専用 DB に分離されます。
- OpenAI API を使う箇所は外部 API 依存のため、レートリミットや一時的障害に対してリトライやフェイルセーフの実装がありますが、API コストやレート制限には注意してください。
- ログはデフォルトで logs/ に出力されます。ログディレクトリ作成に失敗した場合はコンソールのみになります。

トラブルシューティング（簡易）
------------------------------
- .env を読み込まない / 別の .env を使いたい:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。
  - config_setup の --env-file オプションで別ファイルを指定できます。

- monitoring が停止しない / 停止フラグを使いたい:
  - data/stop_requested.flag を作成すると run_monitoring と run_execution のループが停止を検知します（手動停止用）。
  - KillSwitch が作成する data/kill.flag は ExecutionEngine 停止のトリガです。必要に応じて clear() を呼ぶかファイルを削除してください。

追加情報 / 貢献
----------------
- コード内に設計ノート（PortfolioConstruction.md や StrategyModel.md 参照とある箇所）や TODO コメントがあります。研究・運用要件に応じて拡張してください。
- 新しい機能や修正を加える場合はユニットテストや手元での検証（validate_config / paper_verification_report 等）を活用してください。

以上が基本的な README の内容です。より具体的な実行手順や運用手順（systemd/cron でのデーモン化、コンテナ化、監視アラート設定等）が必要であれば、使用環境に合わせた運用ドキュメントを別途作成できます。必要な箇所を教えてください。