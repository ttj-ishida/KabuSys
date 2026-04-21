KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。  
主なコンポーネントは実行エンジン（ExecutionEngine）、監視（Monitoring）、ファクター／リサーチ、ポートフォリオ構築、AI（ニュース NLP / レジーム判定）などで構成されています。  
設計方針として「本番 DB とペーパートレードの分離」「ルックアヘッドバイアス回避」「外部 API の失敗に対するフェイルセーフ」などを重視しています。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading（MockBrokerClient）／live を切替。
  - ペーパートレード時は data/paper_trading.db に分離して記録。
  - プロセス優先度を高く設定して実行。
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム負荷・データ鮮度・取引ログ・リスク（ドローダウン・ポジション上限）等のポーリング監視。
  - Kill Switch（条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る）。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定（デフォルト 60 秒）。監視は常に本番用 sqlite_path を参照。
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等比配分 / スコア重み / リスクベースのポジションサイジング。
  - セクター集中制限やレジームに応じた乗数適用。
- リサーチ（research パッケージ）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用して prices_daily などのテーブルを参照）。
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー等。
- AI モジュール（ai パッケージ）
  - ニュース記事に対する LLM ベースのセンチメントスコアリング（news_nlp.score_news）。
  - 市場レジーム判定（regime_detector） — LLM と価格情報を組み合わせて daily レジーム（bull/neutral/bear）を判定。
  - LLM 呼び出しは OpenAI クライアント（環境変数 OPENAI_API_KEY）を利用。リトライ・パース保護等を実装。
- ツール類
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

前提（推奨）
-------------
- Python 3.10+
- 推奨ライブラリ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で利用）
- SQLite（標準パッケージで可）
- ネットワーク接続（OpenAI 等 API 利用時）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <project-root>

2. Python 仮想環境の作成と有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows の場合: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 代表的な依存:
     - pip install duckdb psutil openai PyYAML
   - 実際の requirements.txt がある場合はそれを使用してください（本リポジトリに同梱されている場合）。

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って J-Quants トークン、kabu API パスワード、KABUSYS_ENV（development/paper_trading/live）等を設定してください。
   - 生成された .env は決してコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合はエラーメッセージに従って修正します。
   - --strict を付けると警告もエラー扱いになります。

基本的な使い方
----------------
- 実行エンジン（Execution）
  - 本番またはペーパートレードの ExecutionEngine を起動します:
    - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データは data/paper_trading.db に記録されます。
  - 起動時に data/stop_requested.flag が既に存在するとエンジンを起動しません（安全措置）。
  - 実行中は data/execution.pid に PID が書き込まれます。

- 監視（Monitoring）
  - 監視ループを開始:
    - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を設定可能。例: export MONITOR_POLL_INTERVAL=30
  - 監視は常に本番 sqlite_path を参照して監視データを記録します（環境にかかわらず本番の監視 DB を使う設計）。
  - 停止方法:
    - プロジェクトルートの data/stop_requested.flag を作成すると、監視ループは次のポーリングで終了します（run_execution も同様に検出して停止）。
    - KillSwitch（条件満足）により data/kill.flag が作成されると、ExecutionEngine 側で停止シグナルとして扱われます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）
  - 稼働率、注文成功率（fill rate）、送信率、P95 レイテンシなどを集計して PASS/FAIL を判定します。

- AI / レジーム判定・ニューススコア
  - news_nlp.score_news をプログラムから呼ぶ場合、OpenAI API キーを指定（引数または環境変数 OPENAI_API_KEY）。
  - 例（スクリプト内呼び出し）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="xxxxx")

重要な環境変数（主要）
---------------------
- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API リフレッシュトークン
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- OPENAI_API_KEY — OpenAI を利用する場合の API キー
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring.db）のパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL / LOG_DIR — ログ設定
- KILL_FLAG_CLEAR_ON_START — 本番での Kill Flag 自動クリア設定（0/1）

運用上のポイント
-----------------
- 監視は常に本番の監視 DB（SQLITE_PATH）を使うように設計されています。ペーパートレードの Execution は paper_sqlite_path に分離されます。
- Kill Switch（monitoring.kill_switch）により、ドローダウンやポジション上限等の条件を満たすと data/kill.flag が書かれ、ExecutionEngine が停止する仕組みです。必要に応じて kill.flag を手動で作成/削除できます（clear() を実行する API も提供）。
- ログは logs/<app_name>.log に日次ローテートで保存されます（utils.logging_setup.setup_logging を各起動スクリプトが呼出）。
- process priority は起動時に high に設定されます（utils.process_priority.set_process_priority）。権限等で失敗する場合は警告でスキップします。
- LLM 呼び出しは外部ネットワークを使うため、API レート制限や一時エラーに対してリトライとフォールバックを実装しています。

ディレクトリ構成（主要ファイル）
-------------------------------
（プロジェクトルート / src/kabusys を想定）

- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定読み込みロジック
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py   — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP（OpenAI 呼出、ai_scores 書込み）
    - regime_detector.py             — 市場レジーム判定（LLM + MA200 等）
  - monitoring/
    - monitoring_db.py               — SQLite テーブル初期化 / 永続化 API
    - system_monitor.py              — システム状態 / データ鮮度監視
    - trade_monitor.py               — （取引ログ監視 — 実装あり）
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — kill.flag の作成 / 管理
    - monitoring_engine.py           — 各 Monitor を束ねるランナー
    - alert_manager.py               — 通知（LINE 等）管理（実装参照）
  - portfolio/
    - portfolio_builder.py           — 候補選定 / 重み計算
    - position_sizing.py             — 株数決定 / 単元丸め / 集約キャップ
    - risk_adjustment.py             — セクター上限 / レジーム乗数
    - __init__.py
  - research/
    - factor_research.py             — Momentum / Volatility / Value 等
    - feature_exploration.py         — 将来リターン / IC / 統計
    - __init__.py
  - utils/
    - logging_setup.py               — 共通ログ設定ユーティリティ
    - process_priority.py            — プロセス優先度 / CPU affinity
    - __init__.py
  - monitoring/*, execution/*, data/* など （DB/フラグファイルは data/ に置く想定）

補足（開発者向け）
------------------
- .env 自動ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml が存在する場所）を検出して .env/.env.local を自動で読み込みます。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブル作成と簡単なカラム追加マイグレーションを行います。
- テスト:
  - 外部 API 呼び出し（OpenAI など）はユニットテストでモックすることを想定した設計（内部呼び出し関数を差し替え可能）。

ライセンス / バージョン
-----------------------
- バージョン: __version__ = "0.1.0" （kabusys.__init__.py）
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（存在する場合）。

以上。導入や運用で不明点があれば、どのスクリプトをどう動かしたいか（例: 本番での監視構成、ペーパートレードの検証方法など）を教えてください。必要に応じて具体的なコマンド例やトラブルシュート手順を追加で作成します。