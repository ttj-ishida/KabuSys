KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買・リサーチ基盤（KabuSys）の一部モジュール群を含みます。  
主に以下の機能を提供します。

- Execution Engine（発注エンジン）とペーパートレード切替
- 監視（Monitoring）コンポーネント（システム状況、注文ログ、リスク監視、Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ／ファクター計算（モメンタム、ボラティリティ、バリュー等）
- AI ベースのニュースセンチメント（OpenAI を利用したニュース NLP）と市場レジーム判定
- 設定ウィザード・検証ツール、運用支援ツール（Paper Trading 検証レポート等）
- ログ設定・プロセス優先度設定などのユーティリティ

主な特徴
-------
- 環境変数ベースの設定（.env ファイル生成ウィザードあり）
- KABUSYS_ENV によるモード切替（development / paper_trading / live）
  - paper_trading モードでは MockBrokerClient を使い、専用の SQLite（data/paper_trading.db）へ記録
- 監視は常に監視用の production sqlite_path を使用（環境に依らない）
- OpenAI（gpt-4o-mini想定）を使ったニュースセンチメントおよびレジーム判定の実装
- DuckDB を分析用データベースとして利用（prices_daily / raw_financials 等のテーブルを想定）
- フェイルセーフ設計（API エラー時はフォールバック、部分失敗時の DB 保護など）

セットアップ
-----------

1. Python 環境（3.10+ を想定）を準備します。venv 推奨。

2. 必要な Python パッケージをインストールします（例）:

   pip install duckdb psutil openai

   追加で便利なパッケージ:
   - PyYAML（config/*.yaml の検証をしたい場合）
     pip install pyyaml

   ※ パッケージ管理はプロジェクトの requirements.txt / pyproject.toml に合わせて行ってください。

3. プロジェクトルートに data/ と logs/ ディレクトリを作成（多くの処理で自動作成されますが、明示的に作ると確実です）:

   mkdir -p data logs

4. .env を作成します（対話式ウィザード推奨）:

   python -m kabusys.config_setup

   ウィザードは J-Quants トークンや kabuステーション API パスワードなどの必須項目を促します。
   生成後、設定を検証します:

   python -m kabusys.validate_config

   --strict オプションをつけると警告も失敗扱いになります。

重要な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading モード時）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant/partial/never/reject）

使い方（主要スクリプト）
-----------------------

- 環境設定ウィザード（.env の作成／更新）
  python -m kabusys.config_setup

- 設定検証（.env と config/*.yaml の整合チェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution Engine（発注エンジン）を起動
  python -m kabusys.run_execution

  挙動のポイント:
  - プロセス優先度を "high" に設定してから起動します（utils.process_priority）。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB を使います（data/paper_trading.db）。
  - 起動時に data/stop_requested.flag（プロジェクトルート直下 data 側）を検出すると起動を中止します。
  - 実行中は data/stop_requested.flag を書き込むことでエンジン停止をリクエストできます（Kill Switch とは別の停止フラグ扱い）。

- Monitoring（監視ループ）を起動
  python -m kabusys.run_monitoring

  挙動のポイント:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は常に settings.sqlite_path（監視用 DB）に接続します（環境に関係なく本番 sqlite_path を使用）。
  - data/stop_requested.flag を検出するとループを終了します。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で DB ファイルパスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も利用可能。

- AI 系（プログラム API 呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  これらは DuckDB 接続を受け取り、ai_scores / market_regime テーブルなどへ書き込みます。OpenAI キーを引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。

監視・Kill Switch の動作概要
---------------------------
- MonitoringEngine は SystemMonitor、TradeMonitor、RiskMonitor を定期実行し、AlertManager / KillSwitch を経由してアラートや停止シグナルを出します。
- KillSwitch はリスク条件（ドローダウン超過、ポジション上限超過など）が満たされた場合に data/kill.flag を書き込みます。
- ExecutionEngine 側では起動時やループ中に kill.flag / stop flag を確認し、安全に停止する仕組みがあります。

ディレクトリ構成（主要ファイル・モジュール）
---------------------------------------
以下は src/kabusys 以下の主なファイル・ディレクトリの一覧（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数/Settings 管理、.env 自動読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - __init__.py
    - logging_setup.py       — ログ設定ユーティリティ（Stream + 日次ローテーション）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 用永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - monitoring_engine.py   — 監視エンジン（各 Monitor の統合）
    - system_monitor.py      — システム状態・データ鮮度チェック
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - (TradeMonitor / AlertManager 等の想定コンポーネントは同ディレクトリに存在)
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（起動・セッション管理）
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
    - factor_research.py     — Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー等
  - ai/
    - news_nlp.py            — ニュース記事のセンチメントスコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント合成）

注意事項 / 運用メモ
------------------
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも明記）。
- 本番モード（KABUSYS_ENV=live）では設定ミスが致命的になる可能性があるため、validate_config で入念にチェックしてください。
- OpenAI の呼び出しは料金・レート制限があるため、テスト時はモックするか API キーの取り扱いに注意してください。
- DuckDB / SQLite のファイルパスは .env で設定できます。デフォルトは data/kabusys.duckdb と data/monitoring.db です。
- MONITOR_POLL_INTERVAL が 0 や負の値に設定されていると無効として 60 秒にフォールバックします。

貢献・拡張の方向性（一例）
-------------------------
- stocks マスタを導入して銘柄ごとの lot_size を管理
- ExecutionEngine のセッション管理強化（フォールトトレランス、再試行ポリシーの拡張）
- AI モジュールの多言語対応 / プロンプト最適化
- モニタリング・アラートのチャネル拡張（Slack / PagerDuty 等）
- DuckDB に対する ETL パイプラインの自動化（CSV / S3 取り込み等）

ライセンス
----------
リポジトリにライセンス情報が含まれていない場合は、プロジェクト方針に従って適切なライセンスを追加してください。

---

必要なら、README に含めるコマンド例や .env のテンプレート（.env.example）を具体的に追加できます。どの程度サンプルを含めるか指示してください。