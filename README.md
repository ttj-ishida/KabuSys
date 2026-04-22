KabuSys — 日本株自動売買システム（リポジトリ README）
以下はコードベース（src/kabusys）に基づく導入・使い方ドキュメントです。開発者・運用者向けの要点を日本語でまとめています。

プロジェクト概要
- KabuSys は日本株自動売買・研究・監視を目的としたモジュール群です。
- 主な機能は戦略研究（ファクター計算／特徴量解析）、ポートフォリオ構築（候補選定・重み付け・株数計算）、注文実行エンジン（ExecutionEngine）、監視（Monitoring）および AI を使ったニュースセンチメント／レジーム判定です。
- 設計方針の例：DuckDB を使った分析、SQLite を監視ログ用に使用、Paper Trading は本番 DB と分離して動作、OpenAI API はオプションでニュース解析／レジーム判定に利用。

主な機能一覧
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db を使用（本番と分離）
  - プロセス優先度設定、PID 管理、停止フラグ監視
- 監視ループ起動スクリプト: run_monitoring.py
  - SystemMonitor をポーリングして system_status 等を監視・永続化
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
- 設定ウィザード / 検証
  - python -m kabusys.config_setup : .env の対話式生成・更新
  - python -m kabusys.validate_config [--strict] : .env / config/*.yaml の事前検証
- 監視 / Kill Switch / アラート
  - monitoring/ 配下に SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine 等
  - kill.flag によるエンジン停止シグナル、stop_requested.flag によるプロセス終了
- ポートフォリオ構築
  - 候補選定（select_candidates）、等重・スコア重み付け、リスク調整（セクターキャップ・レジーム乗数）、株数算出（単元丸め・aggregate cap）
- 研究用モジュール
  - research.factor_research: momentum / volatility / value 等のファクター計算（DuckDB 接続）
  - research.feature_exploration: 将来リターン計算、IC（Spearman ρ）、統計サマリー等
- AI / NLP（オプション）
  - ai.news_nlp.score_news: raw_news → OpenAI による銘柄別センチメントを ai_scores に書込
  - ai.regime_detector.score_regime: ETF の MA 乖離 + マクロ記事の LLM センチメントで市場レジーム判定
- 運用支援ツール
  - tools.paper_verification_report: ペーパートレード DB を集計して検証レポートを生成

必要な前提・依存
- Python 3.10+（PEP 604 の型表記や最新構文の利用を考慮）
- 必須／推奨パッケージ（少なくとも下記を pip でインストールしてください）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config 検証時に YAML を解析する場合）
- ビルトイン: sqlite3, logging, pathlib 等

セットアップ手順（開発 / 簡易）
1. リポジトリをクローン、作業ディレクトリをプロジェクトルートにする
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix) / .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （必要に応じて他の依存を追加）
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参照）
   - 主に設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - LOG_LEVEL（例: INFO）
     - OPENAI_API_KEY（AI 機能利用時）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject）
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

設定検証
- 設定整合性チェック: python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit(1)

使用例（運用用コマンド）
- 実行エンジンを起動
  - python -m kabusys.run_execution
  - 停止は data/stop_requested.flag を作成すると検知して停止
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring で間隔を変更
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（優先順位: --db > 環境変数 > デフォルト）
- AI スコア付与（Python API）
  - score_news(conn, target_date, api_key=None) — ai.news_nlp.score_news を呼ぶ（DuckDB 接続が必要）
  - score_regime(conn, target_date, api_key=None) — ai.regime_detector.score_regime

ログ・データ・フラグの配置
- data/
  - monitoring.db（デフォルトの SQLite 監視 DB）
  - paper_trading.db（Paper Trading 用 DB、環境変数で上書き可能）
  - execution.pid（ExecutionEngine の PID 管理）
  - kill.flag（Kill Switch により Execution を停止するためのファイル）
  - stop_requested.flag（run_* スクリプトの外部停止フラグ）
- logs/
  - ログは logs/<app_name>.log に日次ローテーションで出力（デフォルト 30 日保持）
  - 環境変数 LOG_DIR で変更可能
- 注意: .env は絶対に Git にコミットしないこと

簡単な Python 呼び出し例（研究用）
- DuckDB コネクションを渡してモジュールを使う例:
  - import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    from kabusys.research import calc_momentum
    records = calc_momentum(conn, date(2026,4,1))
- AI 関連は環境変数 OPENAI_API_KEY を設定するか、api_key 引数で渡す

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                  — パッケージ定義、バージョン
  - config.py                    — 環境変数/設定読み込み・Settings
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — 優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py           — SQLite の永続化層（テーブル初期化 / CRUD）
    - system_monitor.py          — システム / データ鮮度監視
    - trade_monitor.py           — （注文監視: ファイル内に実装あり）
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — kill.flag 管理
    - monitoring_engine.py       — 各モニタの統合ループ
    - alert_manager.py           — （アラート送信管理: 実装参照）
  - execution/
    - execution_engine.py        — ExecutionEngine（起動・セッション管理）
    - broker_factory.py          — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 発注株数計算・上限制御
    - risk_adjustment.py         — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py         — ファクター計算（momentum / value / volatility）
    - feature_exploration.py     — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py                — ニュースセンチメント（OpenAI 呼出）
    - regime_detector.py         — レジーム判定（MA + マクロセンチメント）
  - data/ (推奨ローカルディレクトリ)
    - monitoring.db
    - paper_trading.db
    - stop_requested.flag
    - kill.flag
    - execution.pid
  - logs/                         — ログファイル格納（logs/<app_name>.log）

運用上の注意
- KABUSYS_ENV が live の場合は本番扱いになります。validate_config で本番ガード（LINE トークン等）を確認してください。
- Paper Trading は本番 DB と分離されるよう設計されています。環境変数 PAPER_TRADING_SQLITE_PATH を確認してください。
- kill.flag / stop_requested.flag / execution.pid による外部制御を用意しています。運用時にこれらの取り扱いルールを決めてください。
- OpenAI を呼ぶ機能は API キーに課金が発生する点に注意してください。障害時はフェイルセーフ（スコア 0.0 等）で継続する実装です。

よくあるコマンドまとめ
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- ペーパートレード検証: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

追加情報・拡張
- DuckDB 内のテーブル（prices_daily / raw_financials / raw_news / ai_scores 等）に依存するため、データ投入パイプライン（data pipeline）を別途整備する必要があります。
- 将来的には lot_size を銘柄別に持たせる、リスク・手数料の詳細反映などの拡張が想定されています（ソース内に TODO コメントあり）。

フィードバック / コントリビューション
- README の改善、ドキュメント追記、ユニットテスト追加、運用スクリプトの containerization（Docker 化）など歓迎します。

以上。必要であれば、セットアップ用の requirements.txt や example .env、運用手順の詳細（systemd / supervisor 用の unit ファイル例）を作成します。どの情報を優先して追加しますか？