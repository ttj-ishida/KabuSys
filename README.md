KabuSys — 日本株自動売買システム
================================

本文書はリポジトリ内の主要モジュールに基づく README です。開発用/運用用の簡易ガイド、環境変数、実行方法、ディレクトリ構成を日本語でまとめています。

プロジェクト概要
----------------
KabuSys は日本株の自動売買（シグナル生成 → ポートフォリオ構築 → 発注）を目的としたモジュール群と、運用監視・検証ツールを含むコードベースです。主要な特徴は次のとおりです。

- Execution Engine（発注エンジン）: リスク管理、オーダー管理、ブローカークライアント抽象化を備えています。  
- Monitoring（監視）: システム稼働状況、データ鮮度、注文ログ・リスク監視、Kill Switch による自動停止指示など。  
- Portfolio モジュール: 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム補正などの純粋関数群。  
- Research / AI: DuckDB を用いたファクター計算・特徴量探索、OpenAI を用いたニュース NLP（センチメント）と市場レジーム判定。  
- 運用支援ツール: 設定ウィザード (.env 生成)、設定検証 CLI、Paper Trading 検証レポート生成など。

機能一覧
--------
- 環境設定ウィザード（kabusys.config_setup）で .env を対話生成  
- 起動前の設定検証（kabusys.validate_config）  
- ExecutionEngine（本番 / ペーパートレード切替対応）起動スクリプト run_execution.py  
- Monitoring（SystemMonitor, TradeMonitor, RiskMonitor）ポーリング／通知／Kill Switch 実装、run_monitoring.py 起動スクリプト  
- DuckDB/SQLite を用いたデータ格納・分析（prices_daily, raw_financials, ai_scores 等を想定）  
- AI モジュール（news_nlp, regime_detector）による LLM ベースのセンチメント評価（OpenAI）  
- Paper Trading 向け検証レポート（kabusys.tools.paper_verification_report）  
- ロギング整備（コンソール + 日次ローテートファイル）

前提・依存
---------
（実際の pyproject.toml / requirements.txt を参照してください。代表的な依存ライブラリ）
- Python 3.8+
- duckdb
- psutil
- openai
- sqlite3（標準ライブラリ）
- 追加：PyYAML（config 検証で存在すれば YAML のパース検証を行う）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は duckdb, psutil, openai 等を個別にインストール）

3. .env の初期作成（推奨）
   - python -m kabusys.config_setup
     - 対話形式で .env を作成 / 更新します。
     - 生成後は .env を絶対に git にコミットしないでください（API トークン等が含まれます）。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。

5. データディレクトリの作成（必要に応じて）
   - デフォルト DB / ログ格納先（例）:
     - data/ (monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid など)
     - logs/ (アプリケーションログ)
   - run_* スクリプトは起動時に自動で DB スキーマを作成します（SQLite 用 init）。

実行方法（主要コマンド）
-----------------------
- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します（本番 DB とは分離）。

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション例: --from 2026-04-01 --to 2026-04-11 --db path/to/paper_trading.db

- AI モジュール呼び出し（プログラム内 API）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=...) など
  - OpenAI API キーは環境変数 OPENAI_API_KEY を使用（関数引数で上書き可能）。

環境変数一覧（主要）
-------------------
以下は本コードで参照される主要な環境変数と説明（デフォルト値がある場合は併記）。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時に必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR — ログディレクトリ（デフォルト: logs/）
- PID_FILE_PATH — Execution の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用 flag（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動削除するか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒。run_monitoring のオーバーライド）

起動 / 停止制御
----------------
- stop_requested.flag（data/stop_requested.flag）:
  - run_execution / run_monitoring スクリプトはこのファイルを監視しています。ファイルが存在するとループを抜けて終了します（手動停止用フラグ）。
- kill.flag:
  - KillSwitch が条件を満たした場合に data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る（Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていれば自動クリア）。
- execution.pid:
  - ExecutionEngine 起動時に PID を書き込む想定（既定: data/execution.pid）。

ログ
----
- ログは stdout と日次ローテートされたファイルログ（logs/<app_name>.log）へ出力されます。
- setup_logging(app_name="execution") のように各プロセスから呼び出されます。
- LOG_DIR 環境変数でログ保存先を変更できます。

セキュリティ注意
--------------
- .env に API トークンやパスワードを保存しますが、.env を Git にコミットしないでください。
- OpenAI やブローカー API のキーは必要に応じて環境変数や安全なシークレット管理を用いてください。

ディレクトリ構成（主要ファイル）
------------------------------
以下は主要モジュールの抜粋的構成（src/kabusys 配下）。実際のファイル数はさらに存在します。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings
  - config_setup.py             — .env 作成ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py          — ログ設定ユーティリティ
    - process_priority.py       — プロセス優先度 / affinity
  - monitoring/
    - monitoring_db.py          — SQLite テーブル初期化 / 永続化 API
    - system_monitor.py         — システム・プロセス・データ鮮度監視
    - risk_monitor.py           — ドローダウン・ポジション監視
    - monitoring_engine.py      — 各 Monitor を束ねるエンジン
    - kill_switch.py            — kill.flag 書き込みロジック
    - (trade_monitor.py, alert_manager.py など別ファイルあり)
  - execution/                   — ExecutionEngine と注文管理（発注ロジック）
    - (OrderManager, OrderRepository, Reconciler, RiskManager, broker_factory, execution_engine など)
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 株数計算・リスク制限
    - risk_adjustment.py        — セクター上限・レジーム乗数
  - research/
    - factor_research.py        — モメンタム/バリュー/ボラティリティ計算（DuckDB）
    - feature_exploration.py    — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py               — ニュースを LLM に流して銘柄ごとのスコアを生成
    - regime_detector.py        — マクロニュース + ETF MA で市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

開発メモ / よくある質問
-----------------------
- Paper Trading と Live は DB を分離（PAPER_TRADING_SQLITE_PATH を使う）しており、本番の monitoring DB を汚さない設計になっています。  
- Monitoring はデフォルトで production の sqlite_path を使用します（監視は常に本番 DB を参照する想定）。  
- AI 呼び出し（OpenAI）では 429・タイムアウト・5xx に対して指数バックオフでリトライします。API キーがないと実行時エラーになるため、テスト時はモック化を推奨します。  
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を検出して行います。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス / 責務
-----------------
本 README はコードベースの説明を目的としています。実運用の前に config/*.yaml や各モジュールの実装（ブローカーの実装・リスク設定）を十分に確認してください。実運用による損失については適切な責任分配・検証が必要です。

補足 / 参考コマンド例
--------------------
- ローカルで監視を1回だけ動かしてみる（テスト用）:
  - Python REPL などで MonitoringEngine を組み立てて .run_once() を呼ぶことが可能（ユニットテスト向け API が用意されています）。
- Paper レポート（一例）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。運用時の細かい設定や依存関係はプロジェクトの pyproject.toml / requirements.txt を参照し、必要に応じて本 README を補完してください。