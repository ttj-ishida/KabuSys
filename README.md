KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システム向けライブラリ群です。  
主な機能は以下の通りです。

- 発注・実行エンジン（ExecutionEngine）と監視プロセス（Monitoring）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）
- リスク監視（ドローダウン監視・ポジション上限監視）と Kill Switch
- 研究用モジュール（ファクター計算・特徴量探索）
- ニュース NLP を用いた銘柄センチメント評価（OpenAI）
- ペーパートレーディング用の分離 DB と検証ツール
- 共通ユーティリティ（ログ設定・プロセス優先度設定など）

主要機能一覧
--------------
- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV によって実際発注/ペーパーを切替）
  - paper_trading 環境では MockBrokerClient を用い、data/paper_trading.db を使用
- run_monitoring.py: SystemMonitor のポーリングループを起動（デフォルト 60 秒間隔）
  - 環境変数 MONITOR_POLL_INTERVAL で間隔変更可
- config_setup.py: .env を対話式で作成・更新するウィザード
- validate_config.py: 起動前チェック（必須環境変数 / config/*.yaml / DB パス等）
- monitoring/*: 監視関連（system_monitor, trade_monitor, risk_monitor, monitoring_engine, monitoring_db）
  - monitoring_db: SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- portfolio/*: 銘柄選定・重み・ポジションサイズ計算・セクター上限・レジーム乗数
- research/*: DuckDB を用いたファクター計算・将来リターン/IC 計算・特徴量サマリー
- ai/*: ニュース NLP（OpenAI）による銘柄センチメント付与、レジーム判定
- tools/paper_verification_report.py: ペーパートレーディングの検証レポート生成

前提 / 依存
------------
主な依存ライブラリ（必須/任意）:
- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml のパース検証を行う場合。ただし未インストールでも起動できる）

環境変数の自動読み込み:
- プロジェクトルートにある .env/.env.local が自動で読み込まれます（OS 環境変数が優先）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- LOG_LEVEL (例: INFO, DEBUG)
- LOG_DIR (ログ保存先、デフォルト: logs/)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒、デフォルト 60)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（Kill Switch / PID 管理）

セットアップ手順
----------------
1. 必要パッケージをインストール
   - 例: pip install -r requirements.txt
   - もしくは最低限: pip install duckdb psutil

2. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成します（.env は絶対に Git にコミットしないでください）

3. 設定検証（任意／推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

4. DB の初期化
   - run_execution/run_monitoring は起動時に必要な monitoring テーブル等を初期化します。
   - DuckDB ファイルは必要に応じて外部スクリプトやデータ取り込みで準備します。

使い方（コマンド例）
--------------------
- 実行エンジン起動（本番/ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 注意: 起動前に Kill Switch（data/kill.flag）が残っていると起動を拒否します。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアしますが、本番環境では推奨しません。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH を使用するか環境変数 PAPER_TRADING_SQLITE_PATH を設定

- AI / レジーム判定（ライブラリ的に呼ぶ）
  - ニュース NLP の呼び出し例（Python から直接呼ぶ）:
    - from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
      score_regime(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")

停止・Kill Switch
-----------------
- run_execution / run_monitoring はプロジェクト内 data/stop_requested.flag の存在を見て安全に停止します。停止させたい場合はこのファイルを作成してください（運用上の注意あり）。
- Kill Switch（自動停止）は risk_monitor の検出条件により data/kill.flag を書き込みます。ExecutionEngine は起動時/稼働中にこの kill.flag を検出して停止します。

ログ
----
- ログは stdout と logs/<app_name>.log（日次ローテーション）に出力されます。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で指定できます。
- ログディレクトリは LOG_DIR で上書き可能（デフォルト logs/）。

ディレクトリ構成（抜粋）
------------------------
以下は src/kabusys 以下の主要ファイル/ディレクトリ構成です（提供コードに基づく）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパー検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロNEWS + LLM）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - monitoring_engine.py   — 各 Monitor を束ねる Engine
    - system_monitor.py      — システム状態監視
    - risk_monitor.py        — ドローダウン / ポジション監視
    - kill_switch.py         — kill.flag 管理
    - trade_monitor.py       —（省略されたが trade 監視ロジックが入る想定）
    - alert_manager.py       —（アラート送信ロジック）
  - execution/
    - broker_factory.py      — ブローカークライアント生成（Mock / live 切替）
    - execution_engine.py    — 発注実行ロジック（Engine）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py
  - data/                    — 例: monitoring/paper DB、flag/pid ファイル等（ランタイム生成）

開発上の注意 / 運用上の注意
---------------------------
- .env は機密情報（API トークン等）を含むため絶対に VCS にコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では Kill Switch の設定や LINE 通知などを慎重に確認してください。validate_config.py は本番専用の追加警告を出します。
- OpenAI API を使う機能は API キーとコスト、レスポンスの検証に注意してください。AI 呼び出しはリトライやバリデーションを実装していますが、誤応答に対するロバスト性設計は必要です。
- ペーパートレーディングは本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH を使用）。

サンプル運用フロー
------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. 必要 DB を配置（DuckDB に過去価格等をロード）
4. 監視を起動（python -m kabusys.run_monitoring）
5. 実行エンジンを起動（python -m kabusys.run_execution）
6. 運用中、異常があれば monitoring が kill.flag を書き込み実行エンジンを停止する

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報は本リポジトリのトップレベルに従ってください（ここでは明示していません）。

補足
----
- この README は提供されたコードベースの主要点をまとめたものです。各モジュールの詳細な使用方法や公開 API（関数署名・返り値等）は該当ソース（src/kabusys/ 以下のファイル）を参照してください。
- 追加の CLI やスクリプトを用意する場合は、logging_setup と Settings を利用して一貫した挙動にすることを推奨します。

必要であれば、README にサンプル .env テンプレートや具体的な Python API 使用例（コードスニペット）を追加します。どの情報を補足しますか？