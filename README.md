# KabuSys

KabuSys は日本株向けの自動売買／リサーチ／監視ツール群です。  
このリポジトリは、エンジン（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI を利用）などの主要コンポーネントを含みます。

以下はこのコードベースの概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

- 目的: 日本株の自動売買を支える実行エンジン、監視システム、研究用モジュールを提供する。
- 特長:
  - ExecutionEngine / OrderManager / Reconciler による発注・状態管理と起動時リコンシリエーション
  - MonitoringEngine によるシステム稼働・注文・リスク監視、LINE 通知
  - DuckDB を用いた時系列データ処理・ファクター計算（research モジュール）
  - OpenAI を利用したニュースセンチメント評価（ai.news_nlp）とレジーム判定（ai.regime_detector）
  - Paper Trading モード（本番 DB と分離）と検証レポート生成ツール

---

## 機能一覧

- 実行（Execution）
  - 注文作成・送信・状態同期（OrderManager, OrderRepository）
  - ブローカー抽象化（BrokerClientFactory）
  - 起動時の自動リコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
- 監視（Monitoring）
  - システムリソース監視（CPU/メモリ/ディスク）
  - Execution プロセス生存チェックと stale PID 検出
  - 注文滞留・約定価格異常の検出（TradeMonitor）
  - ドローダウン・ポジション上限アラート（RiskMonitor）
  - Kill Switch（条件を満たしたら data/kill.flag を作成して実行エンジンを停止）
  - LINE によるアラート送信（AlertManager）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- 研究（Research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、統計サマリ（feature_exploration）
- ポートフォリオ構築（Portfolio）
  - 候補選定、等ウェイト/スコア加重、ポジションサイズ計算
  - セクターキャップ・レジーム乗数の適用
- AI（OpenAI 連携）
  - ニュースを LLM でスコアリングして ai_scores に格納（news_nlp.score_news）
  - マクロニュース + ETF MA200 乖離から市場レジームを判定（regime_detector.score_regime）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発・実行環境）

1. 必要な Python バージョン
   - Python 3.9+ を推奨（typing | None の表記などを使用）

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリのインストール
   - pip install duckdb psutil openai requests streamlit
   - sqlite3 は標準ライブラリとして同梱（追加インストール不要）

   （実際のプロジェクトでは requirements.txt を用意することを推奨します）

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（OS 環境変数が優先）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 重要な環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV: execution/monitoring の挙動切替（development / paper_trading / live）. デフォルト: development
     - PAPER_FILL_MODE: paper trading の約定挙動（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - PID_FILE_PATH, KILL_FLAG_PATH: 各種パス（デフォルト設定あり）

5. データディレクトリ作成
   - data/ ディレクトリを作成しておく（pid/flag/db ファイルが格納されます）
   - mkdir -p data

---

## 使い方（主要コマンドと動作）

- 監視ループを起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を設定可能（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 動作: プロセス優先度を上げ、monitoring DB を初期化、SystemMonitor をポーリングして system_status 等を記録します。
  - 停止方法: Ctrl+C またはプロジェクトルートの data/stop_requested.flag を作成するとループを終了します。

- 実行エンジン（ExecutionEngine）を起動
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い、Paper Trading 用 DB（data/paper_trading.db）へ記録して本番 DB と分離します。
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作成するとエンジンに停止信号が送られます。

- Streamlit ダッシュボードを起動（監視 DB を読み取り専用で表示）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは positions / recent orders / latest system status / recent risk logs を表示します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニューススコア・レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB の raw_news / news_symbols / ai_scores を利用してニュースを LLM に渡し ai_scores に書き込む。OPENAI_API_KEY が必要。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 1321 の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime に書き込む。OPENAI_API_KEY が必要。

- Kill Switch / 手動フラグ
  - KillSwitch は評価結果に応じて data/kill.flag を作成します。ExecutionEngine 起動時に clear する設計（Settings.kill_flag_clear_on_start を参照）。
  - 手動で停止させたい場合は data/kill.flag を作成する、または data/stop_requested.flag を作成して監視スクリプト等に停止を通知します。

---

## 設定と挙動のポイント

- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml ベース）から `.env` / `.env.local` を読み込みます。OS 環境変数は保護（上書きされない）されます。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

- KABUSYS_ENV のモード
  - development: 開発用（デフォルト）
  - paper_trading: ブローカーは Mock、DB は paper_trading_db を使用して本番と分離
  - live: 本番モード

- DB 初期化
  - init_monitoring_db(conn) は冪等で監視用のテーブル（system_status, trade_logs, positions, risk_logs, dashboard）を作成します。run_monitoring / run_execution 内で自動的に呼ばれます。

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔を秒単位で指定（環境変数）。不正値または 0 以下はデフォルト 60 秒にフォールバックします。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite を用いた監視ログ永続化（init / MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込み / 管理
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - streamlit_dashboard.py — Streamlit を使ったダッシュボード
  - execution/
    - order_manager.py — 注文管理（OrderManager）
    - reconciler.py — 起動時の同期処理
    - order_repository.py, order_record.py, broker_factory.py, execution_engine.py 等（発注ロジック・ブローカー抽象）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリューの計算（DuckDB）
    - feature_exploration.py — forward returns, IC, 統計サマリ 等
  - ai/
    - news_nlp.py — OpenAI を用いたニュースセンチメント集計・書込
    - regime_detector.py — レジーム判定（MA200 と LLM の合成）
  - tools/
    - paper_verification_report.py — Paper Trading のレポート生成

- data/
  - monitoring.db (デフォルト) — 監視 SQLite
  - paper_trading.db (paper_trading モード時) — Paper Trading 用 DB
  - kabusys.duckdb (デフォルト DUCKDB_PATH)
  - stop_requested.flag, kill.flag, execution.pid などのランタイムフラグ/ファイル

---

## 開発上の注意点 / ベストプラクティス

- 環境変数は .env.example を参考にして安全に管理してください。必須のキー（JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD など）は Settings クラスが未設定時に例外を投げます。
- Paper Trading を使うと実際のブローカーとは完全に分離された DB に書き込まれます。検証・デバッグには paper_trading モードを推奨します。
- OpenAI を使用する機能は API キーが必要です。API コール失敗時はフェイルセーフとしてスコアをスキップしたりデフォルト値（0.0）で継続する設計になっていますが、レート制限には注意してください。
- monitoring / execution は外部プロセス（systemd や supervisor 等）で管理する想定です。プロセス優先度設定や PID ファイルの扱いに注意してください。
- DuckDB / prices_daily / raw_financials 等のデータ品質に依存するモジュール（research, ai, regime_detector）はルックアヘッドバイアスを避けるため target_date の扱いに注意しています。データ投入順序や日付範囲に気をつけてください。

---

## よく使うコマンドまとめ

- 監視起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Python REPL からモジュール呼び出し例:
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime

---

必要に応じて README を拡張して、実際の .env.example、requirements.txt、起動用 systemd ユニットのサンプル、テスト手順、CI 設定などを追加することを推奨します。必要ならテンプレートや追加のドキュメントを作成しますので指示ください。