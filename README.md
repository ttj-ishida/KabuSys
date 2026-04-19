KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視ツール群を含む Python パッケージです。
このリポジトリには、発注エンジン起動スクリプト、監視デーモン、ペーパートレード検証用ツール、
ファクター計算やニュース NLP を用いた AI モジュールなどが含まれます。

主な設計方針
- 本番とペーパートレードを分離（KABUSYS_ENV による振る舞い切替）
- DuckDB を分析用、SQLite を監視・発注ログ用に利用
- 外部 API 呼び出し（OpenAI 等）は明示的な API キーで保護
- .env を使った設定管理と対話式ウィザード / 検証 CLI を提供

機能一覧
--------
- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading のときは MockBroker を用い、data/paper_trading.db を使用
- 監視デーモン
  - run_monitoring.py: SystemMonitor のポーリングループを実行（MONITOR_POLL_INTERVAL で間隔変更可）
  - MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager 等を含む
- 設定管理 / 検証
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI（--strict あり）
  - config.py: 自動 .env ロード（.env / .env.local）と Settings 抽象
- 研究 / ファクター計算
  - research.factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB ベース）
  - research.feature_exploration: 将来リターン算出、IC 計算、統計サマリ等
- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定・重み計算
  - portfolio.position_sizing: 株数決定・aggregate cap と単元丸め
  - portfolio.risk_adjustment: セクターキャップ、レジーム乗数
- AI（OpenAI）
  - ai.news_nlp: ニュースを LLM でスコアリングして ai_scores に格納
  - ai.regime_detector: MA200 とマクロニュースで市場レジーム判定
- ユーティリティ
  - utils.logging_setup: ログ設定（stdout + 日次ローテート）
  - utils.process_priority: プロセス優先度 / CPU affinity の簡易ラッパー
- ツール
  - tools.paper_verification_report: ペーパートレード結果の検証レポート生成

前提・依存関係
---------------
- Python 3.10 以上（型アノテーションに | を使用しているため）
- 主要依存ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- 必要であれば requirements.txt を用意のうえ pip install -r requirements.txt を実行してください。
  （本リポジトリに requirements.txt がない場合は上記パッケージを個別に pip install してください）

環境変数（主要）
----------------
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
  - paper_trading: 発注はモック。専用 DB（PAPER_TRADING_SQLITE_PATH）を使用
  - live: 本番動作（API キーなどの設定に注意）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（開発用）

設定ファイル読み込みの注意
- config.py は自動でプロジェクトルート（.git または pyproject.toml を基準）を探し、
  .env を自動で読み込みます（.env.local は .env を上書き）。自動ロードを無効にするには
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順
---------------
1. リポジトリをクローン・作業ディレクトリへ移動
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)
3. 依存関係をインストール
   - pip install duckdb psutil openai pyyaml
   - または requirements.txt がある場合: pip install -r requirements.txt
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 生成後、設定を検証: python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱い（exit 1）
5. 必要ディレクトリ（data/ logs/）が自動作成されますが、権限等に注意してください。

使い方（起動例）
----------------
- ExecutionEngine 起動（通常）:
  - python -m kabusys.run_execution
  - 注意: 実行中は data/stop_requested.flag を監視しており、存在すれば停止します。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 DB を使用し、MockBroker を利用

- Monitoring 起動（ポーリング）:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
  - 監視は KABUSYS_ENV にかかわらず sqlite_path に接続します（監視 DB は本番 path を参照）

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI/リサーチモジュール（プログラムから呼び出す例）
  - from kabusys.ai import score_news
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - OpenAI を使う機能を呼ぶ場合は OPENAI_API_KEY を設定してください。

停止 / Kill Switch
------------------
- 実行エンジン停止用フラグ: data/kill.flag（KillSwitch により書き込みされる）
- run_execution/run_monitoring は data/stop_requested.flag を参照し、存在すると停止します
- KillSwitch.clear() は kill.flag を削除するユーティリティ（起動時のクリーンアップ等）

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                     — 環境変数ロード & Settings
    config_setup.py               — .env 対話ウィザード
    validate_config.py            — 設定検証 CLI
    run_execution.py              — ExecutionEngine 起動スクリプト
    run_monitoring.py             — SystemMonitor ポーリング起動スクリプト

    utils/
      logging_setup.py            — ログ設定ユーティリティ
      process_priority.py         — プロセス優先度設定ユーティリティ

    monitoring/
      monitoring_db.py            — SQLite 用監視 DB 層
      system_monitor.py           — システム状態・データ鮮度監視
      risk_monitor.py             — ドローダウン / ポジション上限監視
      kill_switch.py              — kill.flag 管理
      monitoring_engine.py        — モニター統合エンジン
      (他: trade_monitor.py, alert_manager.py 等)

    execution/                     — 発注エンジン周り（BrokerFactory, ExecutionEngine 等）
      (order_manager, order_repository, reconciler, risk_manager など)

    portfolio/
      portfolio_builder.py         — 候補選定・重み計算
      position_sizing.py           — 株数算出・スケーリング
      risk_adjustment.py           — セクター制限・レジーム乗数

    research/
      factor_research.py          — ファクター計算（momentum / value / volatility）
      feature_exploration.py      — IC 計算・統計サマリ

    ai/
      news_nlp.py                 — ニュース NLP スコアリング（OpenAI）
      regime_detector.py          — 市場レジーム判定（MA200 + マクロ NLP）

    tools/
      paper_verification_report.py — ペーパートレード検証レポート

注意点 / 運用上のヒント
-----------------------
- 監視 DB（SQLite）と発注 DB（ペーパートレード用 SQLite）は分離して運用することを推奨します。
- 本番運用時は KABUSYS_ENV=live を指定し、LINE 等の通知設定を確認してください（validate_config が警告を出します）。
- OpenAI を使う機能は API 利用料が発生します。API キーは安全に管理してください。
- ログは logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR 環境変数で変更可。
- プロセス優先度設定は権限に依存します（set_process_priority が AccessDenied をハンドリングします）。

開発 / 貢献
------------
- コードの各モジュールはテストしやすさを意識して純粋関数と副作用分離を心がけています。
- 単体テスト・統合テストを追加する場合は、環境変数の自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- 変更を加える際は config/*.yaml のスキーマや DB マイグレーションに注意してください（monitoring_db.init_monitoring_db は簡易マイグレーションを行います）。

ライセンス
---------
プロジェクト固有のライセンス情報はリポジトリルートの LICENSE 等を参照してください（本 README には含めていません）。

---

不明点や追加で README に載せたい内容があれば教えてください。設定項目のサンプル .env テンプレートや運用チェックリストも作成できます。