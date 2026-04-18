KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買 / 研究用ライブラリ群と実行／監視用スクリプト群を含むプロジェクトです。  
本 README はコードベース（src/kabusys 以下）を基に、プロジェクト概要、機能一覧、セットアップ手順、使い方、主要ディレクトリ構成を日本語でまとめたものです。

要点
-----
- Python パッケージとして設計され、モジュール単位でインポートして利用できます。
- 実運用（ExecutionEngine）とそれを監視する Monitoring（監視ループ）が含まれます。
- Paper Trading（ペーパートレード）モードをサポートし、本番 DB と分離して動作可能。
- DuckDB / SQLite をデータ層に利用。OpenAI を使ったニュース NLP / レジーム判定機能を備えます（オプション）。

プロジェクト概要
---------------
KabuSys は以下の主要責務を持ちます。

- ExecutionEngine: ブローカークライアント経由での発注管理、注文管理、リスク管理の実行。
- Monitoring: システム状態、注文ログ、リスク指標のポーリングと永続化、アラート/Kill Switch の判定。
- Portfolio construction: 候補選定、重み付け、ポジションサイズ計算、セクター制約などの純関数群。
- Research: DuckDB 上でファクタ計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）。
- AI モジュール: ニュースのセンチメントスコアリング（OpenAI）と市場レジーム判定。
- ツール: Paper Trading 検証レポート生成、設定ウィザード、設定検証スクリプト 等。

主な機能一覧
-------------
- 実行系
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に記録。
  - ブローカーファクトリ、OrderManager、RiskManager、Reconciler を組み合わせたエンジン。
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL で間隔を変更可能（デフォルト 60秒）。
  - MonitoringDB（SQLite）への system_status / trade_logs / risk_logs / positions / dashboard の永続化。
  - KillSwitch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）、RiskMonitor、TradeMonitor、AlertManager の統合。
- ポートフォリオ構築
  - 候補選定（select_candidates）、等ウェイト/スコア重み、position sizing（calc_position_sizes）、セクター制約、レジーム乗数。
- リサーチ
  - DuckDB 接続でファクター計算（calc_momentum/calc_volatility/calc_value）、将来リターン、IC 計算、要約統計など。
- AI
  - news_nlp.score_news: OpenAI を用いてニュース記事のセンチメントを銘柄毎に算出して ai_scores に書き込み。
  - regime_detector.score_regime: ETF の MA とマクロニュース NLP を合成して市場レジーム（bull/neutral/bear）判定・保存。
- ツール
  - config_setup.py: 対話式ウィザードで .env を生成/更新。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI。
  - tools.paper_verification_report: Paper Trading DB から検証レポートを生成。

必須 / 主要環境変数（概要）
---------------------------
（詳しい説明・デフォルトは config.py / config_setup.py を参照してください）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要（任意・デフォルトあり）
- KABUSYS_ENV — execution モード (development / paper_trading / live)。デフォルト development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...。デフォルト INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必要）
- PAPER_FILL_MODE — Paper Trading の fill 動作（instant/partial/never/reject）

自動 .env 読み込み
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基に .env, .env.local を自動読み込みします。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必要な Python パッケージ（代表）
--------------------------------
- duckdb
- psutil
- openai  （AI 機能を使う場合）
- PyYAML （config/*.yaml 検証を行う場合に任意）
- 標準ライブラリ: sqlite3, logging, threading, argparse 等

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を準備
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -r requirements.txt
     （requirements.txt が存在しない場合は少なくとも duckdb, psutil をインストールしてください）
   - OpenAI を使う場合: pip install openai

3. .env ファイルを作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成。config_setup.py の出力フォーマットを参照してください。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

5. データディレクトリ・DB の初期化
   - 通常はアプリ起動時に必要なファイル・テーブルは自動作成されます（logs/ や data/ 等）。
   - DuckDB / SQLite のデフォルトパス:
     - data/kabusys.duckdb
     - data/monitoring.db
     - data/paper_trading.db（paper_trading モード）

使い方（代表例）
----------------

- ExecutionEngine を起動する（本番・ペーパー共通）
  - python -m kabusys.run_execution
  - 起動時に Settings が KABUSYS_ENV を参照し、paper_trading の場合は paper_sqlite_path を使用して DB を分離します。
  - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
  - 実行中は data/execution.pid（デフォルト）に PID を書きます。

- Monitoring を起動する
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
  - 監視は本番の sqlite_path を常に参照（環境にかかわらず monitoring は production sqlite_path を使用する設計になっています）。
  - 監視ループ停止: data/stop_requested.flag を作成する（監視側はこれを検出して終了）。

- 設定ウィザードと検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数: PAPER_TRADING_SQLITE_PATH を使って DB を指定可能

- AI 機能（例: ニューススコア）
  - Python から直接呼び出し:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="...")

停止・Kill フロー
-----------------
- 緊急停止（ExecutionEngine 停止）:
  - KillSwitch は RiskMonitor 等から条件が満たされたときに data/kill.flag を書き込みます。ExecutionEngine は kill.flag を検知して停止するような実装（Execution 側の実装に依存）になっています。
- 優雅な終了（監視・実行スクリプト共通）:
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検出して終了します。
  - run_execution は起動時に kill flag を検出して起動を抑止します（安全機構）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / Settings 管理（自動 .env ロード含む）
- config_setup.py               — .env 対話式ウィザード
- validate_config.py            — 設定検証 CLI
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト

サブパッケージ
- ai/
  - news_nlp.py                  — ニュースセンチメント（OpenAI）と ai_scores 書き込み
  - regime_detector.py           — 市場レジーム判定（MA + マクロ NLP）
- monitoring/
  - monitoring_db.py             — SQLite 永続化層（テーブル作成・CRUD）
  - monitoring_engine.py         — 監視エンジン（複数 Monitor の束ね）
  - system_monitor.py            — システム状態チェック（CPU/メモリ/データ鮮度等）
  - risk_monitor.py              — ドローダウン / ポジション上限監視
  - kill_switch.py               — kill.flag 書き込みユーティリティ
  - trade_monitor.py             — (注文系の監視ロジック、該当ファイル参照)
  - alert_manager.py             — (LINE など通知管理、該当ファイル参照)
- execution/
  - broker_factory.py            — ブローカークライアント生成
  - execution_engine.py          — 実行エンジン本体
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py         — 候補選定・スコア基準
  - position_sizing.py           — 株数決定・資金配分ロジック
  - risk_adjustment.py           — セクター上限・レジーム乗数
- research/
  - factor_research.py           — ファクター計算（momentum/volatility/value）
  - feature_exploration.py       — 将来リターン・IC・統計関数
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - logging_setup.py             — ログ初期化ヘルパ
  - process_priority.py          — プロセス優先度・CPU affinity

補足 / 運用上の注意
-------------------
- 本プロジェクトは実取引を想定する設計要素を含むため、本番（KABUSYS_ENV=live）での設定は慎重に行ってください。validate_config は本番ガードの警告を出します。
- OpenAI API を利用する機能はキーの設定と利用料が必要です。失敗時はフェイルセーフ（スコア=0 等）で続行する実装が多いですが、実運用での挙動は事前に確認してください。
- .env は決してバージョン管理にコミットしないでください（config_setup.py のヘッダにも注意喚起があります）。
- ログはデフォルト logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR 環境変数で変更可能です。

貢献 / 開発
------------
- ローカル開発では KABUSYS_ENV=development を使用すると本番 API 呼び出しを避けられる設計になっています（ただし一部実装によりモック設定が必要）。
- テストや CI で自動読み込みを防ぎたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからテストしてください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ にて管理（現在: 0.1.0）。  
- ライセンス情報や詳細な設計ドキュメントはリポジトリの別ファイル（例: docs/）にまとめることを推奨します。

---
この README はソースコード（src/kabusys/*.py）を参照して作成しています。実行前に必ず .env の設定と validate_config によるチェックを推奨します。必要であれば README に含めるサンプル .env や systemd / supervisor 用の起動例を追加できます。希望があれば追記します。