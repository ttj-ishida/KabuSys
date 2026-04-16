# KabuSys

日本株向けの自動売買システム（プロトタイプ）。シグナル処理、発注管理、モニタリング、ポートフォリオ構築、リサーチ、AI を用いたニュース評価などのコンポーネントを含むモジュール群です。

以下はこのリポジトリの README（日本語）です。

## プロジェクト概要

KabuSys は日本株の自動売買パイプラインを構成するライブラリ兼実行スクリプト群です。主要な機能は次の通りです。

- ExecutionEngine：ブローカー API と連携した発注・注文管理・リスク管理・リコンシリエーション
- Monitoring：プロセス・リソース・注文・ドローダウン監視、アラート通知（LINE）
- Portfolio construction：候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- Research：DuckDB を用いたファクター計算・特徴量解析・将来リターン計算
- AI モジュール：ニュースの LLM（OpenAI）によるセンチメント評価、レジーム判定
- Tools：Paper Trading 検証レポート生成、Streamlit ダッシュボード起動スクリプト 等

設計方針として、本番の発注 DB と Paper Trading DB を明確に分離し、ルックアヘッドバイアスを避ける（date.today() を直接参照しないなど）実装がなされています。

## 主な機能一覧

- SystemMonitor：CPU / メモリ / ディスク / プロセス生存確認、価格データ鮮度チェック
- TradeMonitor：滞留注文検出（stale orders）、約定価格の異常検出
- RiskMonitor：ドローダウン監視、ポジション数上限監視、ダッシュボード更新、リスクログ保存
- KillSwitch：条件に応じた停止フラグ（data/kill.flag）作成で ExecutionEngine を停止
- AlertManager：LINE Messaging API による通知（クールダウン機構あり）
- MonitoringEngine：上記モニタをまとめてポーリングしアラート／KillSwitch を評価
- Monitoring DB（SQLite）：system_status / trade_logs / positions / risk_logs / dashboard を管理、簡易マイグレーション機能あり
- Execution 側：OrderManager / OrderRepository / Reconciler / RiskManager / ExecutionEngine の組み合わせによる発注フロー
- Portfolio モジュール：候補選定・等重/スコア加重・リスクベース・単元丸め・集約キャップ処理
- Research：momentum / volatility / value ファクター、forward returns、IC 計算、統計サマリ
- AI：news_nlp（OpenAI を用いた記事センチメント → ai_scores に書き込み）、regime_detector（MA + マクロセンチメント合成）
- Tools：paper_verification_report（Paper Trading DB を基に指標を計算して PASS/FAIL 判定）、streamlit_dashboard（監視ダッシュボード）

## セットアップ手順（ローカル）

※ 仮想環境の作成を推奨します。

1. リポジトリをクローン／チェックアウト

2. 仮想環境作成（例）

   - Unix/macOS:
     python -m venv .venv
     source .venv/bin/activate
   - Windows (PowerShell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1

3. 必要パッケージをインストール

   リポジトリに requirements.txt がある場合はそれを使用してください。ない場合は最低限以下のパッケージが必要です（バージョンは適宜）:

   pip install duckdb psutil openai streamlit requests

   （実際の運用では kabu API クライアントなど追加依存が必要になることがあります）

4. 環境変数の準備

   プロジェクトルートの .env / .env.local を用いて環境変数を設定できます（自動読み込みあり。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

   主な環境変数:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須の所あり）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（実運用）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を有効にする場合
   - PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant|partial|never|reject、デフォルト instant）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

5. data ディレクトリの作成（必要なら）

   mkdir -p data

DB 初期化は run_monitoring / run_execution 実行時に自動で行われます（init_monitoring_db を呼び出すため）。DuckDB は指定パスにファイルを作成します。

## 使い方（代表的な起動方法）

- 監視プロセスの起動（Monitoring）

  環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定できます（デフォルト 60 秒）。監視は本番の sqlite_path を使います（KABUSYS_ENV に依存しない挙動）。

  実行例:

  python -m kabusys.run_monitoring

  停止方法:
  - Ctrl+C（KeyboardInterrupt）
  - またはプロジェクトルートの data/stop_requested.flag を作成するとループが検知して終了します。

- ExecutionEngine の起動（発注エンジン）

  KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用の SQLite（デフォルト data/paper_trading.db）に書き込みます。ライブ環境では実ブローカークライアントを使います。

  実行例:

  python -m kabusys.run_execution

  停止方法:
  - 停止フラグ（data/stop_requested.flag）を作成するとエンジンに停止信号が送られる設計です。
  - kill.flag（Settings.kill_flag_path）を生成する KillSwitch により、特定条件で ExecutionEngine を停止させることが可能です。

- Streamlit 監視ダッシュボード

  Streamlit を用いて監視データを可視化できます。コマンド例（コード内ヘルプ参照）:

  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート

  Paper Trading 用 SQLite を読み取って指標（稼働率 / 注文成功率 / レイテンシ等）を出力します。

  実行例:

  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI モジュール （ニュース評価 / レジーム判定）

  両モジュールは OpenAI API キー（OPENAI_API_KEY）を要求します。score_news / score_regime の呼び出しはライブラリ API を通じて行います（詳細はコード参照）。

## 重要なファイル・フラグ

- data/stop_requested.flag
  - run_monitoring / run_execution のループ停止用フラグ（存在を検知して優雅に終了）

- data/kill.flag
  - KillSwitch により書き込まれる実行停止フラグ（ExecutionEngine 側で検知して安全停止させる）

- data/execution.pid（デフォルト）
  - ExecutionEngine の PID 管理に使用（SystemMonitor は pid ファイルの stale 判定を行う）

- SQLite / DuckDB
  - デフォルト:
    - Monitoring SQLite: data/monitoring.db（Settings.sqlite_path）
    - Paper Trading SQLite: data/paper_trading.db（Settings.paper_sqlite_path）
    - DuckDB: data/kabusys.duckdb（Settings.duckdb_path）

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み機能含む）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・読み書きラッパ
    - system_monitor.py — システム (CPU/メモリ/ディスク/プロセス/データ鮮度) 監視
    - trade_monitor.py — 注文滞留 / 約定異常検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の作成・管理
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード起動スクリプト
  - execution/
    - order_manager.py, order_repository.py, reconciler.py 等 — 発注／DB／リコンシリエーション関連
    - execution_engine.py, broker_factory.py 等 （発注エンジン・ブローカー抽象）
  - portfolio/
    - portfolio_builder.py — 候補選定・等重/スコア加重
    - position_sizing.py — 株数決定・集約キャップ・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — OpenAI を使ったニュースセンチメント集計・書込
    - regime_detector.py — MA + マクロセンチメントでレジーム判定
  - data/ （リポジトリ外 or ルートに手動で作成）
    - monitoring.db, kabusys.duckdb, paper_trading.db など

（上記は主要ファイルのみ抜粋。実際の repo にはさらに細かなモジュールがあります。）

## 環境変数／設定の注意点

- .env / .env.local による自動読み込みが行われます（config._find_project_root() がプロジェクトルートを自動判別）。
- 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
- Settings クラスで必須とされる変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定だと例外を発生させます。必要に応じて .env を準備してください。
- PAPER_FILL_MODE（paper_trading のモック約定モード）は "instant"|"partial"|"never"|"reject" のいずれかでなければなりません。

## 運用に関する補足

- 監視ループ（run_monitoring）は環境に関係なく「本番の」sqlite_path を参照して監視ログを保存します。Paper Trading の監視も必要に応じて別 DB を参照する設計にできますが、現状の run_monitoring は settings.sqlite_path（本番）を使います。
- ExecutionEngine は KABUSYS_ENV によって paper_trading 用の専用 DB（PAPER_TRADING_SQLITE_PATH）を使用するので、本番 DB と明確に分離できます。
- KillSwitch による kill.flag の生成は冪等（既存ファイルがあれば再書き込みなし）です。
- MonitoringDB は既存 DB に対してマイグレーション（カラム追加）を行うロジックを持ちます（例: trade_logs.latency_ms, dashboard.peak_value の追加）。

## 開発／拡張のヒント

- OpenAI 呼び出し部分はリトライや JSON mode を使った堅牢化が施されています。テスト時は内部関数（_call_openai_api）をモックするとよいです。
- DuckDB を使ったリサーチ部分は SQL と Python を組み合わせて実装されています。prices_daily / raw_financials / raw_news 等のテーブルスキーマに依存します。
- ExecutionEngine 側はブローカー抽象を採っているため、実ブローカークライアントと MockBrokerClient を BrokerClientFactory 経由で切り替えられます。

---

不明点や README に追加したい情報（例: 実行時のログ例、requirements.txt の正確な内容、データスキーマ定義等）があれば教えてください。必要に応じて運用手順やデプロイ手順（systemd / supervisor / docker-compose など）も追記できます。