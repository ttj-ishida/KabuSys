# KabuSys

日本株向け自動売買システムのコアライブラリ群および運用ユーティリティ群です。  
このリポジトリはエンジン起動スクリプト、監視・リスク管理、ポートフォリオ構成、リサーチ（DuckDB ベース）、およびニュース NLP / レジーム判定のための AI 統合を含みます。

## プロジェクト概要
- 自動売買エンジン（ExecutionEngine）と監視プロセス（MonitoringEngine）を分離して実装。
- DuckDB を用いた時系列データ解析（ファクター計算、特徴量探索）。
- SQLite に監視ログ・トレードログ・ダッシュボード等を永続化。
- Paper Trading モード（本番データと分離した専用 SQLite を使用）をサポート。
- OpenAI を利用したニュースのセンチメントスコアリングと、それを利用した市場レジーム判定機能を搭載。
- ログはコンソールと日次ローテートのファイル出力（logs/*.log）で管理。

## 主な機能一覧
- 実行・監視
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV による paper_trading/live の振る舞い切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（監視データを SQLite に記録）
- 構成管理・検証
  - config_setup.py: .env を対話式に生成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の基本検証 CLI（--strict オプションあり）
- 運用ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成（稼働率・約定率・レイテンシ等）
- ポートフォリオ構築
  - portfolio: 候補選定、重み計算、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイジング
- リサーチ
  - research: ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリ
- AI（OpenAI 統合）
  - ai.news_nlp: ニュース記事のセンチメントを LLM で評価して ai_scores に保存
  - ai.regime_detector: ETF・ニュースを組み合わせた日次レジーム判定（market_regime へ書き込み）
- 監視（monitoring）
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch: 各種監視と Kill Switch（data/kill.flag）連携
- ユーティリティ
  - utils.logging_setup: 統一的なログ設定（stdout + 日次ローテート）
  - utils.process_priority: プラットフォームを吸収したプロセス優先度設定

## セットアップ手順（ローカル開発向け）
前提:
- Python 3.10+ を推奨
- システムに duckdb, psutil, openai 等が必要（下記を参考にインストール）

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係インストール
   - 要件ファイルがある場合:
     - pip install -r requirements.txt
   - 最低限必要なパッケージ（例）:
     - pip install duckdb psutil openai
   - 追加（YAML 検証を行う場合）:
     - pip install pyyaml
4. .env の用意
   - 対話式ウィザードで生成:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成してください。
5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告も致命扱いにしたい場合: python -m kabusys.validate_config --strict
6. データディレクトリ・ログディレクトリの確認
   - デフォルトで以下のパスが使われます。存在しない場合は起動時に自動作成されることがありますが、権限等に注意してください。
     - SQLite: data/monitoring.db
     - Paper SQLite (paper_trading): data/paper_trading.db
     - DuckDB: data/kabusys.duckdb
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログ: logs/

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
  - paper_trading のときは run_execution が MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（開発用。1=クリア）

## 使い方（起動例）
- ExecutionEngine（実際の取引もしくは Paper Trading）
  - python -m kabusys.run_execution
  - 動作:
    - Settings に基づき SQLite / DuckDB に接続
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使う（本番 DB と分離）
    - 起動中は data/execution.pid を生成
    - data/stop_requested.flag を検知すると安全に停止
- Monitoring（監視ループ）
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL によりポーリング間隔を設定（環境変数で上書き可能, デフォルト 60 秒）
    - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、実行プロセスの有無）をチェックし SQLite に記録
    - KillSwitch 判定により data/kill.flag を書き込むことがある（ExecutionEngine 停止トリガ）
- .env の作成 / 更新（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI スコアリング / レジーム判定（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

## 運用上の注意
- Monitoring は KABUSYS_ENV に関係なく Settings.sqlite_path（本番用 DB）を使用して監視データを記録します。別ファイルを使いたい場合は環境変数で SQL*ITE_PATH を変更してください。
- run_execution は paper_trading モードでは paper_sqlite_path を使用して発注ログを分離します。
- 停止 / 停止要求:
  - data/stop_requested.flag が存在すると run_execution / run_monitoring が検出して終了します。
  - Kill Switch（data/kill.flag）は Monitoring がリスク条件を検出した際に書き込むことで ExecutionEngine に停止を促します。
  - kill.flag を手動で削除するには: rm data/kill.flag（あるいは Windows の場合は削除コマンドを使用）
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。
- ログ:
  - logs/<app_name>.log に日次ローテーションでログが出力されます。ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。
- OpenAI 利用:
  - API 呼び出しはリトライ・フェイルセーフ処理を含みますが、APIキー未設定時は該当機能は実行できません（呼び出し側で ValueError が発生）。

## ディレクトリ構成（主要ファイル）
（省略せず主要モジュールを列挙）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数/設定読み込み（.env 自動ロードロジック含む）
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート
    - utils/
      - logging_setup.py       — ログ初期化ユーティリティ
      - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
    - monitoring/
      - monitoring_db.py       — SQLite 永続化（テーブル作成・読み書きラッパー）
      - system_monitor.py      — システム状態とデータ鮮度監視
      - trade_monitor.py       — （トレード関連監視、実装に依存）
      - risk_monitor.py        — ドローダウン・ポジション上限監視
      - kill_switch.py         — kill.flag 書き込みユーティリティ
      - monitoring_engine.py   — 各 Monitor を束ねるエンジン
      - alert_manager.py       — （通知管理、実装に依存）
    - execution/               — ExecutionEngine 本体・注文管理等（実装ファイル群）
    - portfolio/
      - portfolio_builder.py   — 候補選定・重み付け
      - position_sizing.py     — 発注株数計算・利用可能現金スケール等
      - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - research/
      - factor_research.py     — Momentum / Value / Volatility ファクター計算
      - feature_exploration.py — 将来リターン・IC・統計サマリ
    - data/                    — スキーマ定義・パイプライン実装（prices_daily 等）※別モジュール参照
    - ai/
      - news_nlp.py            — ニュースの LLM スコアリング
      - regime_detector.py     — レジーム判定（ma200 + macro sentiment）
    - ... その他モジュール

（上記に記載のない補助モジュールも含まれます）

## 開発・テストに関する補足
- YAML ファイルの検証には PyYAML が必要です（validate_config.py 内のオプション）。
- OpenAI API 呼び出し部分はユニットテストでモック化しやすいように設計されています（_call_openai_api を patch 可能）。
- DuckDB をローカルに用意して prices_daily / raw_financials / raw_news 等のテーブルを準備することで research 関連機能を検証できます。

---

問題が発生した場合や README に追加して欲しい項目があれば教えてください。必要に応じてサンプル .env テンプレートや起動スクリプトの運用例（systemd / Supervisor 用のユニット例）も追加できます。