README
=====

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした小規模なフレームワークです。
このリポジトリには以下の主要機能が含まれます:

- ExecutionEngine（発注実行）: 実口座／ペーパートレード両対応
- Monitoring（監視）: システム状態、注文状況、リスク（ドローダウン / ポジション上限）を定期チェック
- Portfolio Construction（銘柄選定・配分・株数決定）モジュール
- Research（ファクター計算・特徴量探索）
- AI 統合（OpenAI を使ったニュースセンチメント評価・市場レジーム判定）
- 各種 CLI/ユーティリティ: .env ウィザード、設定検証、ペーパートレード検証レポート等

主な設計方針:
- DB は DuckDB（分析）と SQLite（監視・発注ログ）を併用
- 本番／ペーパーは DB を分離（KABUSYS_ENV による切替）
- ルックアヘッドバイアスを避ける設計（日時の扱いに注意）
- OpenAI 呼び出しは失敗時にフォールバックするフェイルセーフを組み込み

特徴一覧
--------
- 環境設定ウィザード: python -m kabusys.config_setup による .env 生成/更新
- 設定検証ツール: python -m kabusys.validate_config による起動前チェック（--strict オプションあり）
- 実行エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、data/paper_trading.db にログを残す
- 監視エンジン起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- ポートフォリオ構築ユーティリティ: 候補選定・重み計算・株数決定・セクターキャップ等の純粋関数群
- AI モジュール:
  - kabusys.ai.score_news: raw_news を OpenAI に送信して銘柄別センチメントを ai_scores に格納
  - kabusys.ai.regime_detector: ETF とニュースから市場レジーム（bull/neutral/bear）を判定
- ログ設定ユーティリティ: 統一的な stdout + 日次ローテートファイル出力（logs/）

前提・依存
-----------
推奨環境:
- Python >= 3.10

主な Python パッケージ（例）:
- duckdb
- psutil
- openai
- PyYAML (config YAML 検証を行う場合に推奨)

インストール例:
- 仮想環境作成（任意）:
  python -m venv .venv
  source .venv/bin/activate  # POSIX
  .\\.venv\\Scripts\\activate  # Windows

- パッケージインストール（最低限）:
  pip install duckdb psutil openai

- YAML の検証を行いたい場合:
  pip install pyyaml

セットアップ手順
--------------
1. リポジトリをクローンしてワークディレクトリに移動
2. 仮想環境を作成して有効化（上記参照）
3. 必要な依存パッケージをインストール（上記参照）
4. .env を作成
   - 対話式に作る（推奨）:
     python -m kabusys.config_setup
   - あるいは手動でルート直下に .env を作成。必要な主要環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - OPENAI_API_KEY (AI 機能を利用する場合)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB のデフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト data/paper_trading.db）
     - LOG_LEVEL（デフォルト INFO）
     - その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知）

5. 設定検証（起動前チェック）:
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いして exit(1) になります

使い方
------
共通:
- ログ: デフォルト logs/ に app_name.log（例: execution.log, monitoring.log）を日次ローテートで出力
- DB: デフォルトは data/ 下に保存（存在しないディレクトリは自動作成を試みます）
- 停止フラグ: data/stop_requested.flag を作成すると run_monitoring / run_execution のループが終了します
- Kill Switch: data/kill.flag を書き込むと ExecutionEngine に停止シグナルが送られます

主要コマンド:
- 環境ウィザード:
  python -m kabusys.config_setup
  → .env を対話的に作成/更新します

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループ起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用 sqlite_path を使います（監視データは環境に依らず共通）

- 実行エンジン起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、PAPER_TRADING_SQLITE_PATH に記録します
  - 起動時にデータ/kill.flag が既にあれば起動せず終了します
  - 実行は別スレッドで行われ、stop フラグやデータの存在をポーリングして終了します

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを直接指定することも可能（優先順位: --db > 環境変数 > デフォルト）

AI 機能:
- OpenAI を利用するには OPENAI_API_KEY を設定してください
- kabusys.ai.score_news(conn, target_date, api_key=None) — ai_scores に書き込み
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — market_regime に書き込み
- これらは DuckDB 接続（分析用 DB）を受け取り、raw_news / prices_daily 等のテーブルを参照します

停止とフラグファイル:
- 停止を要求する（人手）:
  - run_execution/run_monitoring の停止: data/stop_requested.flag を作成
  - ExecutionEngine の強制停止（Kill Switch）: data/kill.flag を作成（KillSwitch が検出すると停止）
- KillFlag の自動クリアは KILL_FLAG_CLEAR_ON_START=1 で有効（本番では 0 推奨）

設定・環境変数（主なもの）
------------------------
- KABUSYS_ENV: development | paper_trading | live（動作モード）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効）

ディレクトリ構成
----------------
プロジェクトの主要なファイル/モジュール構成（src/kabusys を基準）:

- kabusys/
  - __init__.py
  - config.py                 # 環境変数読み込み・Settings クラス
  - config_setup.py           # .env 対話式ウィザード
  - validate_config.py        # 起動前設定検証 CLI
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - run_monitoring.py         # Monitoring 起動スクリプト
  - utils/
    - logging_setup.py        # ログ設定ユーティリティ
    - process_priority.py     # プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        # SQLite 永続化（監視テーブル）
    - system_monitor.py       # システム状態・データ鮮度監視
    - trade_monitor.py        # (存在) 注文の滞留・約定異常監視
    - risk_monitor.py         # ドローダウン・ポジション上限監視
    - kill_switch.py          # kill.flag 書き込みロジック
    - monitoring_engine.py    # 各 Monitor の束ね処理
    - alert_manager.py        # (存在) アラート送信管理（LINE 等）
  - execution/
    - execution_engine.py     # ExecutionEngine 本体（起動・セッション管理）
    - order_manager.py        # 発注管理
    - order_repository.py     # DB への注文永続化
    - reconciler.py           # ブローカーと DB の突合
    - broker_factory.py       # BrokerClient の生成（Mock/実口座分岐）
    - risk_manager.py         # 実行時のリスク制御
  - portfolio/
    - portfolio_builder.py    # 候補選定・重み
    - position_sizing.py      # 株数計算・スケーリング・丸め
    - risk_adjustment.py      # セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      # ファクター計算（momentum/value/volatility）
    - feature_exploration.py  # 将来リターン・IC・統計
  - ai/
    - news_nlp.py             # ニュース NLP → ai_scores 書き込み
    - regime_detector.py      # 市場レジーム判定
  - data/                      # 実行時に作成される（DB / pid / flag / logs など）
  - tools/
    - paper_verification_report.py  # ペーパートレード検証レポート生成スクリプト

補足・開発者向けノート
---------------------
- DuckDB は分析用に SQL を直接投げる設計です。prices_daily / raw_financials / raw_news 等のテーブル構築は別途スクリプト等で行ってください。
- 設定検証ツールは PyYAML がない場合 YAML の中身検証をスキップします（警告）。
- OpenAI 連携は外部 API に依存するため、キーを設定しても API 利用制限・コストを考慮してください。
- ログディレクトリ作成に失敗するとファイルハンドラは無効になり stdout のみになります。LOG_DIR 環境変数で変更可能です。
- プロセス優先度/CPU affinity の設定はプラットフォーム依存かつ権限が必要な場合があります（psutil の権限エラーは警告でスキップ）。

ライセンス
----------
（このテンプレートにはライセンスファイルが含まれていません。必要に応じて LICENSE を追加してください。）

問い合わせ
----------
不具合報告・機能要望はリポジトリの issue を利用してください。README の内容に誤りや不足があれば PR も歓迎します。