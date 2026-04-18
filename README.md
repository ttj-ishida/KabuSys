README
=====

概要
----
KabuSys は日本株向けの自動売買 / 調査用ライブラリ兼実行基盤です。  
主に以下の機能を備え、実行用エンジン（ExecutionEngine）と監視（Monitoring）を分離して運用できる設計になっています。

主な特徴:
- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（システム状態・注文ログ・リスク監視・Kill Switch）
- Portfolio 構築（候補選定、重み計算、ポジションサイジング、セクター制約）
- Research（ファクター計算・将来リターン・IC、特徴量解析）
- AI モジュール（ニュース NLP によるセンチメントスコアリング、レジーム判定）
- 各種ツール（ペーパートレード検証レポート生成 等）
- 簡易的な設定ウィザード・検証 CLI、統一的なログ設定

機能一覧
--------
- 実行（run_execution.py）
  - 実際のブローカークライアントまたは Paper Trading 用の MockBrokerClient を起動
  - 発注 / 注文履歴（SQLite）・分析（DuckDB）への書き込み
  - PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止
- 監視（run_monitoring.py / MonitoringEngine）
  - CPU/Mem/Disk、Execution プロセスの生存、データ鮮度、滞留注文・約定異常の検出
  - Kill Switch（data/kill.flag）による Execution 停止トリガー
  - 監視ログ（SQLite）と DuckDB を利用した分析データとの連携
- ポートフォリオ（kabusys.portfolio）
  - 候補選定、等金額/スコア加重の重み算出
  - セクター上限・レジーム乗数・ポジションサイズ計算（単元株丸め 等）
- リサーチ（kabusys.research）
  - Momentum / Value / Volatility 等のファクター計算（DuckDB 上の prices_daily/raw_financials を参照）
  - 将来リターン計算、IC（Spearman rank）や統計サマリー
- AI（kabusys.ai）
  - ニュース記事を LLM（OpenAI）でスコアリングして ai_scores テーブルへ書き込み
  - 市場レジーム判定（ETF の MA とマクロセンチメントの合成）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- 設定管理
  - .env 対話式作成ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
- ユーティリティ
  - ログ設定（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）

セットアップ手順
----------------

前提
- Python 3.9+ を想定（実行環境に依存）
- 必要な外部パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証時、任意）

インストール（例）
- 仮想環境を作成しアクティベート
  python -m venv .venv
  source .venv/bin/activate  # macOS/Linux
  .\.venv\Scripts\activate   # Windows

- 必要パッケージをインストール（プロジェクトに requirements.txt があればそれを使う）
  pip install duckdb psutil openai PyYAML

初期設定
1. .env を生成（推奨）
   python -m kabusys.config_setup
   - ウィザード形式で .env を生成 / 更新します。
   - 生成後、.env を絶対に Git にコミットしないでください。

2. 設定を検証
   python -m kabusys.validate_config
   - --strict を指定すると警告も FAIL 扱いで exit(1) になります。

ディレクトリ・ファイルの準備
- デフォルトでは以下のファイル/ディレクトリが使用されます（必要なら作成してください）:
  - data/ （SQLite、PID、フラグファイル等）
  - logs/ （ログファイル）
- 必要に応じて .env でパスを上書きしてください（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH）。

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR、デフォルト: INFO）
- OPENAI_API_KEY（AI モジュール使用時）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔（秒）、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか: 0/1）

使い方
------

設定・検証
- .env の生成（対話式）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

ログ設定
- 共通の logging 設定ユーティリティを使用:
  from kabusys.utils.logging_setup import setup_logging
  setup_logging(app_name="execution")

監視の起動
- デフォルトのポーリング間隔（MONITOR_POLL_INTERVAL=60 秒）:
  python -m kabusys.run_monitoring

- 環境変数でポーリング間隔を指定:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 監視は .env の KABUSYS_ENV に関係なく本番用 sqlite_path を使用して監視 DB を初期化します。

実行エンジンの起動
- 本番 / 開発 / ペーパートレードは KABUSYS_ENV で制御:
  KABUSYS_ENV=development python -m kabusys.run_execution
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- ペーパートレード時は MockBrokerClient を用い、デフォルトで data/paper_trading.db に記録（本番 DB と分離）。

停止（Kill / Stop）
- data/stop_requested.flag が存在すると run_monitoring と run_execution のループは終了処理を行います（stop フラグ、外部からの安全な停止）。
- Kill Switch（監視が検知し実行する停止）は data/kill.flag を作成します。Execution 起動時に KILL_FLAG_CLEAR_ON_START が 1 であれば自動クリアされます（本番では 0 を推奨）。

ツール
- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report
  オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  環境変数 PAPER_TRADING_SQLITE_PATH に DB を設定することも可能

AI / LLM 機能
- ニュース NLP スコアリング:
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（conn）を渡し target_date を指定して実行すると、ai_scores テーブルへ書き込みます。
  - OPENAI_API_KEY を環境変数で設定するか api_key に渡してください。

Quick start 例
1) .env を作成
   python -m kabusys.config_setup

2) 設定検証
   python -m kabusys.validate_config

3) 監視を起動（別プロセスで）
   MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

4) 実行エンジンを起動（別プロセス）
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution

ディレクトリ構成
----------------
以下はソースコード配下の主要ファイルとサブパッケージの概観（src/kabusys 以下）:

- __init__.py
- config.py                 — 環境変数 / 設定読み込み、Settings クラス
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証 CLI

- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト

- ai/
  - news_nlp.py             — ニュース記事の LLM スコアリング
  - regime_detector.py      — 市場レジーム判定
  - __init__.py

- monitoring/
  - monitoring_db.py        — SQLite 用永続化層（テーブル初期化 / CRUD）
  - system_monitor.py       — CPU/Mem/Disk、データ鮮度、プロセス監視
  - trade_monitor.py        — （trade 関連監視ロジック: 滞留注文等）※実装参照
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag 書き込みロジック
  - monitoring_engine.py    — 各 Monitor を束ねるループ
  - alert_manager.py        — （通知管理、LINE 等）※実装参照

- execution/
  - execution_engine.py     — 実行エンジン本体（セッション管理）
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py

- portfolio/
  - portfolio_builder.py    — 候補選定・重み
  - position_sizing.py      — 株数計算・スケールダウンロジック
  - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - __init__.py

- research/
  - factor_research.py      — Momentum / Value / Volatility ファクター
  - feature_exploration.py  — 将来リターン、IC、統計サマリー
  - __init__.py

- data/                    — デフォルトの DB / フラグ / PID 保存場所（runtime）
  - monitoring.db (default)
  - paper_trading.db (default)
  - kill.flag
  - stop_requested.flag
  - execution.pid

- tools/
  - paper_verification_report.py

- utils/
  - logging_setup.py        — 共通ログ設定
  - process_priority.py     — 優先度／CPU affinity ユーティリティ
  - __init__.py

注意事項 / 運用上のヒント
-----------------------
- 本番運用時は KABUSYS_ENV=live を使用してください。validate_config は live の場合に追加警告を出します（LINE の設定など）。
- .env に秘密情報（API トークン等）を平文で保存する設計です。リポジトリにコミットしないでください。
- run_monitoring は監視 DB を初期化します（monitoring は環境に関わらず本番 sqlite_path を使用する設計になっています）。
- run_execution は paper_trading 環境であれば paper_sqlite_path（分離された DB）を使用して記録します。
- Logs は logs/<app_name>.log に日次ローテーションで出力されます（デフォルト 30 日保持）。LOG_DIR 環境変数で変更可能。
- OpenAI API 呼び出しは外部サービス依存です。API キー管理・レート制限に注意してください。AI 機能はフェイルセーフ（失敗時フォールバック）設計になっていますが、運用ポリシーを用意してください。

ライセンス / 著作権
------------------
（ここにプロジェクトのライセンス情報を記載してください）

お問い合わせ / 開発
-------------------
- 開発者向け: 各モジュールはユニットテスト可能な純粋関数・クラス群で構成されています。モジュール境界によりテスト置換（モック）しやすい設計です。
- 質問や改良提案があれば README に追記してください。