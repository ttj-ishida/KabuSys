KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。本リポジトリは信号生成・ポートフォリオ構築・発注実行・監視・レポート・研究ユーティリティを含むモジュール群を提供します。設計方針として「本番データベース・発注 API へ不要なアクセスを行わない」「テスト／ペーパー／本番環境を分離」「フェイルセーフ（API失敗や部分失敗はシステム全体を停止させない）」を重視しています。

主な機能
-------
- 環境設定ウィザード（.env 作成／更新）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の事前チェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番／ペーパー切替）: run_execution.py
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）へ記録
- 監視ループ（SystemMonitor ポーリング）: run_monitoring.py
  - ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
- 監視サブシステム
  - SystemMonitor: CPU/メモリ/Disk、Execution プロセス存在、データ鮮度の監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・保有上限監視、ダッシュボード更新
  - KillSwitch / AlertManager: 条件に応じた停止シグナル（kill.flag）と通知
- ポートフォリオ構築ユーティリティ（候補選定・重みづけ・ポジションサイジング・セクター制限）
- 研究用モジュール（DuckDB を用いたファクター計算・特徴量分析）
- AI モジュール（OpenAI を用いたニュースセンチメント / レジーム判定）
- Paper Trading 検証レポート生成スクリプト

前提（依存ライブラリ）
--------------------
少なくとも以下が必要です（バージョンは本リポジトリの要求に合わせてインストールしてください）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を有効にする場合）

pip でのインストール例（例示）:
pip install duckdb psutil openai PyYAML

環境変数（主なもの）
-------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading: 発注はモック化・専用 SQLite を使用
  - live: 実際に発注が行われるため注意が必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- PAPER_FILL_MODE — ペーパー発注のフィルモード: instant | partial | never | reject（デフォルト instant）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動 .env ロード
----------------
パッケージ起動時、プロジェクトルート（.git または pyproject.toml があるディレクトリ）が検出されると、
.env（次に .env.local）を自動で読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順
----------------
1. レポジトリをクローン / 取得
2. Python 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   pip install duckdb psutil openai PyYAML
4. .env を作成（推奨: ウィザードを使用）
   python -m kabusys.config_setup
   ウィザード実行後、.env が生成されます（絶対に Git にコミットしないでください）。
5. 設定検証（オプション）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

実行方法（主要コマンド）
----------------------
- ExecutionEngine を起動（本番 / ペーパーに応じて動作）
  python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録
  - 起動時に data/stop_requested.flag があれば起動せず終了
  - 実行中は同じ stop フラグを監視して停止する
  - 起動時にプロセス優先度を "high" に設定しようとします（権限により失敗することがありますが無害）

- Monitoring を起動（ポーリングループ）
  python -m kabusys.run_monitoring

  オプション:
  - 環境変数 MONITOR_POLL_INTERVAL=<秒> でポーリング間隔を設定（デフォルト 60 秒）
  挙動:
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず）
  - data/stop_requested.flag を検知すると監視ループを終了します

- 環境設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

AI / レジーム / ニューススコア
----------------------------
- OpenAI を使う機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。
- news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続を渡して実行します（モジュール API）。
- regime_detector.score_regime(conn, target_date, api_key=None) — 同様に実行。

監視・停止フロー
----------------
- stop_requested.flag:
  - run_monitoring.py と run_execution.py が参照する外部停止フラグファイル（data/stop_requested.flag）。
  - ファイルが存在すると run_monitoring は監視ループを抜け、run_execution は起動を回避または実行中に停止します。
- kill.flag:
  - KillSwitch（監視サブシステム）がリスク条件を満たした場合に data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります。
  - Settings.kill_flag_clear_on_start=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

監視 DB（SQLite）について
------------------------
初回起動時に監視用 DB（デフォルト data/monitoring.db）へ必要テーブルを作成します（冪等）。
主なテーブル:
- system_status: CPU/メモリ/Disk/プロセス状態の時系列
- trade_logs: 発注 / 約定イベントログ（latency_ms カラムあり）
- positions: 保有ポジション
- risk_logs: リスク・アラート履歴
- dashboard: ダッシュボード集計（id=1 の 1 行で保持）

ディレクトリ構成（主要ファイル）
------------------------------
プロジェクトの主要モジュール構成（src/kabusys を想定）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - execution/                — 発注系コンポーネント（Engine / OrderManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（プロジェクトルート）
- config/                     — YAML テンプレート（system_config.yaml 等）
- data/                       — デフォルト DB / フラグファイル配置（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag, data/execution.pid）

運用上の注意
-----------
- 本番（KABUSYS_ENV=live）での運用では、必ず .env を正しく設定し、LINE 通知設定等を確認してください。validate_config は本番チェックに有用です。
- kill.flag や stop_requested.flag の取り扱いには注意してください。特に KILL_FLAG_CLEAR_ON_START=1 は本番では危険です（自動クリアにより停止状態を見逃す可能性があります）。
- Process priority / CPU affinity の設定は OS 権限に依存します。設定失敗時は警告が出ますが処理は継続します。
- AI 機能（OpenAI）を使う場合、API 利用料やレート制限に注意してください。news_nlp ではレート制限や 5xx に対してリトライ実装がありますが、失敗時は安全にフォールバックします。

よく使うコマンドまとめ
---------------------
- .env 作成ウィザード:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config
- ExecutionEngine 起動:
  python -m kabusys.run_execution
- Monitoring 起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 拡張ポイント
-----------------------
- strategy / execution の詳細実装（ブローカーファクトリや Engine 内部）はこの README に含まれているモジュール群と連携して拡張できます。
- DuckDB を用いた研究・バックテスト（research/*）は外部ツールとの連携や追加ファクターの実装が容易です。
- AI モジュールは API 呼び出し抽象化を行っているため、テスト時は _call_openai_api をモックして検証できます。

ライセンス
----------
（ここにプロジェクトのライセンスを記載してください）

---
何か特定の機能（例: ExecutionEngine の起動オプション、AI モジュールのローカル実行例、またはディレクトリ構成の詳細なツリー出力）について README を拡張したい場合は教えてください。