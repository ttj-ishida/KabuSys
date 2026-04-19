# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README。

このドキュメントはリポジトリ内の主要モジュールや起動スクリプトの使い方、セットアップ手順、ディレクトリ構成を簡潔にまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームです。基本機能は次のとおりです。

- シグナル生成とポートフォリオ構築（ファクター計算・重み付け・ポジションサイズ算出）
- ExecutionEngine による発注・リスク管理（紙トレード/本番切替対応）
- 監視（システム・注文・リスク）と Kill Switch による自動停止
- ニュース NLP を用いた AI スコアリング・レジーム判定（OpenAI 統合）
- Paper Trading 検証レポート出力ツール
- DuckDB / SQLite を用いた分析・ログ永続化

設計方針として、ルックアヘッドバイアス対策、フェイルセーフ（API失敗時のフォールバック）、モジュール分離（AI 呼び出しの分離）などが組み込まれています。

---

## 主な機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動（KABUSYS_ENV による paper/live 切替）
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動
- 設定管理
  - python -m kabusys.config_setup : 対話式 .env 作成ウィザード
  - python -m kabusys.validate_config : 設定検証 CLI（--strict オプションあり）
- 監視（monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine
  - kill.flag による ExecutionEngine 停止
  - monitoring.db（SQLite） へのログ永続化
- ポートフォリオ構築（portfolio）
  - 候補選定、重み付け（等金額/スコア加重）、ポジションサイズ計算（単元丸め・集約キャップ）
  - セクターキャップ適用、レジーム乗数計算
- リサーチ（research）
  - ファクター（Momentum/Value/Volatility）計算（DuckDB 上での SQL 実行）
  - 将来リターン計算、IC 計算、統計サマリー
- AI（ai）
  - news_nlp.score_news: ニュース記事を OpenAI でスコア化して ai_scores に書き込み
  - regime_detector.score_regime: MA200 とマクロニュースで市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の実績を検証するレポート生成

---

## セットアップ手順（ローカル開発向け）

以下はローカルで動かすための基本手順です。

1. リポジトリをクローンし、Python 仮想環境を作成
   - 推奨: Python 3.9+
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - 明示的な requirements.txt は本コードブロックに含まれていませんが、主な依存は以下です:
     - duckdb
     - psutil
     - openai
     - (任意) PyYAML（validate_config の YAML 検証を有効にする場合）

   - 例:
     - pip install duckdb psutil openai PyYAML

   - 注意: OpenAI SDK のバージョン差異による API 呼び出し形に注意してください。

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または手動で .env を作成（リポジトリ直下に置く）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...  （AI 機能を使う場合）
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db  （paper_trading 用）
     - LOG_LEVEL=INFO
     - その他: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, PAPER_FILL_MODE, など

   - .env 作成後、設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります。

4. データディレクトリの準備
   - デフォルトでは data/ 以下に DB・フラグ等を作成します。必要に応じてパスを .env で上書きしてください。
   - ログは logs/ に出力されます（TimedRotatingFileHandler による日次ローテーション）。

5. 実行権限・プロセス優先度
   - 実行スクリプトは起動時にプロセス優先度を設定しようとします（psutil を使用）。権限がない環境では警告が出ますが動作は継続します。

---

## 使い方（主要コマンド例）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録します。
    - KABUSYS_ENV=live の場合は本番 API を使って実際に発注します。
    - 起動前に data/stop_requested.flag があれば起動しません。
    - 実行中に data/stop_requested.flag が作成されると安全停止処理が行われます。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings に基づき SQLite（monitoring.db）と DuckDB に接続し SystemMonitor をポーリングします。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します（監視ログは本番 DB に集約する設計）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を与えるか、環境変数 PAPER_TRADING_SQLITE_PATH を参照します。

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）を .env または引数で設定してください。
  - ai.score_news / ai.regime_detector の関数は DuckDB 接続と target_date を受け取る形で使用します。

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使用し、paper_trading.db に記録
  - live: 本番発注（注意して使用）
- DUCKDB_PATH: data/kabusys.duckdb（分析 DB）
- SQLITE_PATH: data/monitoring.db（監視ログ DB）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 SQLite）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（Kill Switch / PID 管理）

設定値は kabusys.config.Settings クラスで管理されています。プログラム内部で validation を行うので、不正な値は起動時にエラーになります。

---

## 停止・Kill Switch の仕組み

- kill.flag（デフォルト: data/kill.flag）
  - KillSwitch クラスが条件を満たすとこのファイルを書き込み、ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine は起動時に kill.flag を検査し、存在する場合は起動しません。
  - KillSwitch の主トリガー例: ドローダウン閾値超過、ポジション数上限超過 等。

- stop_requested.flag（run_monitoring / run_execution が参照）
  - 監視ループ・実行ループの外部停止に使用されます（data/stop_requested.flag を作ればモジュールが終了します）。

---

## ログとデータ

- ログ
  - デフォルト: logs/<app_name>.log（日次ローテーション・30 日保持）
  - setup_logging() ユーティリティで統一的に設定されます。

- DB
  - DuckDB: 分析用（prices_daily, raw_financials, raw_news, …）
  - SQLite: 監視ログ（monitoring.db）と Paper Trading 用（paper_trading.db）

---

## ディレクトリ構成

下記は src/kabusys 以下の主な構成です（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理（Settings）
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - utils/
      - logging_setup.py       — ログ設定ユーティリティ
      - process_priority.py    — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py       — SQLite 永続層（テーブル作成・CRUD）
      - system_monitor.py      — システム状態・データ鮮度監視
      - trade_monitor.py       — （注文監視ロジック; ソースに依存）
      - risk_monitor.py        — ドローダウン・ポジション上限監視
      - kill_switch.py         — kill.flag 書込ロジック
      - monitoring_engine.py   — 各 Monitor を束ねるエンジン
      - alert_manager.py       —（アラート送信管理; 実装依存）
    - execution/
      - execution_engine.py    — ExecutionEngine（起動・セッション管理）
      - order_manager.py       — Order 管理
      - order_repository.py    — DB 層（発注ログ等）
      - broker_factory.py      — ブローカークライアント生成（Mock / Live 切替）
      - risk_manager.py        — 発注前リスク制御
      - reconciler.py          — 注文とブローカー状態の整合処理
    - portfolio/
      - portfolio_builder.py   — 候補選定・重み付け
      - position_sizing.py     — 株数算出・集約キャップ
      - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - research/
      - factor_research.py     — ファクター計算（Momentum/Value/Volatility）
      - feature_exploration.py — IC / 統計サマリー等
    - ai/
      - news_nlp.py            — ニュース NLP（OpenAI 統合）
      - regime_detector.py     — マーケットレジーム判定
    - tools/
      - paper_verification_report.py — Paper Trading レポート生成
    - data/                     — 実行時に生成される（デフォルト）:
      - monitoring.db
      - paper_trading.db
      - kill.flag
      - execution.pid
    - logs/
      - execution.log
      - monitoring.log
      - など

（注）上記はリポジトリ内のファイルヘッダ情報から抜粋しています。実際のファイルはさらに多数存在します。

---

## 注意事項 / ヒント

- KABUSYS_ENV の取り扱い
  - development: 開発用（発注しない設計の箇所があります）
  - paper_trading: 発注ロジックは MockBrokerClient を使用し、paper_trading.db に記録されます。本番 DB と分離されます。
  - live: 実際に発注を行います — 本番環境での設定には十分注意してください（LINE 通知や Kill Switch 設定の確認推奨）。

- OpenAI を使う機能
  - OPENAI_API_KEY が必須です。API 呼び出しはネットワークエラー・429・5xx を考慮したリトライ実装が入っていますが、キーの保護に注意してください。
  - レスポンスは JSON モードで扱いますが、パース失敗時はフェイルセーフ（スコア 0.0 で継続）になっています。

- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等でテーブルやカラムの後付け処理を行います（既存 DB に不足カラムがあれば追加）。

- 権限
  - process_priority の設定やファイル作成（logs/、data/）には権限が必要です。権限不足のケースでは警告が出て処理は継続しますが、期待する挙動にならない可能性があります。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行（Execution）:
  - python -m kabusys.run_execution
- 監視（Monitoring）:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースに含まれるモジュールの説明をまとめたもので、詳細な API 仕様や設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）が別途存在する想定です。実運用前には .env の値、データベースのバックアップ、Kill Switch の動作確認、監視アラートの受信設定（LINE 等）を必ず行ってください。