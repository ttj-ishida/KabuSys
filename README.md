README
======

概要
----
KabuSys は日本株向けの自動売買プラットフォーム（プロトタイプ）です。本リポジトリは以下の主要機能を提供します:

- 発注エンジン（ExecutionEngine） — 実口座 / ペーパートレードの両対応
- 監視サブシステム（Monitoring） — システム状態・注文・リスクの定期チェックと Kill Switch
- ポートフォリオ構築（選定・重み付け・株数決定）
- 研究用モジュール（ファクター計算・特徴量評価）
- AI 支援モジュール（ニュースの NLP によるセンチメント評価 / レジーム判定）
- 運用ユーティリティ（.env ウィザード、設定検証、ペーパートレード検証レポート等）

特徴
----
- 設定は .env / 環境変数ベース。Settings クラスで一元管理。
- Live / Paper Trading / Development の実行モード切替（KABUSYS_ENV）。
- ペーパートレードは本番 DB から分離（PAPER_TRADING_SQLITE_PATH）。
- DuckDB を用いたリサーチ用データ処理（prices_daily / raw_financials 等）。
- OpenAI（gpt-4o-mini 相当）を用いたニュース NLP とレジーム判定（API キー必須）。
- ログはコンソール（stdout）と日次ローテートファイル両方に出力（logs/*.log）。
- Stop / Kill フラグ（data/stop_requested.flag, data/kill.flag）で外部からセッション停止可能。

セットアップ
----------
前提:
- Python 3.10+（typing|match 機能を使う箇所に依存）
- 必要なパッケージ: duckdb, psutil, openai, (PyYAML は config 検証時に必要)
  ※ requirements.txt がある場合はそちらを使用してください。

1. リポジトリルートに移動
   - パッケージは src/ 配下に配置されています。CWD に依存しない設計ですが、通常はプロジェクトルートで作業します。

2. 仮想環境作成 & パッケージインストール
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
   - pip install -r requirements.txt
     （requirements.txt がない場合は最低限 duckdb, psutil, openai をインストールしてください）

3. .env の準備（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくはプロジェクトルートに .env を手動で作成
   主要環境変数（例・必須）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY — AI 機能を使う場合に必須
     - LOG_LEVEL — デフォルト: INFO

4. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

5. ログ / データディレクトリ
   - デフォルトのログディレクトリ: logs/
   - データ・フラグ類は data/ 以下に作成されます（例: data/monitoring.db, data/stop_requested.flag）

使い方
------
主な実行エントリポイント:

- 監視プロセスを起動（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は Settings の sqlite_path（監視 DB）を使用します（環境にかかわらず本番 sqlite_path を参照）

- 発注/実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します
  - 実行中に data/stop_requested.flag を作成するとエンジンに停止指示を送ります

- .env の対話式セットアップ
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（モジュールとして利用）
  - ニュース NLP スコア付与: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...)）を受け取り、DB のテーブル（raw_news / prices_daily 等）を参照します
  - OpenAI API を使用するため、OPENAI_API_KEY を環境変数で設定するか、関数呼び出し時に api_key を渡してください

運用上の注意
-------------
- 本番 KABUSYS_ENV=live の際は LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の値を注意深く設定してください。
- 設定検証スクリプトで live のガードチェックを行います。必ず validate_config を実行して問題ないか確認してください。
- Kill Switch（data/kill.flag）を書き込むと ExecutionEngine に停止シグナルを送れます。
- プロセス優先度設定: 起動スクリプトは set_process_priority("high") を最初に呼びます（psutil を通じて OS に依存した設定を行います）。権限がない場合は警告が出ますが継続します。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py                       — パッケージ定義（__version__ 等）
- config.py                         — 環境変数 / Settings クラス、自動 .env ロード機構
- config_setup.py                   — .env 対話式ウィザード
- validate_config.py                — 起動前の設定検証 CLI
- run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                  — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py                      — ニュース記事の NLP スコアリング（OpenAI）
  - regime_detector.py               — 市場レジーム判定（MA + マクロ NLP）
- monitoring/
  - monitoring_db.py                 — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py                — システム監視（CPU/メモリ/ディスク・データ鮮度・プロセス監視）
  - trade_monitor.py                 — 注文関連の監視（滞留注文や約定異常）※（実装ファイルあり）
  - risk_monitor.py                  — ドローダウン・ポジション数監視
  - kill_switch.py                   — Kill Switch 書込みロジック
  - alert_manager.py                 — 通知管理（LINE 等へ通知）※（実装ファイルあり）
  - monitoring_engine.py             — 各 Monitor を束ねるループ実行器
- execution/
  - execution_engine.py              — 発注セッション管理（Engine）
  - broker_factory.py                — BrokerClient の生成（実ブローカ / モック）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注・リスク周り
- portfolio/
  - portfolio_builder.py             — 候補選定・重み付け
  - position_sizing.py               — 株数決定（リスクベース / 等配分 等）
  - risk_adjustment.py               — セクターキャップ・レジーム乗数
- research/
  - factor_research.py               — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py           — 将来リターン計算、IC、統計サマリ
- tools/
  - paper_verification_report.py     — Paper Trading の運用検証レポート生成
- utils/
  - logging_setup.py                 — 共通ログ設定ユーティリティ
  - process_priority.py              — プロセス優先度・CPU affinity ユーティリティ
  - その他ユーティリティ

設定例 (.env の抜粋)
--------------------
# --- システム ---
KABUSYS_ENV=development
LOG_LEVEL=INFO

# --- API ---
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# --- DB ---
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# --- OpenAI (AI 機能を使う場合) ---
OPENAI_API_KEY=sk-...

よくある質問 / トラブルシューティング
-------------------------------------
- Q: .env を自動で読み込まないようにできますか?
  - A: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します（主にテスト用）。

- Q: 監視ループの間隔を変更したい
  - A: MONITOR_POLL_INTERVAL 環境変数（秒）で上書きできます。0 以下や不正値は無視されデフォルト 60 秒が使われます。

- Q: Paper Trading と本番 DB を混同しないようにできますか?
  - A: はい。KABUSYS_ENV=paper_trading の場合、run_execution は paper_sqlite_path を使用し本番 DB と分離します。

- Q: OpenAI API エラーが出る/レスポンスが不安定
  - A: news_nlp / regime_detector は一部リトライやフェイルセーフを実装していますが、API キーやネットワーク、レート制限を確認してください。API キーは OPENAI_API_KEY を設定してください。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンスやコントリビューション方針はリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

補足
----
この README はコードベース（src/kabusys/*.py）から抜粋された仕様に基づいています。実運用前には必ず python -m kabusys.validate_config を実行し、.env の内容を確認してください。