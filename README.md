# KabuSys

日本株自動売買システムのコードベース README（日本語）

概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコンポーネント群です。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine） — ブローカーへの発注、リスク管理、注文管理、再同期（リコンシリエーション）
- 監視（Monitoring） — システム状態・データ鮮度・注文滞留・リスク監視、kill flag による停止トリガー、LINE 通知、Streamlit ダッシュボード
- ポートフォリオ構築（Portfolio） — 候補選定、重み計算、ポジションサイズ決定、セクター制限およびレジーム調整
- リサーチ（Research） — ファクター算出（モメンタム・ボラティリティ・バリュー）、特徴量探索、IC 計算
- AI モジュール（AI） — ニュースの NLP による銘柄センチメント評価、マクロニュースと価格から市場レジーム判定
- ユーティリティ — 環境設定ローダ、プロセス優先度設定など
- ツール群 — Paper Trading の検証レポート生成スクリプト等

重要な設計方針：
- DuckDB/SQLite を利用したデータ層（研究用は DuckDB、監視や注文ログは SQLite）
- 環境変数 / .env による設定（自動ロード機能あり）
- Paper Trading（`KABUSYS_ENV=paper_trading`）は本番 DB と分離（専用 SQLite）して動作

---

## 機能一覧（要約）

- Execution
  - ブローカークライアントの抽象化（本番 / モック切替）
  - 注文作成・送信・同期（OrderManager, Reconciler）
  - リスク管理（RiskManager）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存確認・データ鮮度チェック
  - TradeMonitor: 注文滞留や約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard の upsert
  - KillSwitch: フラグファイル書き込みで ExecutionEngine 停止指令
  - AlertManager: LINE へのプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視データの可視化）
- Research / Portfolio
  - ファクター算出（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC 計測、統計サマリー
  - 候補選定、等重/スコア重み、ポジションサイズ決定（lot 単位丸め、aggregate cap）
  - セクター上限・レジーム乗数（市場レジームに応じた投下資金調整）
- AI
  - ニュースを OpenAI（gpt-4o-mini）でスコアリングして ai_scores に書き込み
  - マクロニュース + ETF MA200 乖離から市場レジーム（bull/neutral/bear）判定
  - 再試行・JSON バリデーション・スコアクリップ等の堅牢化処理
- ツール
  - Paper Trading 検証レポート生成（期間指定可）

---

## セットアップ手順（開発 / 実行環境）

前提：
- Python 3.9+（ソースで型ヒント等を使用しているため 3.9 以上を推奨）
- 必要なパッケージ: duckdb, psutil, requests, streamlit, openai（用途に応じて）
  - 例: pip install -r requirements.txt（requirements.txt がない場合は個別にインストール）

最低インストール例：
- pip install duckdb psutil requests streamlit openai

リポジトリのルートに .env（または .env.local）を置くと自動で読み込まれます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必要な（代表的な）環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API 用
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用
- LINE_USER_ID — LINE 通知先
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- PAPER_FILL_MODE — paper_trading のモック fill 動作（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH など監視設定
- 各閾値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

データディレクトリ作成（例）:
- mkdir -p data

初回実行時は DB スキーマを自動作成する処理が各起動スクリプト内で呼ばれます（init_monitoring_db 等）。明示的に初期化する必要は通常ありません。

---

## 使い方（主要なコマンド）

以下はプロジェクトルートから実行する想定です。

- 監視ループ起動（Monitoring）
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用します（監視ログは常に本番 DB）
  - 実行例:
    - python -m kabusys.run_monitoring

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します
  - 実行例:
    - python -m kabusys.run_execution
  - 事前に .env や環境変数で KABUSYS_ENV 等を設定してください。

- Streamlit 監視ダッシュボード
  - 起動方法:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - もしくは別の path を指定できます（--db オプション）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（`--db` で上書き可）

- AI 機能（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 呼び出す際は DuckDB の接続オブジェクトを渡します（OpenAI キーは第3引数または環境変数 OPENAI_API_KEY）

注意点:
- 監視側は本番の sqlite_path を常に参照します。Paper Trading の挙動とは分離されています。
- ExecutionEngine 起動時はプロセス優先度を "high" に試みます（set_process_priority）。
- KillSwitch は設定された flag ファイル（デフォルト data/kill.flag）を書き込むことで ExecutionEngine に停止指示を送ります。ExecutionEngine は起動時にフラグのクリアを行うオプションを持つ（設定に依存）。

---

## 主要モジュールの簡単説明

- kabusys.config
  - .env 自動ロード、Settings クラス（アプリケーション設定の取得）

- kabusys.monitoring
  - monitoring_db: SQLite のスキーマ初期化と永続化 API（MonitoringDB）
  - system_monitor, trade_monitor, risk_monitor: 各種チェックを実装
  - kill_switch: フラグファイル経由の停止ロジック
  - alert_manager: LINE へ通知（クールダウン）
  - monitoring_engine: これらを束ねるポーリングエンジン
  - streamlit_dashboard: 監視データ可視化用 UI

- kabusys.execution
  - order_repository / order_manager / reconciler / execution_engine 等（注文ライフサイクル、再同期、リスク制御）

- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment（候補選定・重み・株数計算・セクター/レジーム制御）

- kabusys.research
  - factor_research, feature_exploration（ファクター算出・IC 等）

- kabusys.ai
  - news_nlp, regime_detector（OpenAI を用いたニュース評価・レジーム判定）

- kabusys.utils
  - process_priority: プロセス優先度・CPU affinity 設定用ユーティリティ

---

## ディレクトリ構成

（src/kabusys をルートとした主要ファイル・モジュール）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - order_repository.py
      - order_record.py
      - reconciler.py
      - execution_engine.py
      - broker_factory.py
      - broker_api.py
      - (その他 execution 関連ファイル)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - pipeline.py
      - stats.py
      - (DuckDB / prices データ操作用)
    - utils/
      - __init__.py
      - process_priority.py

（上記は主要ファイルの抜粋です。実装済みファイルや補助モジュールがさらに存在します。）

---

## その他の注意点 / 運用メモ

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等で、既存 DB に対してカラム追加（簡易マイグレーション）を行う処理があります（例: peak_value, latency_ms の追加）。
- Paper Trading:
  - `KABUSYS_ENV=paper_trading` の場合、実行エンジンは MockBrokerClient を用い、`PAPER_TRADING_SQLITE_PATH` に結果を記録します。本番 DB とは分離されます。
  - PAPER_FILL_MODE でモック約定の挙動を制御できます（instant/partial/never/reject）。
- ロギング:
  - 起動スクリプトは basicConfig(level=logging.INFO) を設定しています。必要に応じて LOG_LEVEL を設定してください。
- OpenAI API:
  - AI 機能は外部 API を呼ぶため API キー（OPENAI_API_KEY）が必要です。API 呼び出しは再試行やバックオフを行いますが、失敗時はフォールバック動作（例: macro_sentiment=0）を行いシステムの停止に繋がらないよう設計されています。
- プロセス優先度:
  - 起動時に set_process_priority("high") を呼んでいます。権限や OS により設定が失敗する場合はログに警告が出ますが稼働自体は継続します。

---

必要があれば、README に含める詳細な環境変数一覧、サンプル .env、docker-compose / systemd ユニットの例、あるいは API の詳細仕様書（ExecutionEngine の外部 API 等）を追加で作成します。どの情報を優先して追加しますか？