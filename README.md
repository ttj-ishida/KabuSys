README
======

注意: この README は src/kabusys のコードベースに基づいて作成した日本語の利用説明書です。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買システム / 研究フレームワークです。  
主要コンポーネントは以下を含みます:

- ExecutionEngine: 発注ロジック、注文管理、リスク管理を統合して売買セッションを実行
- Monitoring: システム状態・注文状態・リスク指標をポーリングして記録・アラート・Kill Switch を管理
- Portfolio: 銘柄選定・重み付け・ポジションサイズ計算・セクター制約などのポートフォリオ構築ロジック
- Research: DuckDB 上の時系列データを用いたファクター計算・特徴量解析ユーティリティ
- AI: OpenAI を利用したニュースのセンチメント評価や市場レジーム判定
- Tools: ペーパートレード結果検証などの CLI ツール

設計方針の要点:
- DuckDB/SQLite をローカル DB として利用し、分析と監視を分離
- Paper trading（ペーパートレード）と Live（本番）を分離して安全にテスト可能
- ログ・PID・フラグファイルを用いた運用制御（停止フラグ、Kill Switch 等）
- OpenAI API 呼び出しは再試行やフェイルセーフを備え、失敗時は安全側の挙動を取る

主な機能一覧
-------------
- 発注エンジン（ExecutionEngine）: ブローカークライアント抽象化、リスク管理、注文管理、再調整（reconciler）
- 監視（Monitoring）: CPU / メモリ / ディスク / プロセス生存 / データ鮮度のチェック、監視ログを SQLite に保存
- Kill Switch: ドローダウンやポジション上限超過で data/kill.flag を作成して ExecutionEngine を停止
- ポートフォリオ構築: 候補選定、等配分・スコア加重、リスクベースの株数計算、セクターキャップ、レジーム乗数
- 研究用ユーティリティ: モメンタム/ボラティリティ/バリュー等のファクター計算、将来リターン、IC 計算
- AI ニュース解析: OpenAI を用いたニュースの銘柄別センチメントスコア算出（ai_scores に保存）
- レポート: ペーパートレード検証レポート生成ツール（tools/paper_verification_report.py）
- 設定管理: .env ウィザード（config_setup.py）、設定検証 CLI（validate_config.py）
- ロギングの統一設定（utils.logging_setup）

必要条件
--------
- Python >= 3.10（コードは | 型注釈等を使用）
- 必須 Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合に必要）
- 任意:
  - その他ブローカークライアント実装に依存するライブラリ（プロダクション接続時）

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone ... （リポジトリ URL を使用）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt があれば pip install -r requirements.txt）

4. 環境変数の設定 (.env)
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - ウィザードは .env を生成・更新します
   - 手動で .env を作成する場合は .env.example（存在する場合）を参考にしてください
   - 自動 .env ロード:
     - config.py はプロジェクトルートに基づいて .env / .env.local を自動読み込みします
     - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります

6. データディレクトリの作成（自動作成される箇所は多いですが念のため）
   - mkdir -p data logs

基本的な使い方
--------------

- 設定の作成・更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - exit コード: 0 = OK、1 = FAIL（エラーまたは --strict で警告がある場合）

- ExecutionEngine の起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存:
    - paper_trading: MockBrokerClient を使用、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
    - live/development: 実ブローカークライアントを使用し本番 sqlite_path を使用
  - 起動時に data/stop_requested.flag の存在を検査し、存在すると起動せず終了します
  - 実行中は data/execution.pid に PID を書き出します

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - デフォルトポーリング間隔 60 秒。環境変数で変更可能:
    - MONITOR_POLL_INTERVAL=30 など（1 秒以上の整数）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視データを保存します
  - 停止: data/stop_requested.flag を作成するとループが検知して終了します

- Kill Switch（ExecutionEngine 停止フラグ）
  - KillSwitch は risk_monitor 等の結果に基づき data/kill.flag を作成します
  - ExecutionEngine 側では Settings.kill_flag_clear_on_start が 1 の場合起動時に kill.flag を自動クリアする動作を制御（設定に注意）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db、または --db で指定

- AI/NLP 関連（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、指定日用のニューススコアを ai_scores テーブルへ書き込みます
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを計算して market_regime テーブルへ書き込みます

環境変数一覧（主なもの）
------------------------
（Settings / validate_config / config_setup を参照して整理）

必須（少なくとも起動前に設定が期待される）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）

運用 / 任意
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- OPENAI_API_KEY: OpenAI 利用時の API キー（AI モジュール使用時に必要）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject、デフォルト instant）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH: PID や kill.flag のパス（デフォルト data/execution.pid, data/kill.flag）

ログとファイル / 運用用フラグ
------------------------------
- ログ: デフォルト logs/<app_name>.log（utils.logging_setup が日次ローテーションで出力）
- SQLite / DuckDB デフォルト:
  - data/monitoring.db — 監視ログ
  - data/paper_trading.db — ペーパートレード履歴
  - data/kabusys.duckdb — 分析用 DuckDB
- PID / フラグ:
  - data/execution.pid — ExecutionEngine の PID（run_execution が使用）
  - data/stop_requested.flag — スクリプト起動ループの外部停止トリガー（run_monitoring, run_execution が使用）
  - data/kill.flag — Kill Switch による強制停止フラグ
- 注意: Monitoring は明示的に本番 sqlite_path を使用するため、paper_trading でも監視 DB は本番設定を参照します（監視ログは本番 DB に集約される設計）

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 配下の主要ファイル / パッケージと簡単な説明です（抜粋）:

- kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数・.env 自動ロード、Settings クラス
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成 CLI
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）スコアリング
    - regime_detector.py — 市場レジーム判定（OpenAI + MA200 等）
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB の初期化 / 永続化 API
    - system_monitor.py — システム監視（CPU/メモリ/ディスク/データ鮮度）
    - trade_monitor.py — （コード中にあり）注文監視（滞留注文・異常約定等）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch の管理（flag ファイル書込み）
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - alert_manager.py — （アラート送信の抽象化）
  - execution/
    - execution_engine.py — 発注エンジン本体
    - broker_factory.py — BrokerClient の生成（paper_trading 時は Mock）
    - order_manager.py, order_repository.py, reconcilier.py, risk_manager.py — 発注・リスク管理周り
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
  - research/
    - factor_research.py, feature_exploration.py — ファクター計算・解析
  - utils/
    - logging_setup.py — 統一ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (運用時に生成される想定)
    - monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid
  - logs/
    - execution.log, monitoring.log, ...（日次ローテート）

運用のヒント / 注意点
--------------------
- 本番（KABUSYS_ENV=live）では LINE トークンや通知先の設定を必ず確認してください。validate_config は live のときに追加警告を出します。
- Kill Switch の自動クリア（KILL_FLAG_CLEAR_ON_START）は本番で危険です。デフォルト 0（クリアしない）を推奨します。
- Monitoring のポーリング間隔を短くするとログが増えます。MONITOR_POLL_INTERVAL は整数秒で 1 以上にしてください。
- Paper trading は本番 DB と分離しているため、ペーパートレードの検証や実験は paper_trading モードで安全に実行できます。
- OpenAI の利用は API キーが必要です。AI モジュールは外部 API 呼び出しのためコストとレート制限を考慮してください。エラーが多い場合の再試行ログを確認してください。
- DB の初期化: monitoring は起動時に必要なテーブルを自動生成します（init_monitoring_db）。ただし config/*.yaml の生成や外部マスタデータ（prices_daily 等）は別途準備が必要です。

開発 / 貢献
--------------
- コードはモジュール化されており、ユニットテストやモックを用いたテストが容易です。AI 呼び出し部分はテスト時に差し替え可能な設計になっています（_call_openai_api など）。
- 新しい機能追加や修正の際はまずローカルで config_setup → validate_config → run_monitoring/run_execution の流れで動作確認してください。

問い合わせ
-----------
この README はソースコードのコメントと構成から自動生成・要約したものです。実運用前には必ず設定の確認、テスト、およびセキュリティ（API キー管理等）の確認を行ってください。