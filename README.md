KabuSys — 日本株自動売買システム
================================

このリポジトリは、シンプルな日本株自動売買（ExecutionEngine）とそれを監視・運用するためのモジュール群をまとめたものです。  
README ではプロジェクト概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成を日本語で説明します。

プロジェクト概要
----------------
KabuSys は以下の責務を持つコンポーネント群で構成されます。

- ExecutionEngine：発注ロジック、リスク管理、注文管理を行うエンジン（本番 / ペーパートレード切替対応）
- Monitoring：システム稼働状況・注文状況・リスクを定期的にチェックし、アラートや Kill Switch（停止フラグ）を管理
- Portfolio：銘柄選定、重み付け、枚数計算などのポートフォリオ構築ロジック（純粋関数）
- Research：DuckDB 上の時系列データからファクター計算や特徴量解析を行うモジュール
- AI：OpenAI を利用したニュースセンチメントや市場レジーム判定（オプション）
- ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード、設定検証ツール等

主な特徴（機能一覧）
-------------------
- ExecutionEngine
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアント分離（paper_trading 時は Mock を使用）
  - リスクマネージャ（最大保有比率・利用率・ドローダウン等）
  - 発注管理・再整合（Reconciler / OrderManager）

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス稼働/データ鮮度の監視
  - TradeMonitor：注文の滞留・約定異常検出（trade_logs を参照）
  - RiskMonitor：ドローダウン・保有数上限監視、ダッシュボード更新
  - KillSwitch：リスク閾値到達で data/kill.flag を書き込み ExecutionEngine に停止シグナルを送出
  - MonitoringEngine：上記 Monitor をまとめてポーリング実行、AlertManager 経由で通知

- Data / Research
  - DuckDB でファクター計算（モメンタム・ボラティリティ・バリュー等）
  - ペーパートレード用検証レポート生成ツール（paper_verification_report）

- AI（オプション）
  - ニュースを OpenAI でスコアリングして ai_scores へ保存（score_news）
  - マクロ + ETF MA200 乖離から市場レジーム判定（score_regime）
  - API 呼び出しは冪等性・リトライ・クリップ等を考慮

- 開発支援ツール
  - config_setup.py：.env の対話式ウィザードで初期化
  - validate_config.py：起動前に環境変数・設定ファイルの検証
  - 共通ログ設定ユーティリティ（ログの stdout + 日次ファイルローテーション）

要求環境（依存）
----------------
以下のパッケージが最低限必要です（環境や機能により追加が必要）。

- Python 3.9+
- duckdb
- psutil
- openai （AI 機能を使うとき）
- PyYAML（config/*.yaml を検証したいとき。必須ではない）
- その他: 標準ライブラリのみで動作するモジュールも多数

（プロジェクトに requirements.txt が無い場合は手動でインストールしてください）
例:
  pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo>
   - cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
     → 対話で J-Quants トークンや KABU_API_PASSWORD などを設定します
     → 生成された .env は絶対に Git にコミットしないでください

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 本番前は --strict を付けて警告も FAIL として扱う: python -m kabusys.validate_config --strict

6. データディレクトリ作成
   - デフォルトでは data/ に DB やフラグファイルが置かれます。自動作成されますが、権限等に注意してください。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development / paper_trading / live、デフォルト: development)
  - paper_trading: MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と完全分離）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB。デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB。デフォルト: data/paper_trading.db)
- OPENAI_API_KEY (AI モジュール利用時に必要)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意、アラート通知用）
- LOG_LEVEL (DEBUG/INFO/…、デフォルト: INFO)
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒。run_monitoring ではデフォルト 60 秒）
- PAPER_FILL_MODE（paper_trading の約定動作: instant/partial/never/reject。デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START（本番での Kill Flag 自動クリアのフラグ。0 推奨）

起動・実行方法（使い方）
-----------------------

- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 実行はバックグラウンドでスレッドとして開始され、data/execution.pid に PID を出す設計です
  - 停止リクエスト: data/stop_requested.flag を作成すると起動中のプロセスは検知して停止します
  - KillSwitch は条件を満たすと data/kill.flag を書き込み ExecutionEngine が停止する仕組みです

- Monitoring を起動（ポーリングで各 Monitor を巡回）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - Monitoring の DB 接続は KABUSYS_ENV にかかわらず本番 sqlite_path を参照します（監視データは一元管理）

- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付与すると警告でも exit(1) になります

- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で指定するか、PAPER_TRADING_SQLITE_PATH 環境変数で指定

- AI モジュール（ニューススコア / レジーム判定）
  - 実行には OPENAI_API_KEY が必要
  - 関数を直接呼ぶ API ベース:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、ai_scores / market_regime 等のテーブルに書き込みます
  - OpenAI コールはリトライ・バックオフ・結果バリデーションを行いますが、API キーやコストに注意してください

運用メモ（特徴的な挙動）
---------------------
- Monitoring は実行環境にかかわらず sqlite_path（デフォルト data/monitoring.db）を使用します。
- ExecutionEngine は paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使い、本番 DB と分離します。
- 停止制御:
  - 手動停止要求: data/stop_requested.flag を作る
  - KillSwitch による停止: monitoring が条件を満たすと data/kill.flag を書き込む（ExecutionEngine は Settings.kill_flag_path を参照）
- ログ:
  - 共通の setup_logging により stdout と logs/<app_name>.log（日次ローテーション）へ出力します
  - ログディレクトリは LOG_DIR 環境変数、もしくはデフォルト logs/

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主なモジュールと役割の概観です（抜粋）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数・.env 自動ロード、Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト

  - execution/               — 実行エンジン関連（Engine, OrderManager, RiskManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続層（system_status, trade_logs, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC 計算等
  - ai/
    - news_nlp.py            — ニュースセンチメントスコア算出（OpenAI）
    - regime_detector.py     — 市場レジーム判定（ETF MA200 + マクロニュース）
  - tools/
    - paper_verification_report.py  — Paper Trading の検証レポート生成
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

注意事項 / ベストプラクティス
------------------------------
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します（自動で kill.flag を解除すると危険）。
- AI 機能は外部 API を呼ぶため、API キー管理とコスト制御に注意してください。
- DB ファイル（data フォルダ）はバックアップ・アクセス権に注意してください。
- 実行ユーザーが psutil による優先度変更や PID 書き込みを行う権限を持っている必要があります。

問い合わせ / 開発メモ
--------------------
- 小さなユーティリティや設計意図は各ソースファイルの docstring / コメントに記載しています。実装を拡張・修正する際はそちらも参照してください。
- テストを書く場合は Settings の自動 .env ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと便利です。

以上がこのコードベースの README 相当情報です。必要ならば README.md の具体的なテンプレート化（例 .env サンプルの埋め込み、コマンド一覧の表形式化など）を作成します。どの形式が良いか指示ください。