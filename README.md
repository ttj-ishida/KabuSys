KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の軽量実装です。  
主な目的は以下のとおりです。

- 戦略 → シグナル → 発注までの ExecutionEngine（本番 / ペーパートレード対応）
- システム稼働・注文・リスク監視とアラート（Monitoring）
- ファクター計算・特徴量探索などの Research ツール
- ニュース系の NLP（OpenAI を用いたセンチメント集計）やレジーム判定
- ペーパートレード検証レポート生成ツール

本リポジトリはライブラリとしても利用でき、モジュール単位で機能を呼び出せます。

主な機能
--------
- Execution
  - ExecutionEngine による注文発行（実際のブローカ／モック切り替え）
  - リスク管理（最大ポジション比率等）
  - 発注履歴の記録（SQLite / DuckDB）
- Monitoring
  - システム（CPU/メモリ/ディスク）・プロセス監視
  - 注文の滞留チェック、約定価格の異常検出
  - ドローダウン / ポジション上限の監視 → Kill Switch（フラグファイル）で Execution 停止
  - 監視ログ永続化（SQLite）
- Research
  - momentum / volatility / value 等のファクター計算（DuckDB 上で SQL 実行）
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- AI（OpenAI）
  - ニュース記事を集約して銘柄別センチメントを取得（ai_scores テーブルに保存）
  - マクロニュース＋ETF MA を組み合わせた市場レジーム判定（market_regime へ保存）
- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成スクリプト

前提 / 必要ライブラリ
--------------------
主な外部依存（代表例）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能利用時)
- PyYAML（validate_config が YAML のパース検証を行う場合に使用。未インストール時は警告）
実行環境により追加パッケージが必要になる場合があります（例: Windows の優先度設定等）。

セットアップ手順
--------------
1. リポジトリをクローンし、仮想環境を作成・有効化する:
   - python -m venv .venv
   - source .venv/bin/activate（Windows では .venv\Scripts\activate）

2. 依存関係をインストールする（プロジェクトに requirements.txt があればそれを利用）:
   - pip install duckdb psutil openai
   - （開発用）pip install PyYAML

   ※ 実際のパッケージリストはプロジェクト外の依存管理ファイルに合わせてください。

3. 初期設定ファイル (.env) を作成する（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
   - ウィザードは .env を生成・更新します。生成後は設定を必ず確認してください。

4. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリ作成（必要に応じて）:
   - デフォルトの DB などは data/ 以下に作成されます。必要であれば事前に作成してください。
   - 例: mkdir -p data

設定（環境変数）
----------------
自動ロード:
- プロジェクトルートに .git または pyproject.toml が存在する場合、起動時に .env と .env.local を自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化するには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、Execution は専用の paper DB を使用（SQLITE パスは PAPER_TRADING_SQLITE_PATH）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db） — Monitoring は常に本番 sqlite_path を使用
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の mock フィルモード（instant | partial | never | reject）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 実行時に kill.flag を自動クリアするか（1 = 有効。production では 0 推奨）
- KILL_FLAG_PATH / PID_FILE_PATH: kill.flag / PID ファイルのパスカスタマイズ

重要なファイル（制御フラグ）
- data/kill.flag: Kill Switch による Execution 停止フラグ（存在すると実行停止が要求される）
- data/stop_requested.flag: run_monitoring / run_execution の起動ループを停止させるためのフラグ
- data/execution.pid: ExecutionEngine が書き込む PID ファイル（SystemMonitor が存在有無でプロセス生存判定）

使い方（主要コマンド）
--------------------
- 環境ウィザード（.env の生成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor の簡易スクリプト）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を環境変数で上書き可能（秒）
  - 監視は monitoring.db（Settings.sqlite_path）を使用（KABUSYS_ENV に依らず本番の sqlite_path）

- ExecutionEngine 起動（実際の発注処理／ペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
  - 実行中に data/stop_requested.flag を作成すると優雅に停止します

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを上書き可能（環境変数 PAPER_TRADING_SQLITE_PATH も使用可能）

- ライブラリ API（プログラムから利用）
  - 設定: from kabusys.config import settings
  - AI スコアリング: from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定: from kabusys.ai.regime_detector import score_regime
  - Research: from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  - Portfolio 計算: from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

実行上の注意
------------
- Monitoring と Execution は DB を同時にアクセスするため、ファイルパス設定を適切に行ってください。ペーパートレード実行時は paper 用 SQLite を使用して本番 DB と分離します。
- OpenAI を使う処理は API キーが必須です。API 呼び出しはリトライ・フェイルセーフ設計になっていますが、課金やレート制限に注意してください。
- SystemMonitor は pid ファイルを参照してプロセス生存を判断します。PID ファイルの整合性が重要です。
- .env は絶対にリポジトリにコミットしないでください（ウィザードにも注意書きあり）。

ディレクトリ構成（主要ファイル）
------------------------------
下記は src/kabusys 以下の主要ファイルと役割（抜粋）です。

- __init__.py
  - パッケージ初期化、__version__ 等

- config.py
  - Settings クラス: 環境変数の解決・バリデーション、自動 .env ロードロジック

- config_setup.py
  - 対話式 .env ウィザード（python -m kabusys.config_setup）

- validate_config.py
  - 起動前設定検証 CLI（python -m kabusys.validate_config）

- run_execution.py
  - ExecutionEngine 起動スクリプト（実行フローの組み立て、ペーパートレード分離）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔を制御）

- monitoring/
  - monitoring_db.py : SQLite テーブル初期化・読み書きユーティリティ（MonitoringDB）
  - system_monitor.py  : システム状態・データ鮮度チェック
  - trade_monitor.py   : 注文滞留・約定異常チェック
  - risk_monitor.py    : ドローダウン / ポジション上限の監視
  - kill_switch.py     : kill.flag の生成 / 監視用ユーティリティ
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - alert_manager.py   : （アラート管理、別実装想定）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, order_record.py など
  - 発注ロジック・ブローカー抽象化・リスク制御

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 銘柄選定・配分・ポジションサイズ計算・セクター制限

- research/
  - factor_research.py : momentum / value / volatility 等のファクター計算（DuckDB ベース）
  - feature_exploration.py : 将来リターン・IC・統計サマリー等

- ai/
  - news_nlp.py        : ニュース集合 → LLM センチメント、ai_scores 書き込み
  - regime_detector.py : ETF MA + マクロセンチメントでレジーム判定（market_regime 書き込み）

- tools/
  - paper_verification_report.py : ペーパートレード検証レポート生成スクリプト

開発者向けメモ
--------------
- DuckDB 接続を受け取って SQL と Python を組み合わせる設計が多く、テスト時は DuckDB のモックやテスト DB を使うと良いです。
- OpenAI 呼び出し部分はリトライやレスポンス検証を行っています。テストでは _call_openai_api をモックすることが設計上想定されています。
- 設定の自動ロードはプロジェクトルート検出（.git / pyproject.toml）に依存します。配布後に自動ロードが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

問い合わせ / 拡張
----------------
- README の内容はコードコメント・ドキュメントに基づいて作成しています。各モジュールの詳細実装や拡張（AlertManager の実装、ブローカープラグイン追加など）は該当モジュールを参照してください。

以上。必要であれば README にサンプル .env のテンプレートやよくあるトラブルシュート項目を追加しますか？