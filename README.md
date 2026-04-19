KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株向けの自動売買システム用ライブラリ / 起動スクリプト群を含みます。  
主に発注実行エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ（ファクター計算）、
および AI を用いたニュース評価やレジーム検出などの機能を提供します。

概要
----
- Python パッケージとして設計されており、各種 CLI / モジュールが `python -m kabusys.<module>` で起動できます。
- 発注は本番（kabuステーション）とペーパートレード（MockBrokerClient）を切り替え可能。
- 監視コンポーネントはシステム健全性、注文ログ、リスク（ドローダウン・ポジション上限）を監視し、
  必要に応じて Kill Switch（停止フラグ）を発行します。
- DuckDB / SQLite をデータバックエンドとして使用。AI モジュールは OpenAI API（例: gpt-4o-mini）と連携可能。

主な機能一覧
-------------
- 起動スクリプト
  - run_execution: 発注実行エンジンを起動（KABUSYS_ENV により paper_trading / live を切替）
  - run_monitoring: 監視用ポーリングループを起動
- 設定管理 / ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 環境変数や config/*.yaml を事前検証する CLI
- モニタリング
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・実行プロセス監視
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション数監視
  - KillSwitch: 条件により停止フラグを書き込み ExecutionEngine を停止
  - MonitoringDB: SQLite に監視ログ / トレードログ / リスクログ / ダッシュボードを永続化
- ポートフォリオ構築
  - 候補選定、重み計算（等金額・スコア加重）、セクターキャップ適用、ポジションサイズ計算など
- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリなど
- AI（任意）
  - news_nlp: ニュース記事を集約して LLM でセンチメント評価し ai_scores に書き込み
  - regime_detector: ETF MA とマクロニュースを組み合わせて市場レジーム判定

セットアップ手順
----------------
1. リポジトリを取得
   - git clone ... （適宜）

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須ライブラリ例（環境によって追加・調整してください）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - pyyaml（validate_config の YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

4. 環境変数の準備（.env）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 必須となる主要項目:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV （development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使用する場合）
     - LOG_LEVEL（デフォルト: INFO）
     - KILL_FLAG_CLEAR_ON_START（0/1、デフォルト: 0。本番では 0 推奨）
   - 例（最小）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_kabu_password_here

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。

使い方（主要コマンド）
--------------------
- 発注エンジンを起動
  - python -m kabusys.run_execution
  - 挙動:
    - プロセス優先度を "high" に設定し、SQLite / DuckDB に接続します。
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
    - 起動前に data/stop_requested.flag が存在する場合は起動を中止します。
    - 実行中は data/execution.pid に PID を書きます（設定により変更可能）。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト: 60）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用します（環境に依存せず監視 DB は本番 DB を参照）。

- .env の対話式作成/更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

注意事項・運用メモ
-----------------
- Paper Trading と本番の DB は分離されています（paper_trading は settings.paper_sqlite_path を使用）。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリが作成できない場合はコンソール出力のみ）。
- Kill Switch:
  - 条件（例: ドローダウン閾値超過、ポジション上限超過）で data/kill.flag を作成すると ExecutionEngine に停止要求を送れます。
  - ExecutionEngine は起動時に kill.flag の自動クリアを制御する KILL_FLAG_CLEAR_ON_START を参照します（0/1）。
- 起動停止フラグ:
  - run_monitoring / run_execution はプロジェクトルートの data/stop_requested.flag を監視し、存在すればループを終了します。
- MONITOR_POLL_INTERVAL は 1 秒以上の正の整数を設定してください。無効値を与えるとデフォルト（60 秒）にフォールバックします。
- PAPER_FILL_MODE（paper_trading の MockBroker の振る舞い）: instant | partial | never | reject

主要な環境変数（概要）
--------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- データパス:
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- ログ:
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)、LOG_DIR（ログ出力先）
- AI:
  - OPENAI_API_KEY（AI 機能を使う場合）
- 監視:
  - KILL_FLAG_PATH（data/kill.flag デフォルト）、KILL_FLAG_CLEAR_ON_START（0/1）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔）

ディレクトリ構成（抜粋）
---------------------
プロジェクトの主要モジュールとファイル例（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 自動読み込み / Settings クラス
  - config_setup.py                — .env 作成ウィザード（CLI）
  - validate_config.py             — 起動前設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py                   — ニュース NLP スコアリング
    - regime_detector.py            — 市場レジーム判定
  - monitoring/
    - monitoring_db.py              — SQLite 永続化層
    - system_monitor.py             — システム監視
    - risk_monitor.py               — ドローダウン・ポジション監視
    - trade_monitor.py              — （注文監視：コード上存在）
    - monitoring_engine.py          — モニタリングの統合実行器
    - kill_switch.py                — kill.flag 管理
    - alert_manager.py              — （アラート送信管理：コード上存在）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py              — ルートロガー設定ユーティリティ
    - process_priority.py           — プロセス優先度・CPU affinity 設定ユーティリティ

（注）上記は本 README に含まれるコード抜粋を元にした主要ファイル一覧です。実際のリポジトリではさらに多くのファイルやサブモジュールが存在する可能性があります。

開発・デバッグのヒント
--------------------
- ログレベルを DEBUG にして詳細ログを出力できます:
  - LOG_LEVEL=DEBUG python -m kabusys.run_execution
- validate_config を使って環境設定の欠落や一般的な落とし穴を事前に検出してください。
- AI モジュールを利用する場合は OPENAI_API_KEY を必ず設定し、API レートやコストに注意してください。
- Paper Trading を試す場合は KABUSYS_ENV=paper_trading を設定し、PAPER_TRADING_SQLITE_PATH を別ファイルにして本番 DB と完全に分離してください。

ライセンス・貢献
----------------
- リポジトリにライセンスファイルが含まれている場合はそれに従ってください。  
- バグ報告・改善提案は issue を立ててください。

質問や追加したいドキュメント（例: デプロイ手順、systemd ユニット例、環境ごとの運用指針）があれば教えてください。README を拡張して具体的な運用手順や例を追加します。