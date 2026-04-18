KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向け自動売買システム「KabuSys」のコアライブラリ群です。  
本 README ではプロジェクト概要、主要機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめています。

概要
----
KabuSys は以下の機能を持つモジュール群で構成されています。

- データ処理（DuckDB を用いた時系列・財務データ集計）
- ファクター計算・特徴量生成（モメンタム、ボラティリティ、バリュー等）
- ポートフォリオ構築（候補選定・重み算出・株数決定・単元調整）
- リスク調整（セクターキャップ、レジーム乗数）
- Execution エンジン（ブローカークライアントによる発注管理、リスクチェック）
- Monitoring（システム稼働監視、トレード監視、Kill Switch）
- AI 補助（OpenAI を用いたニュースセンチメント、レジーム判定）
- 各種ツール（ペーパートレード検証レポート生成など）
- 環境設定ウィザード / 設定検証 CLI

主な特徴（機能一覧）
------------------
- portfolio:
  - 銘柄候補選定（select_candidates）
  - 重み算出（等配分 / スコア加重）
  - ポジションサイズ計算（risk_based / equal / score）
  - セクター集中制限・レジーム乗数
- research:
  - モメンタム / ボラティリティ / バリューの DuckDB ベースファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- ai:
  - ニュースを LLM（OpenAI）で評価して銘柄ごとのスコアを ai_scores に書き込む
  - マクロニュース + ETF ma200 による市場レジーム判定
- monitoring:
  - SystemMonitor: CPU/メモリ/ディスク/データ鮮度/プロセス生存確認
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン等の検出
  - KillSwitch: 条件により ExecutionEngine を停止させるフラグファイル生成
  - MonitoringEngine: 各 Monitor を束ねて定期ポーリング・アラート発報
- utils:
  - ロギング設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
- CLI / ツール:
  - config_setup: .env を対話式に生成・更新
  - validate_config: .env / config/*.yaml の事前検証
  - tools.paper_verification_report: ペーパートレード検証レポート生成

セットアップ手順
----------------

前提
- Python 3.9+（ソースが型アノテーション等を使用）
- システムに DuckDB / SQLite3 を使えること（Python パッケージで済みます）
- OpenAI を使う機能を利用する場合は API キーが必要

1) 仮想環境の作成（推奨）
- venv 例:
  python -m venv .venv
  source .venv/bin/activate  # Linux / macOS
  .venv\Scripts\activate     # Windows

2) 依存パッケージのインストール（例）
- 必要な主なパッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML を検証したい場合）
- インストール例:
  pip install duckdb psutil openai PyYAML

（注）requirements.txt があればそれを使ってください。上は最低限の例です。

3) .env の作成
- 対話式ウィザードを使う（推奨）:
  python -m kabusys.config_setup
  → プロンプトに従って .env を作成します（.env は絶対にコミットしないでください）

- もしくは手動で .env を作成し、主要な環境変数を設定します（下記を参照）。

4) 設定の検証
- 生成した .env や config/*.yaml を起動前に検証できます:
  python -m kabusys.validate_config
- 警告も FAIL 扱いしたい場合:
  python -m kabusys.validate_config --strict

5) データディレクトリ等の準備
- デフォルトでは以下のパスが使われます（必要に応じて .env で上書き）:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - ログ: logs/
  - Kill flag / stop flag / pid ファイル: data/*.flag / data/*.pid
- 実行時に自動生成される箇所が多いですが、適切なパーミッションでディレクトリを作成してください。

主要な環境変数（抜粋）
---------------------
以下は主な環境変数と説明（.env に設定する想定）:

- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite (monitoring) ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant / partial / never / reject）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、run_monitoring 用）
  - run_monitoring は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60）

使い方（実行例）
----------------

1) 環境設定ウィザード
- .env を対話的に作成:
  python -m kabusys.config_setup

2) 設定検証
- 生成後に検証:
  python -m kabusys.validate_config
- --strict を付けると警告も失敗として扱う:
  python -m kabusys.validate_config --strict

3) 実行用スクリプト
- 実際の Execution エンジンを起動（スレッドで実行）:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading.db に記録します（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします
  - 実行中は data/execution.pid が作成されます
  - 停止は stop_flag や kill.flag により制御（stop_requested.flag / data/kill.flag）

- 監視プロセスを起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能（デフォルト 60）
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します（監視 DB は本番 DB と同じパスを参照）
  - data/stop_requested.flag を検出すると監視ループを終了します

4) ツール
- ペーパートレード検証レポートを生成:
  python -m kabusys.tools.paper_verification_report
  - --from / --to で期間指定（YYYY-MM-DD）
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

ログ・ファイル・Kill Switch
--------------------------
- ログ: デフォルト logs/<app_name>.log に日次ローテーションで保存（30日保持）
- Kill Switch:
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止指示を与える仕組みです
  - Run スクリプト・Monitoring から評価・書き込みされます
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアしますが、本番では 0 を推奨

注意点 / 運用メモ
-----------------
- run_monitoring は KABUSYS_ENV に関係なく本番の sqlite_path を参照します（監視は本番 DB を見るため）
- run_execution は paper_trading モードなら paper_trading 用の DB を使い、本番 DB と完全に分離します
- OpenAI を使う処理は API 呼び出し失敗に寛容なフェイルセーフ設計（失敗時はスコア 0.0 やスキップ）
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml がある場所）を起点に .env / .env.local を自動読み込みします
  - OS 環境変数が優先されます
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

ディレクトリ構成
----------------
主要なファイル／パッケージ（src/kabusys 以下）:

- __init__.py
  - パッケージ定義（__version__ 等）

- config.py
  - 環境変数/.env の読み込みと Settings クラス

- config_setup.py
  - .env を対話式で作成するウィザード

- validate_config.py
  - 起動前に .env と config/*.yaml を検証する CLI

- run_execution.py
  - ExecutionEngine の起動スクリプト（実取引 / ペーパートレード対応）

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- utils/
  - logging_setup.py — 統一ログ設定
  - process_priority.py — 優先度 / CPU affinity 設定

- portfolio/
  - portfolio_builder.py — 候補選定 / 重み算出
  - position_sizing.py — 株数計算・単元丸め・資金スケーリング
  - risk_adjustment.py — セクター制限・レジーム乗数

- research/
  - factor_research.py — momentum / volatility / value 等
  - feature_exploration.py — 将来リターン・IC・統計サマリ

- monitoring/
  - monitoring_db.py — SQLite 永続化レイヤ（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py — システム稼働・データ鮮度監視
  - trade_monitor.py — （注文関連監視）※実装ファイルあり
  - risk_monitor.py — ドローダウン / ポジション数監視
  - kill_switch.py — フラグ書込による停止シグナル
  - monitoring_engine.py — 各 Monitor の統合実行とアラート発報

- ai/
  - news_nlp.py — ニュースの LLM センチメント評価と ai_scores への書き込み
  - regime_detector.py — ETF MA + マクロニュースでレジーム判定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成ツール

補足（開発向け）
----------------
- DuckDB 接続を直接渡して計算を行う設計（研究/分析コードは副作用なし）
- ロギングは各起動スクリプトから setup_logging(app_name=...) を呼んで統一してください
- ProcessPriority 設定は起動直後に行ってシステム上の安定動作を確保します

ライセンス・貢献
----------------
- 本プロジェクトのライセンス／コントリビューション規約はリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

お問い合わせ
-----------
実行方法や設定で不明点があれば、ソースのドキュメントコメントを参照するか、リポジトリ内の issue に問い合わせてください。

以上が KabuSys の概要と基本的な使い方です。安全に注意して設定・起動してください。