README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームです。  
主な機能は取引実行（ExecutionEngine）、システム監視（Monitoring）、ポートフォリオ構築、ファクター計算・研究、AI を用いたニュースセンチメント評価などです。  
内部ストレージに SQLite（監視・発注ログ等）と DuckDB（時系列・研究用途）を利用します。モジュールはコマンドラインからモジュール単位で起動・実行できます。

特徴
----
- ExecutionEngine：本番 / ペーパートレードを環境で切り替え可能（ペーパートレードは専用 DB に完全分離）
- Monitoring：プロセス稼働状況・データ鮮度・注文ログを定期監視し、Kill Switch による強制停止やリスクログ記録
- ポートフォリオ構築：候補選定、重み付け、ポジションサイズ算出（等金額・スコア加重・リスクベース）
- リスク管理：ドローダウン監視・ポジション上限監視・リスクイベントのデデュプリケーション
- 研究（research）：DuckDB を使ったファクター計算（Momentum, Value, Volatility 等）・将来リターンや IC の算出
- AI モジュール：OpenAI を用いたニュースセンチメント（ai.news_nlp）・市場レジーム判定（ai.regime_detector）
- ツール：ペーパートレード検証レポート生成スクリプトなど
- 設定ウィザード（config_setup）と事前検証ツール（validate_config）
- 統一的なログ設定（logs/<app>.log 日次ローテーション）

前提条件
--------
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能使用時）
  - PyYAML（config 検証を厳密に行う場合）
- ネットワークアクセス（kabuAPI / J-Quants / OpenAI を使う構成の場合）
- .env に機密情報（API キー等）を配置することを推奨

セットアップ
-----------
1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成し依存パッケージをインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -r requirements.txt  （requirements.txt がある場合）
3. 初期設定 (.env) を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または .env ファイルを手動作成（下記参照）
4. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit 1）

主要な環境変数（.env）
---------------------
自動読み込み:
- プロジェクトルートにある .env、.env.local が自動ロードされます（OS 環境変数を上書きしない挙動）。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須 / 代表的な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を利用する機能で必要
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

DB / ファイルパス（デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db （KABUSYS_ENV=paper_trading 時に使用）
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag

その他
- PAPER_FILL_MODE: paper_trading の MockBroker 挙動（instant | partial | never | reject、デフォルト instant）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

実行方法
--------
基本的にモジュールを -m で実行します。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - 監視モジュールは本番 sqlite_path を参照（環境に依らず同一 DB を使用する設計）。
    - 停止はプロジェクトルート/data/stop_requested.flag を作成（stop フラグ）することで検知。

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
    - 起動時に data/execution.pid に PID を書きます。停止は data/stop_requested.flag 作成で検知します。
    - 起動時に Kill Flag (data/kill.flag) が既に存在する場合は起動しない挙動あり。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）

ログ
---
- ログはデフォルトで logs/ ディレクトリに出力されます（app_name ごとにログファイル: logs/execution.log, logs/monitoring.log 等）。
- ログはコンソール出力（stdout）および TimedRotatingFileHandler（日次、30 世代保持）に出力されます。
- LOG_DIR を設定してログ出力先を変更できます。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続します。

データ / 制御ファイル
--------------------
- data/monitoring.db（デフォルト SQLITE_PATH）
- data/paper_trading.db（ペーパートレード用）
- data/kabusys.duckdb（DuckDB）
- data/execution.pid（Execution エンジンの PID）
- data/stop_requested.flag（run_* スクリプトの停止フラグ）
- data/kill.flag（Kill Switch による停止要求）

AI 機能について
---------------
- ai.news_nlp / ai.regime_detector は OpenAI を利用します。OPENAI_API_KEY の設定が必要です。
- API 呼び出しはレート制限・ネットワークエラー等に対してリトライとフォールバック処理を備えています（失敗時は安全側のデフォルトで続行）。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 以下の主要構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み / Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py        — 共通ログ設定
    - process_priority.py     — プロセス優先度 / CPU affinity
  - execution/                — 発注エンジン関連（broker, engine, order_manager など）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, risk_logs, positions, dashboard）
    - system_monitor.py       — システム・データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション数監視
    - trade_monitor.py        — 注文滞留 / 約定異常監視（存在）
    - monitoring_engine.py    — 各 Monitor を束ねる
    - kill_switch.py          — kill.flag の管理
    - alert_manager.py        — 通知管理（存在）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 株数計算・キャップ処理
    - risk_adjustment.py      — セクター上限・レジーム乗数
  - research/
    - factor_research.py      — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py  — 将来リターン・IC 計算 / 統計
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — マクロ + MA200 に基づくレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

開発者向けメモ / 注意点
----------------------
- .env / .env.local はプロジェクトルート（.git や pyproject.toml を基準に自動検出）から読み込みます。パッケージ配布後も cwd に依存せず動作するよう設計されています。
- デフォルトで .env の自動読み込みが有効です。テストなどで自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ペーパートレードは production DB に書き込まないよう意図的に分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 系機能は API の応答や JSON パースに対して堅牢性を持たせており、失敗時は例外を上位に投げずフォールバック（0.0 等）する実装がメインです。

よくある操作例
--------------
- .env を対話式で作る:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- 監視を 30 秒間隔で起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート（2026-04-01〜2026-04-11）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
（プロジェクトのライセンス情報や貢献ルールをここに記載してください）

以上。README に不足している点や特定のモジュールの詳細ドキュメントが必要であれば教えてください。必要に応じてサンプル .env テンプレートや起動ユースケースごとの手順（本番/ペーパー切替等）を追記します。