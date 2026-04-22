KabuSys — 日本株自動売買システム（README）
==================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行うためのコンポーネント群です。本リポジトリは
- 発注実行エンジン（ExecutionEngine）
- 監視/リスク管理（Monitoring）
- ポートフォリオ構築ユーティリティ（選定・配分・サイズ決定）
- リサーチ（ファクター計算・特徴量解析）
- AI 補助モジュール（ニュースセンチメント、レジーム判定）
- 運用補助ツール（.env ウィザード・設定検証・ペーパートレード検証レポート）
を含みます。モジュールは可能な限り副作用を抑え、テストしやすい純粋関数/明示的依存注入の設計を意識しています。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じた本番 / ペーパートレード分離（ペーパー時は MockBrokerClient を使用し data/paper_trading.db に記録）
  - リスク管理（RiskManager）、オーダー管理、リコンサイル等の組み立て
  - 停止フラグ（data/stop_requested.flag）検知による安全停止

- Monitoring（run_monitoring.py / monitoring/*）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限の監視
  - KillSwitch: 条件に応じた data/kill.flag の書き込みで Execution を強制停止
  - MonitoringEngine: ポーリングループ、Alert 発行連携（AlertManager 経由）

- ポートフォリオ構築（portfolio/*）
  - 候補選定、等分/スコア重み付け、セクター制約、レジーム乗数、ポジションサイズ計算（単元丸め、aggregate cap）

- リサーチ（research/*）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン、IC（スピアマン）計算、統計サマリー

- AI モジュール（ai/*）
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメント集計・ai_scores への書き込み
  - regime_detector: MA200 とマクロニュースの LLM センチメントを組み合わせた市場レジーム判定

- ツール
  - config_setup.py: .env の対話式ウィザードで初期設定を作成
  - validate_config.py: .env / config/*.yaml の検証 CLI
  - tools/paper_verification_report.py: ペーパートレードログから検証レポートを生成

動作要件（主な依存）
-------------------
- Python 3.9+
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能利用時）
- 開発で便利なパッケージ
  - PyYAML（config/*.yaml 検証に使用。未インストールでも動作は継続します）

セットアップ手順
----------------
1. リポジトリを取得
   - git clone ... でクローン

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - 必要に応じてその他パッケージを追加してください

4. 初期設定（.env）作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で .env を作成
   - 重要な環境変数（最低限必須）
     - JQUANTS_REFRESH_TOKEN（J-Quants）
     - KABU_API_PASSWORD（kabuステーション）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development / paper_trading / live）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. ディレクトリ作成（必要に応じて）
   - data/ や logs/ は自動作成されますが、権限等で失敗することがあるため確認してください

使い方（主要スクリプト例）
-------------------------

- 監視ループの起動（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）
  - 実行:
    - python -m kabusys.run_monitoring
  - 停止:
    - data/stop_requested.flag を作成するとループは検知して終了します

- 実行エンジンの起動（Execution）
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）を使用します
  - 実行:
    - python -m kabusys.run_execution
  - 強制停止:
    - monitoring の KillSwitch が条件を満たすと data/kill.flag を書き込み、Engine 側で検知して停止します
    - またデプロイ側で data/stop_requested.flag を作ると起動済みスレッドを安全に停止します

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数の代替）

環境変数（主なもの）
-------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパー発注時のフィルモード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリア、0=クリアしない、production は 0 推奨）

ログ
----
- ログは logs/<app_name>.log に日次ローテーションで出力されます（logs/ 以下、デフォルト30日保持）。
- ログはコンソール（stdout）にも出力されます。
- setup_logging により共通フォーマットで出力されます。

停止 / Kill Switch
------------------
- data/kill.flag: KillSwitch により作成されるファイル。ExecutionEngine に停止指示を送る。
- data/stop_requested.flag: 実行スクリプト（run_monitoring/run_execution）が監視している停止フラグ（開発用に外部で作成してプロセスに停止を促せます）。
- Settings.kill_flag_clear_on_start = 1 の場合、起動時に kill.flag を自動的にクリアします（production では危険なため推奨されません）。

開発者向け（内部 API）
--------------------
- ポートフォリオ関数群:
  - kabusys.portfolio.select_candidates / calc_equal_weights / calc_score_weights
  - kabusys.portfolio.calc_position_sizes
  - kabusys.portfolio.apply_sector_cap / calc_regime_multiplier
- リサーチ:
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
- AI:
  - kabusys.ai.score_news（DuckDB 接続と target_date を与えて実行）
  - kabusys.ai.regime_detector.score_regime

ディレクトリ構成（抜粋）
--------------------
（プロジェクトの src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — 監視ループ起動スクリプト
  - run_execution.py         — 実行エンジン起動スクリプト

  - ai/
    - news_nlp.py
    - regime_detector.py

  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (実装ファイルがある想定)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装ファイルがある想定)

  - execution/
    - execution_engine.py (実装)
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py
    - process_priority.py

補足 / 運用上の注意
------------------
- 本番（KABUSYS_ENV=live）では kill.flag の自動クリアや .env の不注意な扱いを避けてください。
- OpenAI を使用するモジュールは API 利用料金・レート制限の影響を受けます。API エラー・制限は再試行・フォールバック設計が組まれていますが、運用時はキーやコストに注意してください。
- DuckDB / SQLite のファイルはバックアップ・排他制御に留意してください（複数プロセスからの同時書き込みは想定外の競合を招く場合があります）。

ライセンス / 貢献
----------------
- 本 README に記載されている運用・説明はリポジトリ内のコードを基にまとめたものです。貢献・修正については Pull Request を歓迎します。

以上。セットアップや実行で不明点があれば実行環境やエラーメッセージを添えて質問してください。