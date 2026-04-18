KabuSys
=======

日本株自動売買システム（軽量プロトタイプ）用のリポジトリです。  
本READMEはコードベースの主要機能、セットアップ、起動方法、ディレクトリ構成を日本語でまとめたものです。

概要
----
KabuSys は日本株向けの自動売買フレームワークです。主な目的は以下です。

- 戦略のリサーチ（DuckDB を用いたファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 実行エンジン（本番 / ペーパートレードに対応した発注処理）
- 監視（システム状態・注文滞留・リスク監視）
- AI モジュール（ニュースのセンチメント評価、レジーム判定）
- 開発支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

主要な設計方針
- 本番 DB とペーパー用 DB を明確に分離（KABUSYS_ENV により切替）
- DuckDB を分析用に利用（prices_daily / raw_financials 等）
- OpenAI を利用した文字列処理は失敗時にフェイルセーフで継続
- ルックアヘッドバイアス回避（対象日ベースの処理、datetime.today() に依存しない実装）
- シンプルなファイルフラグによる停止制御（data/kill.flag 等）

機能一覧
--------
- 実行（ExecutionEngine）起動スクリプト（run_execution.py）
  - paper_trading 環境では MockBroker を使用し、data/paper_trading.db に記録
  - PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止
- 監視（Monitoring）起動スクリプト（run_monitoring.py）
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、プロセス生存チェックをポーリング
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視コンポーネント群
  - SystemMonitor: process の生存や DuckDB のデータ鮮度を検査
  - TradeMonitor: 注文滞留・約定価格の異常検出
  - RiskMonitor: ドローダウン・保有上限監視、ダッシュボード更新
  - KillSwitch: リスク条件により data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringDB: SQLite に対する永続化層（初期化・マイグレーション対応）
- ポートフォリオ構築
  - 候補選定 (select_candidates)
  - 等配分 / スコア重みの重み算出
  - ポジションサイズ計算（リスクベース、上限・lot 丸め、aggregate cap）
  - セクター上限適用、レジーム乗数
- リサーチ / 特徴量
  - ファクター計算（momentum/value/volatility）
  - 将来リターン、IC（スピアマン）計算、ファクター統計
- AI モジュール
  - news_nlp.score_news: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores に書込
  - regime_detector.score_regime: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定（bull/neutral/bear）を書込
- ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity 設定（psutil 利用）
  - .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート出力ツール（tools/paper_verification_report.py）

必要条件（推奨）
----------------
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 内容検証に必要だが任意）
- 標準ライブラリ: sqlite3 等

インストール例
-------------
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. ライブラリのインストール（最低限）
   - pip install duckdb psutil openai

   （PyYAML を使う場合）
   - pip install pyyaml

設定（.env）
-----------
プロジェクトルートに .env を配置するか、環境変数で設定します。リポジトリには .env.example を参考に .env を作成してください（.env は絶対に Git にコミットしないでください）。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution モード（development / paper_trading / live）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）

簡易的な .env の例
------------------
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

セットアップ手順（推奨）
---------------------
1. リポジトリをクローンして作業ディレクトリを移動
2. 必要パッケージをインストール（上記参照）
3. .env を作成（python -m kabusys.config_setup を実行すると対話式ウィザードで作成可）
4. 設定検証: python -m kabusys.validate_config
   - --strict を指定すると警告がある場合も exit(1) で失敗扱い
5. データディレクトリ（data/）を作成しておく（必要に応じてスクリプトが自動作成）

使い方
------

各種 CLI / モジュールの呼び出し方法:

- 実行エンジン（ExecutionEngine）起動（デフォルトで settings.env に従う）
  - python -m kabusys.run_execution
  - 注意: 起動時に data/stop_requested.flag が存在すると起動しません
  - 実行中は data/execution.pid に PID が書き込まれます
  - 停止は stop_requested.flag 作成または ExecutionEngine 側の stop 呼び出し

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は Settings で指定した sqlite_path（監視 DB）を使用（環境を問わず本番 sqlite_path を参照）

- .env ウィザード（対話形式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告やエラーを事前に検出できます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも可）

- AI モジュール（プログラム的利用）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key=None)
  - regime_detector.score_regime(duckdb_conn, target_date, api_key=None) を利用して市場レジーム判定可能

停止・Kill Switch
-----------------
- KillSwitch はリスク判定により data/kill.flag を作成します（存在すると ExecutionEngine 停止を誘導）
- data/stop_requested.flag は run_* スクリプトのループ停止用ファイルです（外部運用スクリプトから作成してプロセスを停止できます）
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアしますが、本番では推奨されません

監視 DB（SQLite）について
-------------------------
- monitoring_db.init_monitoring_db(conn) により必要なテーブルを冪等に作成します
- 起動時に簡単なマイグレーション（列追加）を試みます（例: trade_logs.latency_ms, dashboard.peak_value）
- MonitoringDB クラスがログ書込 API を提供します（system_status, trade_logs, positions, risk_logs, dashboard）

ディレクトリ構成
----------------
（src/kabusys をルートとして抜粋）

- src/kabusys/
  - __init__.py                       — パッケージ初期化、バージョン
  - config.py                         — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py                   — .env 作成ウィザード（対話式）
  - validate_config.py                — 設定検証 CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py    — Paper Trading 検証レポート生成スクリプト
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py              — レジーム判定（MA200 + マクロ NLP）
  - monitoring/
    - monitoring_db.py                — SQLite 永続化層（テーブル作成・DB API）
    - system_monitor.py               — システム状態監視
    - trade_monitor.py                — 注文滞留 / 約定異常監視
    - risk_monitor.py                 — ドローダウン・ポジション数監視
    - kill_switch.py                  — kill.flag 管理
    - monitoring_engine.py            — 各モニタの統合とポーリングロジック
    - alert_manager.py                — （未表示）アラート送信管理（LINE など）
  - execution/
    - order_repository.py, order_manager.py, execution_engine.py, ...（発注系コンポーネント）
  - portfolio/
    - portfolio_builder.py            — 候補選定・重み計算
    - position_sizing.py              — 株数決定・aggregate cap
    - risk_adjustment.py              — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py              — ファクター計算（momentum/value/volatility）
    - feature_exploration.py          — 将来リターン / IC / 統計サマリ
  - utils/
    - process_priority.py             — psutil による優先度 / affinity 制御
  - data/ (実行時に使用するローカルディレクトリ、バイナリファイル等)
    - monitoring.db, paper_trading.db, kabusys.duckdb, kill.flag, stop_requested.flag, execution.pid

開発・テストのヒント
--------------------
- .env の自動読み込みは default で有効。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- OpenAI を使うテストは API 呼び出し部分（_call_openai_api 等）をモックすると高速かつ安定します。
- DuckDB クエリは prices_daily テーブルなどを前提にしているため、テスト用の小さなデータセットを用意すると良いです。
- validate_config.py を先に実行して設定ミスを発見してください。

付記
----
- README は実装済みモジュールから導出しています。実運用する場合は各種設定（API キー、金額パラメータ、Kill Switch 設定等）を慎重に確認してください。
- 本リポジトリはプロダクション品質の取引システムではありません。実注文を行う前に十分なレビューとテストを行ってください。

必要であれば、各モジュールの使用例（簡単なコードスニペット）や systemd / supervisord での運用例、データベーススキーマの詳細説明なども追加で作成します。ご希望があれば教えてください。