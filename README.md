# KabuSys

日本株自動売買システムの一部を構成する Python パッケージ。  
このリポジトリはデータ処理 / 研究（ファクター計算） / ポートフォリオ構築 / 実行エンジン / 監視 / AI（ニュース NLP・レジーム判定）等のモジュール群を含みます。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド・モジュール）
- 環境変数・設定のポイント
- ログ / フラグファイル
- ディレクトリ構成（主要ファイルの説明）

---

プロジェクト概要
- KabuSys は日本株の自動売買を想定したコンポーネント群です。  
  - DuckDB を使った時系列データ処理・ファクター計算（research）  
  - ポートフォリオ構築（選定・重み付け・サイズ計算）  
  - 実行エンジン（ExecutionEngine）とブローカークライアントの抽象化（paper_trading 時は Mock を使用）  
  - 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch（自動停止）  
  - ニュース NLP による銘柄センチメント評価（OpenAI を利用）と市場レジーム判定

機能一覧
- 環境設定ウィザード（config_setup）と設定検証ツール（validate_config）
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite に完全分離して記録
- 監視ループ起動スクリプト（run_monitoring）
  - MONITOR_POLL_INTERVAL によりポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は常に production 用 sqlite_path を参照（環境に依存しない）
- 監視コンポーネント
  - SystemMonitor: CPU/メモリ/Disk/プロセス生存・データ鮮度をチェック
  - TradeMonitor / RiskMonitor / MonitoringEngine: 注文滞留・約定異常・ドローダウンなどの監視とアラート判定
  - KillSwitch: 条件により data/kill.flag を書き込んで ExecutionEngine を停止させる
- ポートフォリオ関連ユーティリティ
  - 候補選定、重み計算、単元株丸め、セクターキャップ、レジーム乗数など
- 研究用モジュール（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、統計サマリー
- AI モジュール（news NLP / regime detector）
  - OpenAI を用いたニュースごとのセンチメントスコア算出（ai.news_nlp.score_news）
  - マクロ記事と ETF MA に基づく市場レジーム判定（ai.regime_detector.score_regime）
- ツール
  - Paper Trading 向け検証レポート生成スクリプト（tools.paper_verification_report）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <リポジトリ>
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - 本リポジトリに requirements.txt がある場合はそれを使用してください。無い場合の主要依存例:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（validate_config の YAML 検証に必要）
   - 例:
     - pip install duckdb psutil openai PyYAML
4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動でルートに .env を作成（.env.example を参照してください）
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY を設定
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱う

使い方（主要コマンド）
- 実行エンジンの起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）を使用
    - 起動前に data/stop_requested.flag が存在すると起動をキャンセル
    - 実行中は data/execution.pid に PID を書き込む（Engine 内で処理）
- 監視プロセスの起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で指定（デフォルト 60）
  - run_monitoring は監視用 DB（settings.sqlite_path, デフォルト data/monitoring.db）に接続（環境にかかわらず本番 sqlite_path を使用）
  - 停止: data/stop_requested.flag を作成するとループを抜ける
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルトの DB パス: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
- ライブラリ関数（プログラム的利用）
  - ポートフォリオ: from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
  - 研究: from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  - AI (ニュース NLP): from kabusys.ai import score_news
    - score_news は DuckDB 接続を受け取り、OpenAI API キーが必要
  - レジーム判定: kabusys.ai.regime_detector.score_regime (直接呼び出し可、api_key 引数 or OPENAI_API_KEY)

環境変数・設定のポイント
- 自動 .env ロード
  - OS 環境変数 > .env.local > .env の優先順位でロードされます
  - 自動ロードを無効化する場合:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 重要な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
    - paper_trading の場合、run_execution は paper_trading 用 sqlite を使います
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db、監視ログ用）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト data/paper_trading.db）
  - LOG_LEVEL（デフォルト INFO）
  - OPENAI_API_KEY（AI モジュールを使う場合に必要）
  - MONITOR_POLL_INTERVAL（run_monitoring でポーリング間隔を上書き、秒）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1。production では 0 推奨）
- MONITOR の DB 動作
  - run_monitoring は “環境にかかわらず” settings.sqlite_path（デフォルト data/monitoring.db）を使用します
  - run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用し、本番 DB と分離

ログ / フラグファイル
- ログ
  - デフォルトのログディレクトリ: logs/
  - setup_logging(app_name="...") により stdout と日次ローテーションファイル (logs/<app_name>.log) に出力
  - ログレベルは LOG_LEVEL 環境変数で指定可能
- フラグ・PID ファイル（data ディレクトリ）
  - data/stop_requested.flag: 実行ループ（監視 / 実行）を停止するための外部フラグ（存在するとプロセスは終了）
  - data/kill.flag: KillSwitch によって書き込まれる停止要求（ExecutionEngine はこのファイルを検知して停止）
  - data/execution.pid: 実行エンジンが起動時に書き込む PID（既定位置）
  - これらのファイルは .env の設定でパスを上書き可能（Settings.kill_flag_path, pid など）

注意事項 / 運用メモ
- KABUSYS_ENV=live での運用は慎重に。validate_config は本番ガード（LINE トークン等未設定の警告）を行います。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を指定可能）。
- OpenAI API 呼び出しは料金が発生します。AI モジュールを運用する場合は API キーの管理に注意してください。
- logger や DB 接続は既成のユーティリティ関数を利用しており、ハンドラの二重登録や DB マイグレーション処理を配慮しています。
- DuckDB を直接操作する関数は SQL を用いて高速に集計を行う設計です（外部依存を最小化）。

ディレクトリ構成（主要ファイルと役割）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — Settings クラス（環境変数 / .env 読み込み / validation helpers）
  - config_setup.py — .env 作成の対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（ブローカー・リスク管理・エンジン組立）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングし ai_scores に書き込むロジック
    - regime_detector.py — マクロニュース + ETF MA を使った市場レジーム判定
    - __init__.py — ai の公開 API（score_news 等）
  - monitoring/
    - monitoring_db.py — SQLite 監視ログ層（テーブル作成 / CRUD）
    - system_monitor.py — システム/データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — （注文監視ロジック — ※本 README のコード抜粋に基づく想定）
    - kill_switch.py — Kill Switch の実装（kill.flag 書き込み）
    - monitoring_engine.py — 各モニタを束ねるループ（テスト用 run_once / 本番 run）
    - alert_manager.py — （アラート送信の抽象化）
  - execution/
    - execution_engine.py — ExecutionEngine 本体（セッション管理 / 発注ループ）
    - broker_factory.py — Broker クライアント生成（Mock/実ブローカー切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行周りのコンポーネント
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ等
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け関数
    - position_sizing.py — 株数計算（単元株丸め・リスクベース等）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - utils/
    - logging_setup.py — 統一的なロギング設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - data/ (実行時に使用するパスの例)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (DuckDB)
    - kill.flag / stop_requested.flag / execution.pid

最後に
- この README はリポジトリ内の主要なスクリプトとモジュールの概要・操作手順をまとめたものです。  
- 実運用前には python -m kabusys.validate_config による設定検証を行い、.env の内容（特に本番用の値）を慎重に確認してください。  

質問や追加したいドキュメント（例: API contract、デプロイ手順、CI 設定、詳細な設計ドキュメント）などがあれば教えてください。必要に応じて追記します。