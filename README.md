KabuSys — 日本株自動売買システム
=================================

この README は、リポジトリ内のコード（src/kabusys 以下）に基づいて作成したプロジェクト概要・セットアップ・運用手順ドキュメントです。開発者や運用担当者向けに、主要な機能・起動方法・設定方法・ディレクトリ構成をまとめています。

前提
----
- Python 3.10 以上（型記法に | を使用しているため）。  
- 必要な Python パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証が必要な場合）
- SQLite（標準ライブラリ sqlite3 を使用）
- ネットワークアクセス（kabuステーション API / OpenAI 等を利用する場合）

pip での一例:
  pip install duckdb psutil openai pyyaml

重要: .env ファイルは秘密情報を含むため絶対に Git にコミットしないでください。

プロジェクト概要
---------------
KabuSys は日本株の自動売買（Execution）とその監視（Monitoring）、研究（Research）やポートフォリオ構築（Portfolio）、およびニュース NLP を用いた補助機能（AI）を備えたシステムです。

主な設計方針（抜粋）
- Execution と Monitoring を分離。監視は稼働状況やデータ鮮度、注文状態、リスクなどを定期チェックしてアラート／Kill Switch を発動します。
- Paper Trading モードは本番データベースと分離（専用 SQLite を使用）。
- DuckDB を分析用途（価格・財務・ニュース等）に使用。
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントやレジーム判定をサポート（API キー必須）。
- できるだけ外部副作用を小さくする（純粋関数群、フェイルセーフ等）。

主な機能一覧
---------------
- 実行関連
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - Broker クライアントのファクトリによる本番 / Mock ブローカー切替（KABUSYS_ENV=paper_trading）
  - 注文管理・リスク管理・Reconciler 等の実装（execution/ 以下）
- 監視関連
  - SystemMonitor: CPU/メモリ/Disk の監視、Execution プロセス死活・データ鮮度チェック
  - TradeMonitor: 注文の滞留・約定異常などの検出（trade_monitor.py）
  - RiskMonitor: ドローダウン・ポジション上限監視（risk_monitor.py）
  - KillSwitch: 条件を満たしたら data/kill.flag を書き Execution を停止
  - MonitoringEngine / run_monitoring.py: ポーリングループで上記を回す
  - MonitoringDB: SQLite を用いた監視ログ永続化（monitoring_db.py）
- ポートフォリオ構築（portfolio/）
  - 候補選定、等配分・スコア配分、ポジションサイズ計算、セクター制限、レジーム乗数
- 研究（research/）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 特徴量探索（将来リターン計算・IC 計算・統計サマリ）
- AI（ai/）
  - ニュース NLP によるセンチメントスコア生成（news_nlp.score_news）
  - レジーム判定（regime_detector.score_regime）
- ユーティリティ
  - 環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ログ設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度設定（utils/process_priority.py）
- ツール
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

設定（環境変数 / .env）
-----------------------
主に .env（プロジェクトルート）で設定します。自動ロード機能が有効（デフォルト）で、.env と .env.local を読み込みます。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBroker を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（paper_trading 時に使用）
- LOG_LEVEL, LOG_DIR — ログレベル / ログ出力ディレクトリ
- MONITOR_POLL_INTERVAL — monitoring ポーリング間隔（秒、run_monitoring で使用。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1。production は 0 推奨）

.env の作成・更新
- 対話式ウィザード:
  python -m kabusys.config_setup
  → 指示に従って .env を生成できます。

設定検証
- .env や config/*.yaml の事前検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  （警告も FAIL 扱い）

セットアップ手順
----------------
1. リポジトリクローン / 仮想環境作成
   git clone ... && cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージのインストール
   pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合はそれに従ってください）

3. .env の作成
   python -m kabusys.config_setup
   （または手動で .env を作成する。.env.example を参考にしてください）

4. 設定検証
   python -m kabusys.validate_config
   --strict オプションで厳密検証

5. データディレクトリ / ログディレクトリの準備は通常不要（起動時に自動作成されます）。ただしパス権限に注意。

使い方 / 起動コマンド
--------------------

- ExecutionEngine の起動（本番 / paper_trading に応じて内部でブローカーが切替）
  python -m kabusys.run_execution

  特記事項:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動前に data/stop_requested.flag があると起動せず終了します（stop フラグ）。
  - Execution 側の PID ファイルは data/execution.pid（設定可能）に書き込まれます。
  - 終了は data/stop_requested.flag を書くか、ユーザ割り込み（Ctrl+C）。

- Monitoring（監視ループ）の起動
  python -m kabusys.run_monitoring

  特記事項:
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒指定（デフォルト 60）。
  - Monitoring は KABUSYS_ENV にかかわらず production 用 sqlite_path を使用して監視ログを記録します。
  - ストップ制御: プロジェクトルート/data/stop_requested.flag を配置すると監視ループが終了します。

- Paper Trading 検証レポートの生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または DB を指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 関連（プログラム的に利用）
  - ニューススコア付与:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

ログ
----
- ログは utils/logging_setup.setup_logging を通じて統一的に設定されます。
- デフォルトは logs/<app_name>.log（日次ローテーション、30日保持）と stdout 出力。
- 環境変数 LOG_DIR / LOG_LEVEL で挙動を変更可能。

監視・停止フロー（KILL / STOP）
-----------------------------
- run_monitoring が定期チェックし、RiskMonitor などが閾値を越えた場合に KillSwitch が data/kill.flag を作成します。ExecutionEngine は起動時・稼働中にこの kill.flag を検知して安全に停止します。
- 管理フラグ:
  - data/kill.flag — Execution 停止トリガ（Kill Switch）
  - data/stop_requested.flag — run_* スクリプトの外部終了依頼（ループを抜ける）
  - data/execution.pid — ExecutionEngine の PID 保持

注意点 / 運用上の留意事項
------------------------
- 本番環境（KABUSYS_ENV=live）では特に JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、LINE_*（通知）を適切に設定してください。validate_config は live 時に追加警告を出します。
- .env に機密情報（API キー等）を含むため、適切にアクセス制御された環境で運用してください。
- OpenAI API 呼び出しはレート制限・コストに注意。news_nlp/regime_detector はリトライやフェイルセーフを実装していますが、API キーの管理は厳密に。
- Paper Trading は実取引を行いませんが、動作確認用の DB が別ファイルになっていることを必ず確認してください。
- DuckDB/SQLite ファイルのバックアップ・権限管理を行ってください。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要ファイルと簡単な説明です（存在するファイルを抜粋して記載）。

- kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / 設定取得ロジック（Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 経由で銘柄別センチメント算出）
    - regime_detector.py — レジーム判定（ETF MA + マクロ NLP 混合）
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視ログ永続化層
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文/約定監視（滞留・異常）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の管理
    - alert_manager.py — （アラート送信管理、LINE 等）（実装ファイルがある想定）

  - execution/
    - execution_engine.py — ExecutionEngine（主要ロジック）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    - （ブローカークライアントの抽象化と Mock/実装）

  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - position_sizing.py — 株数計算、資金配分ロジック
    - risk_adjustment.py — セクターキャップ、レジーム乗数

  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン・IC・統計
  - data/
    - pipeline.py, stats.py, ...（価格データ取込・統計ユーティリティ）
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成

テスト・開発
------------
- コードは多くの純粋関数（portfolio/ 等）で構成されており、ユニットテストが書きやすい設計です。
- OpenAI 呼び出し部分は _call_openai_api をラップしており、unittest.mock.patch によるモックが可能です。
- validate_config.run_once や MonitoringEngine.run_once を使って個別コンポーネントを単体実行で確認できます。

よくある運用コマンドまとめ
--------------------------
- .env ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動:
  python -m kabusys.run_execution

- Monitoring 起動:
  python -m kabusys.run_monitoring
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足 / 参照
-----------
- .env.example（プロジェクトルートに存在する想定）を参照して必要変数を準備してください。
- ログ・DB ファイルはデフォルトで data/ および logs/ に置かれます。運用環境では永続ディレクトリへの配置・バックアップを検討してください。

問題や拡張
----------
- price 欠損時のフォールバック処理（position_sizing や sector cap の TODO）
- 銘柄ごとの lot_size（現状は共通 lot_size を想定。将来的に個別対応可能）
- OpenAI の呼び出しエラー時のさらなる堅牢化（リトライ戦略のチューニングなど）

---------------------
この README はコードから読み取れる設計/挙動をまとめたものです。実運用時は必ずローカル環境で動作確認・設定検証（python -m kabusys.validate_config）を行ってください。必要があれば README を実際の環境や運用手順に合わせてカスタマイズしてください。