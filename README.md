# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株向けの自動売買／リサーチ基盤の一部実装です。  
README ではプロジェクト概要、主要機能、セットアップ、基本的な使い方、ディレクトリ構成を日本語でまとめます。

注意：本ドキュメントはソースコード（src/kabusys 以下）を参照して作成しています。実行環境や追加の依存関係はプロジェクトによって異なる場合があります。

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群を含む小規模なトレーディング基盤です。

- 取引エンジン（ExecutionEngine）起動・監視
- Paper Trading（模擬発注）向け分離 DB のサポート
- システム監視（CPU/メモリ/ディスク、プロセス、データ鮮度）
- リスク監視（ドローダウンやポジション上限）
- ニュース NLP（OpenAI を用いたセンチメントスコアリング）
- 市場レジーム判定（MA と LLM を組み合わせたスコア）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ用ファクター計算（DuckDB 上での計算）
- 各種ユーティリティ（ログ設定、プロセス優先度、設定ウィザード、設定検証等）

設計上、実注文を行う「本番（live）」と模擬発注を行う「paper_trading」は明確に分離されています（環境変数 `KABUSYS_ENV` に依存）。

---

## 主な機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動（KABUSYS_ENV に依存）
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動
- 設定管理
  - python -m kabusys.config_setup : 対話式 .env 作成ウィザード
  - python -m kabusys.validate_config : 設定の静的チェック CLI
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に監視ログを永続化（monitoring_db）
  - Kill Switch（条件により data/kill.flag を書き込み、ExecutionEngine を停止）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report : ペーパートレード DB から指標を集計してレポート出力
- AI（OpenAI）連携
  - kabusys.ai.score_news : raw_news を集約して LLM に問い合わせ、ai_scores に書き込み
  - kabusys.ai.regime_detector.score_regime : マクロ + MA200 を組み合わせて市場レジーム判定
- ポートフォリオ構築
  - 候補選定（select_candidates）、重み付け（等重・スコア重み）、位置サイズ計算（calc_position_sizes）
  - セクター上限やレジームによる乗数の適用
- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC 計算・統計サマリ

---

## セットアップ手順（開発者向け）

1. 必要な Python バージョン
   - Python 3.10 以上を推奨（PEP 604 の型記法を使用）。

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  または Windows では .venv\Scripts\activate

3. 依存パッケージをインストール
   - プロジェクトに requirements.txt があればそれを利用してください。無ければ主要ライブラリを個別にインストールします（機能によって追加が必要）。
     - duckdb
     - psutil
     - openai
     - pyyaml （設定検証で YAML を検証する場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

4. .env の作成
   - 対話式ウィザード
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに `.env` を手動で作成（.env.example を参照してください）。

5. 設定検証
   - python -m kabusys.validate_config
   - `--strict` を付けると警告も失敗扱いになります。

6. データディレクトリの準備
   - デフォルトで使用するファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - ログディレクトリ: logs/ （setup_logging が自動作成します）

---

## 環境変数（代表的なもの）

- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用トークン
  - KABU_API_PASSWORD : kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV : development | paper_trading | live （デフォルト: development）

- データベース / ファイルパス
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH : SQLite 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH : ExecutionEngine pid ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH : kill.flag のパス（デフォルト data/kill.flag）

- ロギング / 動作
  - LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR）
  - LOG_DIR : ログ保存ディレクトリ（デフォルト logs/）
  - MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒、デフォルト 60）

- OpenAI
  - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で使用）

- Paper Trading
  - PAPER_FILL_MODE : instant | partial | never | reject（デフォルト "instant"）

---

## 使い方（基本コマンド例）

- .env を作成
  - python -m kabusys.config_setup

- 設定を検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実エンジン起動（Execution）
  - 本番/ペーパートレードは KABUSYS_ENV によって動作が変わる
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
    - ExecutionEngine は data/execution.pid を作成します（pid file）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（例: MONITOR_POLL_INTERVAL=30）
    - 監視は常に（KABUSYS_ENV に関係なく）本番 sqlite_path を使用して監視ログを書き込みます。

- 停止の仕組み
  - stop_requested.flag（data/stop_requested.flag）を作成すると run_execution / run_monitoring のループが停止（スクリプト内のフラグ参照）。
  - Kill Switch（条件により data/kill.flag に理由を書き込み）により ExecutionEngine を停止させることができます。
    - KillSwitch API を使って自動的に kill.flag を作成します（監視コンポーネント内）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（指定がない場合は PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルトを使用）

- プログラム的に利用（ライブラリ使用例）
  - DuckDB 接続を作成してリサーチ関数を呼ぶ例:
    - import duckdb
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.research import calc_momentum
    - calc_momentum(conn, target_date)

  - AI スコアリングを実行するには OpenAI API キーが必要:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

---

## ログと監視データ

- ログ
  - ログはルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（logs/<app_name>.log）を設定します。
  - デフォルトで 30 日分ローテーションを保持します。
  - setup_logging(app_name="execution") のようにアプリ名を渡して使用します。

- 監視データ（SQLite）
  - デフォルト: data/monitoring.db
  - テーブル:
    - system_status（CPU, memory, disk, process_ok, recorded_at）
    - trade_logs（発注イベントログ、latency_ms を含む）
    - positions（現在のポジション）
    - risk_logs（リスクイベント）
    - dashboard（ダッシュボード集計）
  - DB 初期化: 起動時に init_monitoring_db() によりテーブル作成・マイグレーションを行います（冪等）。

---

## ディレクトリ構成（抜粋）

```
src/
  kabusys/
    __init__.py
    config.py                # 環境変数/.env 読込と Settings
    config_setup.py          # 対話式 .env ウィザード
    validate_config.py       # 設定検証 CLI
    run_execution.py         # ExecutionEngine 起動スクリプト
    run_monitoring.py        # SystemMonitor 起動スクリプト

    ai/
      __init__.py
      news_nlp.py            # raw_news → OpenAI → ai_scores
      regime_detector.py     # MA200 + LLM によるレジーム判定

    monitoring/
      monitoring_db.py       # SQLite 永続化層
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      alert_manager.py?      # （コード内参照あり）

    execution/                # Execution 系の実装（BrokerFactory 等）
      broker_factory.py
      execution_engine.py
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py

    research/
      factor_research.py
      feature_exploration.py

    tools/
      paper_verification_report.py

    utils/
      logging_setup.py
      process_priority.py
```

（上は主要ファイルの抜粋です。実際の全ファイルは src/kabusys 配下を参照してください。）

---

## 実運用に関する注意点

- KABUSYS_ENV の設定は重大な影響を与えます。`live` は本番（実際に発注）です。`paper_trading` は発注を模擬し DB を分離します。`development` はローカル開発用です。設定検証を必ず行ってください。
- .env を絶対にリポジトリにコミットしないでください（config_setup.py のヘッダに注意喚起があります）。
- OpenAI を使用する機能は API コスト・レイテンシ・レート制限に注意してください。ネットワークエラーや 5xx にはリトライ実装がありますが、運用上の考慮が必要です。
- run_monitoring と run_execution はフラグファイル（data/stop_requested.flag / data/kill.flag）で停止制御を行います。これらのファイルの取り扱いは慎重に行ってください。
- 実行時は必ずログを確認し、validate_config の出力に注意してください。特に本番環境（KABUSYS_ENV=live）では LINE 通知や KILL_FLAG_CLEAR_ON_START の設定などを再確認してください。

---

## よく使うコマンドまとめ

- 仮想環境作成・有効化
  - python -m venv .venv && source .venv/bin/activate
- 依存ライブラリインストール
  - pip install duckdb psutil openai pyyaml
- .env ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要に応じて README を拡張します。特定のコンポーネント（ExecutionEngine の API、Broker 実装、TradeMonitor の詳細、AlertManager の設定など）についてドキュメント化を希望される場合は、その旨と対象箇所を教えてください。