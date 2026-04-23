README — KabuSys
=================

プロジェクト概要
----------------
KabuSys は日本株の自動売買／研究／監視を目的とした小規模なシステム群です。  
主要コンポーネントは以下を含みます。

- ExecutionEngine: 発注・リスク管理・約定処理（本番／ペーパートレード切替対応）
- Monitoring: システム健全性・取引履歴・リスク監視、Kill Switch（停止フラグ）発行
- Portfolio モジュール: 候補選定・重み計算・ポジションサイズ算出・セクター制限
- Research モジュール: ファクター計算・特徴量探索（DuckDB を使用）
- AI モジュール: ニュースセンチメント（OpenAI）によるスコアリング／レジーム判定
- Tools: ペーパートレード検証レポート等のユーティリティスクリプト

主な設計方針:
- 本番 DB とペーパートレード DB は完全分離
- ルックアヘッドバイアスを避ける実装（date.today() 等を直接参照しない設計）
- フェイルセーフ（API エラーや欠損時に安全側にフォールバック）

機能一覧
--------
- 環境設定ウィザード（.env 生成 / 更新）：kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml 検証）：kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）
  - paper_trading 時は MockBroker を使用し data/paper_trading.db に記録
- Monitoring ポーリング（システム状態・取引・リスク監視、Kill Switch 出力）
- Monitoring DB（SQLite）ラッパー（永続化層）
- RiskMonitor（ドローダウン／ポジション上限監視）
- Trade/システム監視・アラート統合（AlertManager 経由で通知可能）
- Portfolio 構築ユーティリティ（候補選定・重み・ポジションサイズ）
- Research（DuckDB 使用）：モメンタム、バリュー、ボラティリティ等のファクター計算
- AI（OpenAI）:
  - news_nlp.score_news: ニュースから銘柄ごとのセンチメントを ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF + マクロニュースを組み合わせて市場レジーム判定
- ツール: Paper Trading の検証レポート生成（期間指定可能）

前提条件
--------
- Python 3.9+
- 必須ライブラリ（環境に応じてインストール）:
  - duckdb
  - psutil
  - openai (AI 機能を使用する場合)
  - PyYAML（validate_config の YAML 検証を行う場合）
- SQLite（標準ライブラリで利用可）
- ネットワークアクセス（kabuステーション API / OpenAI 等を使う場合）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール（例）
   - pip install duckdb psutil openai pyyaml
   - 必要に応じてその他パッケージを追加してください

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくは .env を直接作成（下記「環境変数」参照）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

環境変数（主要）
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨/任意:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレード時の約定挙動）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（LINE 通知）
- OPENAI_API_KEY（AI 機能を使用する場合）
- KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH（必要に応じてカスタマイズ）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

デフォルトファイルパス（コード内）
- data/kabusys.duckdb（DuckDB）
- data/monitoring.db（監視 SQLite）
- data/paper_trading.db（ペーパー取引用 SQLite）
- data/kill.flag（Kill Switch）
- data/stop_requested.flag（run_* スクリプトを優雅に停止するためのファイル）
- logs/<app_name>.log（ログ、日次ローテーション）

基本的な使い方
--------------
1. 設定の作成・確認
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. ExecutionEngine を起動
   - python -m kabusys.run_execution
   - 補足:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録します。
     - 起動前に data/stop_requested.flag が存在すると起動しません。

3. Monitoring を起動
   - MONITOR_POLL_INTERVAL を環境変数で上書き可能（秒、デフォルト 60）
   - python -m kabusys.run_monitoring

4. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db PATH を使うか環境変数 PAPER_TRADING_SQLITE_PATH を設定

5. AI / レジーム判定（プログラムから呼び出す）
   - kabusys.ai.score_news(conn, target_date, api_key=...)
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
   - OpenAI API Key は環境変数 OPENAI_API_KEY または引数で渡してください

停止 / Kill Switch
------------------
- 稼働中の ExecutionEngine を安全に停止するには data/kill.flag を作成（KillSwitch が検知して停止）または data/stop_requested.flag を作成して run_* スクリプトのループを抜けさせます。
- run_execution/run_monitoring は起動時・ループ中に stop_requested.flag を確認し、存在すれば終了します。

ログ
----
- ログはデフォルトで logs/ 以下に保存され、日次ローテーションで 30 日分保持されます。
- コンソール出力は stdout に出力されます。

ディレクトリ構成（抜粋）
-----------------------
- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード）
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（main）
  - run_monitoring.py — Monitoring ポーリング起動スクリプト（main）
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書込
    - regime_detector.py — ETF + マクロニュースで市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（テーブル作成／CRUD ヘルパ）
    - system_monitor.py — システムリソース・データ鮮度監視
    - trade_monitor.py — 発注ログ整合性等（存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書込 / 管理
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出／資金配分
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — モメンタム／バリュー／ボラティリティ計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - tools/
    - paper_verification_report.py — Paper Trading の合否判定レポート生成
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（file + stdout）
    - process_priority.py — プロセス優先度／CPU affinity 設定ユーティリティ
  - data/（実行時に作られる / デフォルトの DB / フラグ置き場）
  - logs/（ログファイル）

注意事項 / トラブルシューティング
---------------------------------
- .env は絶対にリポジトリにコミットしないでください（config_setup でも同旨が注記されています）。
- OpenAI / kabuステーション 等の外部 API は環境により失敗するため、API エラーは安全側にフォールバックする実装が入っていますが、ログを確認してください。
- validate_config で PyYAML がない場合、config/*.yaml の内容検証はスキップされます（警告）。
- run_* スクリプトは stop_requested.flag を見て優雅に終了します。テスト時はこのフラグで停止操作を行うと便利です。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

さらに詳しい開発者向け情報や API 仕様はソースコード内の docstring を参照してください。必要があれば README に追記します。