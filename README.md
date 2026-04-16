# KabuSys

日本株向けの自動売買システムの一部コードベースです。ポートフォリオ構築、発注エンジン、監視・アラート、リサーチ（ファクター計算）、および AI を利用したニュースセンチメント評価などの機能群を含みます。

以下はこのリポジトリの README.md（日本語）です。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群です。主な目的は以下です。

- シグナルに基づくポートフォリオ構築とポジションサイズ決定
- ブローカーとの発注／状態管理（ExecutionEngine）
- システム稼働性・注文状態・リスクの監視とアラート（LINE）
- Paper Trading（疑似発注）モードによる安全な検証
- DuckDB / SQLite を用いた時系列データ・監視ログの保持
- ニュースを LLM（OpenAI）で評価して銘柄ごとのスコアを生成
- 研究用のファクター計算・特徴量評価ユーティリティ
- Streamlit ベースの監視ダッシュボードと検証レポートツール

設計方針として「外部 API を呼ばない分析部分」「本番 DB と Paper Trading DB の分離」「ルックアヘッドバイアスの回避」「フェイルセーフ（API失敗時の保守的フォールバック）」が採用されています。

---

## 主な機能一覧

- 設定管理
  - `kabusys.config.Settings` による環境変数読み込み（.env/.env.local の自動ロード。無効化可能）
  - 必須変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）

- 実行エンジン
  - `run_execution.py`：ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` では MockBroker を使用し DB を分離。
  - 発注管理（OrderManager / OrderRepository / Reconciler 等）

- 監視
  - `run_monitoring.py`：SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔制御）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログは SQLite（デフォルト `data/monitoring.db`）に永続化（`monitoring_db.init_monitoring_db` がスキーマを作成・マイグレーション）

- アラート
  - `AlertManager`：LINE Messaging API へのプッシュ通知（クールダウン管理）
  - `KillSwitch`：条件に応じて `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送る

- ポートフォリオ構築・リスク調整・ポジションサイズ計算
  - 等重配分・スコア重み・リスクベース配分
  - セクターキャップ適用、レジーム乗数の算出

- リサーチ
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ

- AI 関連
  - `ai.news_nlp.score_news`：raw_news を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを生成して `ai_scores` に書き込む
  - `ai.regime_detector.score_regime`：ETF（1321）MA200 乖離＋マクロニュース LLM 評価で市場レジーム判定を行い `market_regime` に保存

- ツール
  - `tools.paper_verification_report`：Paper Trading DB（デフォルト `data/paper_trading.db`）から検証レポートを生成（稼働率、注文成功率、P95 レイテンシ等）

- ダッシュボード
  - `monitoring/streamlit_dashboard.py`：Streamlit を使った監視ダッシュボード（read-only で SQLite を参照）

---

## セットアップ手順

前提
- Python 3.9+（コードでは typing 機能を使用）
- SQLite は Python 標準ライブラリに含まれます
- DuckDB、psutil、requests、openai、streamlit 等の外部ライブラリが必要

推奨手順（UNIX 系を想定）:

1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt`）

3. プロジェクトルートに .env を配置（自動読み込み）
   - 自動ロードはデフォルトで有効。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. 主要な環境変数（例）
   - 必須（運用によっては必須）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を利用する場合:
     - OPENAI_API_KEY
   - モード:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - その他（省略時はデフォルトを使用）:
     - SQLITE_PATH (default: data/monitoring.db)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - PAPER_FILL_MODE (instant | partial | never | reject) — Paper Trading の約定モード
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager 用
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で使用）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

5. データディレクトリ
   - `data/` 以下に DB やフラグファイル（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）を置きます。起動スクリプトは存在しない場合に作成・初期化します（監視用 DB は起動時にテーブル作成を行います）。

---

## 使い方（起動・実行例）

- 監視ループ起動（SystemMonitor）
  - 簡単: KABUSYS_ENV（オプション）を設定してモジュール実行
    - python -m kabusys.run_monitoring
    - 環境変数でポーリング間隔を上書き: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 仕様:
    - デフォルトポーリング間隔は 60 秒
    - 停止はプロジェクトルートの `data/stop_requested.flag` を作成するか Ctrl+C
    - 監視は常に本番の sqlite_path を参照（環境にかかわらず）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - Paper Trading モード:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合、MockBroker を用いて `data/paper_trading.db` に記録（本番 DB と分離）
  - 動作:
    - 起動時に `data/stop_requested.flag` があれば起動せず終了
    - 実行中に同ファイルが作成されると安全に停止処理を行う
    - ExecutionEngine の PID は `data/execution.pid` に書き込まれる

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only で監視データ（ポジション、注文、システムステータス、リスクログ）を表示

- AI スコアリング・レジーム判定（ライブラリ API）
  - ai.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キーを引数で渡すか環境変数 `OPENAI_API_KEY` を設定

---

## 主要ファイル・ディレクトリ構成

（実際のパスはリポジトリの `src/kabusys` を想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 設定読み込み（.env 自動ロード）と Settings クラス
  - run_monitoring.py
    - SystemMonitor のポーリング起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading の切り替えあり）
  - tools/
    - __init__.py
    - paper_verification_report.py
      - Paper Trading DB に対する検証レポートツール
  - ai/
    - __init__.py
    - news_nlp.py
      - raw_news → OpenAI → ai_scores 書き込み
    - regime_detector.py
      - ETF MA200 とマクロニュースを組合せて market_regime を作成
  - monitoring/
    - __init__.py
    - monitoring_db.py
      - SQLite スキーマ作成と MonitoringDB ラッパー
    - system_monitor.py
      - CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py
      - 滞留注文・約定異常の検出と risk_logs への記録
    - risk_monitor.py
      - ドローダウン・ポジション上限の監視
    - kill_switch.py
      - kill.flag 書き込みロジック（Execution 停止）
    - alert_manager.py
      - LINE プッシュ通知（クールダウン）
    - monitoring_engine.py
      - 各モニタを束ねるポーリングエンジン
    - streamlit_dashboard.py
      - Streamlit ダッシュボード
  - portfolio/
    - __init__.py
    - portfolio_builder.py
      - 候補選定・等重・スコア重み
    - risk_adjustment.py
      - セクターキャップ・レジーム乗数
    - position_sizing.py
      - 発注株数算出（リスクベース / 等分 / スコアベース）
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value ファクター計算（DuckDB SQL）
    - feature_exploration.py
      - 将来リターン・IC・統計サマリ
  - execution/
    - order_manager.py
    - reconciler.py
    - （その他ブローカ抽象や OrderRepository 等）
  - utils/
    - __init__.py
    - process_priority.py
      - プラットフォーム差異を吸収した優先度／CPU affinity 設定ユーティリティ
  - research, data 等の補助モジュール

- data/
  - monitoring.db (SQLite、デフォルト)
  - paper_trading.db (Paper Trading 用 DB)
  - kabusys.duckdb (DuckDB)
  - execution.pid, kill.flag, stop_requested.flag などの制御ファイル

---

## 重要な設計上の注意点 / 運用メモ

- Paper Trading は本番 DB と完全に分離される設計です（`KABUSYS_ENV=paper_trading` のとき `paper_sqlite_path` を使用）。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テスト等で無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 監視ループは `data/stop_requested.flag` により外部から停止できます。Execution 側も同じフラグで停止を受け付けます。
- KillSwitch によって `data/kill.flag` が作成されると ExecutionEngine に停止シグナルを送る運用を想定しています（KillSwitch のトリガーにはドローダウンやポジション上限など）。
- LLM（OpenAI）連携は外部 API 呼び出しのため失敗時のフェイルセーフが多く組み込まれていますが、API キー管理やレート制御は運用で注意してください。
- DuckDB を用いたリサーチ・ファクター計算は SQL と Python の組合せで効率的に行います。prices_daily / raw_financials / raw_news 等のテーブルを前提としています。

---

## よく使うコマンド一覧

- 監視起動：
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動（本番想定）：
  - KABUSYS_ENV=live python -m kabusys.run_execution
- 実行エンジン起動（Paper Trading）：
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper 検証レポート：
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード：
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要であれば README に含める環境変数の完全一覧、サンプル .env.example、または各モジュール（ExecutionEngine の起動フローや Reconciler の詳細）に関する運用手順を追加します。どの情報を拡張しましょうか？