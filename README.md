KabuSys — 日本株自動売買システム（README）
=====================================

概要
----
KabuSys は日本株向けの自動売買／研究プラットフォームのコードベースです。  
主な目的は次の通りです。

- 戦略の研究（DuckDB ベースのファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 発注実行（実口座 / ペーパートレード対応）
- システム監視（プロセス稼働状態、注文ログ、リスク監視、Kill Switch）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- 運用補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

主な特徴
--------
- 環境別分離
  - KABUSYS_ENV により development / paper_trading / live を切り替え
  - paper_trading では MockBroker を用い、専用 SQLite（data/paper_trading.db）に記録して本番 DB と完全分離
- 監視機能
  - system / trade / risk 各種モニタ、Kill Switch による安全停止
  - 監視データを SQLite に永続化（monitoring.db）
- ポートフォリオ構築
  - 候補選定、等金額・スコア加重、リスクベースのポジション決定
  - セクターキャップ、レジーム乗数を組み合わせた安全管理
- 研究モジュール
  - DuckDB を用いたファクター（モメンタム/ボラティリティ/バリュー）計算
  - 将来リターン、IC（情報係数）や統計サマリー
- AI 機能（OpenAI）
  - ニュース記事のセンチメントを LLM で評価して ai_scores に保存
  - マクロ記事と ETF MA200 を組み合わせた市場レジーム判定
- 運用ユーティリティ
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成スクリプト

セットアップ
-----------
前提
- Python 3.10+（typing の | None 等を使用）
- Git（ソース取得）
- SQLite（標準で利用可）
- 任意：system 上での実行権限（プロセス優先度や CPU affinity 設定により管理者権限が必要になる場合あり）

推奨手順（ローカル開発）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil openai
   - 任意で YAML 検証用: pip install pyyaml
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）
4. .env を作成
   - python -m kabusys.config_setup
   - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など（ウィザードで入力）
   - OpenAI 機能を使う場合は OPENAI_API_KEY を設定
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる
6. 初期 DB ファイルやディレクトリ
   - デフォルトで data/ と logs/ にファイルが作成されます（必要に応じて .env 内のパスを調整）

主要な環境変数（概要）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…、デフォルト INFO）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

使い方（主要コマンド）
--------------------

設定関連
- 対話式 .env 作成
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]

監視
- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（例: MONITOR_POLL_INTERVAL=30）
  - 監視は monitoring.db（Settings.sqlite_path）に記録

実行エンジン（Execution）
- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_db（PAPER_TRADING_SQLITE_PATH）へ記録し MockBroker を使用
  - data/stop_requested.flag（停止要求フラグ）を置くと安全に停止させる。data/execution.pid に PID を書く仕組みあり

ツール
- ペーパートレードの検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: PAPER_TRADING_SQLITE_PATH 環境変数、無ければ data/paper_trading.db

AI / レジーム / ニュース
- ニュース NLP（ai.news_nlp.score_news）やレジーム判定（ai.regime_detector.score_regime）は OpenAI API キーが必要です。内部で gpt-4o-mini を指定しています。
- 実行はコード経由で呼ぶか、将来的な CLI を通じて行います（直接のエントリスクリプトはライブラリ関数として提供されています）。

運用上のフラグ
- data/stop_requested.flag: run_execution / run_monitoring の外部停止フラグ（ファイルを作るとループが終了）
- data/kill.flag: KillSwitch が運用停止を要求すると書き込まれる（ExecutionEngine は起動時にこのフラグを確認）
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリア（本番では 0 を推奨）

ログ
- ログは logs/<app_name>.log に日次ローテーションで保存（30世代保持）
- setup_logging() により stdout とファイルの両方に出力

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要ファイル / モジュールの概観（抜粋）です。

- src/kabusys/
  - __init__.py               — パッケージ初期化（バージョン等）
  - config.py                 — 環境変数 / Settings クラス、自動 .env ロードロジック
  - config_setup.py           — .env 対話ウィザード（CLI）
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト

  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — SQLite の監視テーブル定義と永続化クラス
    - system_monitor.py       — システム状態 / データ鮮度監視
    - trade_monitor.py        — 注文ログ監視（滞留注文等）  ※実装ファイルあり（抜粋外）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — Kill Switch ロジック（kill.flag の書き込み）
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — アラート送信ロジック（LINE 等） ※実装ファイルあり（抜粋外）
  - execution/
    - execution_engine.py     — ExecutionEngine（発注セッション制御） ※実装ファイルあり（抜粋外）
    - broker_factory.py       — Broker クライアント生成（Mock / 実環境切替）
    - order_manager.py        — 注文管理
    - order_repository.py     — 注文履歴永続化
    - reconciler.py           — ブローカ状態整合処理
    - risk_manager.py         — 発注前リスクチェックロジック
  - portfolio/
    - portfolio_builder.py    — 候補選定、重み付け
    - position_sizing.py      — 株数決定、資金配分、lot 単位丸め
    - risk_adjustment.py      — セクター制限、レジーム乗数
  - research/
    - factor_research.py      — モメンタム / ボラティリティ / バリュー計算（DuckDB）
    - feature_exploration.py  — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）で ai_scores 書き込み
    - regime_detector.py      — マクロ + ETF MA200 でレジーム判定（OpenAI）
  - data/                     — 既定の data ファイル（生成される：monitoring.db, paper_trading.db, flags, pid など）
  - logs/                     — ログ出力先（setup_logging により作成）

設計上の注意点 / 運用メモ
------------------------
- paper_trading モードでは本番 DB と分離されるため、実運用前の検証に最適です（ただし実際のマーケットと挙動が異なる可能性あり）。
- AI 機能は OpenAI API に依存します。API 呼び出し時の失敗はフェイルセーフでスキップやデフォルト値にフォールバックする実装がなされていますが、API キー管理やコスト管理は運用側で注意してください。
- 監視 / 実行プロセスは stop/kill フラグファイルを使って外部から安全に操作できます。自動クリア設定は本番環境で危険になり得るためデフォルトは無効です。
- DuckDB / prices_daily 等のデータテーブルは research モジュールで前提として使用されます。分析用データ投入は別のパイプライン（kabusys.data.pipeline 等）を想定しています。

開発・拡張
-----------
- 新しい監視ルールやアラート、戦略モジュールは各ディレクトリにある純粋関数／クラスとして追加できます。
- AI 周りの呼び出し部分はリトライ・バリデーションを組み込んでおり、テスト時は _call_openai_api 等をモックして振る舞いを検証できます。
- DuckDB を使った研究モジュールは SQL と Python の混在クエリで記述されており、データモックを用いた単体テストが可能です。

ライセンス / 貢献
-----------------
（リポジトリ側で指定してください）

問い合わせ / 参考
------------------
- コード内ドキュメント（docstring）が詳細な設計意図・運用注意を記載しています。まずは該当モジュールの docstring を参照してください。
- 環境変数の初期化は python -m kabusys.config_setup を使うと安全です。設定検証は python -m kabusys.validate_config で実行してください。

以上。必要があれば実行手順や .env のサンプル、依存パッケージの requirements.txt を追加で作成します。どの部分の具体例が欲しいか教えてください。