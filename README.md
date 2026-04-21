README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤を想定した Python パッケージです。  
主要機能には注文実行エンジン、監視（Monitoring）、ポートフォリオ構築ユーティリティ、ファクター計算・研究ツール、OpenAI を用いたニュース NLP / レジーム判定などが含まれます。

特徴
----
- ExecutionEngine（発注エンジン）と Monitoring（監視ループ）を独立して起動可能
- Paper Trading モード（本番 DB と完全分離）をサポート
- DuckDB を用いた分析用データ格納 / クエリ
- SQLite を用いた監視ログ（system_status / trade_logs / positions / risk_logs / dashboard）
- OpenAI を利用したニュースセンチメント（ai.news_nlp）や市場レジーム判定（ai.regime_detector）
- 設定ウィザード（.env 生成）と起動前検証 CLI（設定検証）
- ロギング設定ユーティリティ、プロセス優先度設定ユーティリティ等の共通ユーティリティ群
- Paper Trading の検証レポート生成ツール

必要条件
----
- Python 3.9+（コードは typing / modern standard を想定）
- 推奨パッケージ（最低限のセット）:
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - pyyaml (config ファイル検証を使う場合)
- （任意）仮想環境（venv / poetry 等）

セットアップ手順
----------------
1. リポジトリをクローン（省略）
2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - 実際のプロジェクトでは requirements.txt または poetry を使用してください
4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参照）
   - 自動ロード: プロジェクトルートに .env / .env.local があれば自動で読み込まれます
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにするには --strict を付与
6. データディレクトリの準備
   - デフォルトでは data/ 以下に DB ファイルやフラグファイルを作成します（必要に応じて .env でパスを変更）

主要環境変数（抜粋）
-------------------
必須
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

重要・動作に影響するもの
- KABUSYS_ENV: 実行環境 （development / paper_trading / live）
  - paper_trading: run_execution は paper_sqlite_path（デフォルト data/paper_trading.db）を使用
  - live: 本番モード（注意喚起メッセージや追加チェックが有効）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能（ai.news_nlp / ai.regime_detector）の API キー
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル保存ディレクトリ（既定 logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（"1" でクリア）

運用上のフラグ / ファイル
- data/stop_requested.flag: run_monitoring / run_execution が停止を検知するためのフラグ
- data/kill.flag（デフォルト）: KillSwitch が書き込むと ExecutionEngine が停止される（理由文字列を含む）
- data/execution.pid: ExecutionEngine の PID ファイル（デフォルト）

使い方（主要スクリプト）
------------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup
    - .env を対話的に作成・更新する

- 設定検証
  - python -m kabusys.validate_config [--strict]
    - 環境変数や config/*.yaml の存在／形式を検査

- Execution（発注エンジン）起動
  - python -m kabusys.run_execution
  - 振る舞い:
    - 起動直後にプロセス優先度を "high" に設定（set_process_priority）
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_sqlite_path に書き込む
    - 停止は data/stop_requested.flag の作成で指示可能

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 振る舞い:
    - プロセス優先度を "high" に設定
    - Monitoring は KABUSYS_ENV に関係なく sqlite_path（本番監視 DB）を使用する点に注意
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）
    - 停止は data/stop_requested.flag の作成で指示可能

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（ライブラリ API）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None) などでニューススコアを取得・書き込み（OPENAI_API_KEY が必要）

停止・Kill Switch
-----------------
- KillSwitch（kabusys.monitoring.kill_switch）は RiskMonitor 等の検知結果に基づき data/kill.flag を生成し ExecutionEngine の停止をトリガーします。
- 実行中プロセスを手動で停止するには data/stop_requested.flag を作成する（両スクリプトがこのフラグを監視します）。

ログ
---
- ログは標準出力（stdout）とファイル出力（logs/<app_name>.log 日次ローテート）に同時出力されます（kabusys.utils.logging_setup）。
- ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/ を使用。作成できない場合はコンソールのみ。

開発メモ
--------
- 設定の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を読み込みます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と本番 DB は明確に分離されます（run_execution が paper_trading を検出した場合）。
- 多くのモジュールは DuckDB 接続や sqlite3.Connection を引数で受け取り、サイドエフェクトを最小化しています（ユニットテストがしやすい設計）。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py
  - Settings クラス: 環境変数読み込み・検証
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前チェック CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 切替あり）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- utils/
  - logging_setup.py: ロギング初期化ユーティリティ
  - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py: SQLite のテーブル初期化・監視データアクセス層
  - system_monitor.py: システム状態・データ鮮度監視
  - trade_monitor.py: 発注ログ監視（該当コード群あり）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 管理
  - monitoring_engine.py: 各モニタを束ねるエンジン
  - alert_manager.py: アラート送信管理（LINE 等、実装部分）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など
  - ExecutionEngine のコア実装と注文管理ロジック

- portfolio/
  - portfolio_builder.py: 候補選定・スコア順ソートなど
  - position_sizing.py: 発注株数計算（単元丸め・aggregate cap 等）
  - risk_adjustment.py: セクター制限・レジーム乗数

- research/
  - factor_research.py: momentum/value/volatility 等のファクター計算
  - feature_exploration.py: 将来リターン・IC 計算・統計サマリ

- ai/
  - news_nlp.py: ニュースをまとめて OpenAI へ投げ、銘柄ごとにセンチメントを ai_scores へ書き込み
  - regime_detector.py: ETF MA200 とマクロニュースを使って市場レジーム判定

- tools/
  - paper_verification_report.py: Paper Trading 検証レポート生成スクリプト

ライセンス・貢献
----------------
（ここにプロジェクトのライセンスや貢献方法を記載してください）

付記（運用上の注意）
-------------------
- KABUSYS_ENV=live（本番）では kill/flag 設定や LINE 通知の有無など、運用リスクに注意して下さい。
- 実環境で稼働させる前に python -m kabusys.validate_config で設定検証を必ず行ってください。
- OpenAI を使う機能は API コストと応答の不確実性があるため、実運用ではリトライ設定やスロットリングを適切に設定してください（既存コードでバックオフ処理が実装されています）。

以上が簡易 README です。必要に応じて実行例、.env.example、requirements.txt、デプロイスクリプト等を追加してください。