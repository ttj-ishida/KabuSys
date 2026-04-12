KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買（バックテスト／実運用／Paper Trading）を想定した軽量な自動売買フレームワークです。本リポジトリは次を含みます:

- 注文管理・ExecutionEngine（ブローカー抽象化、再同期・リコンシリエーション）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング・リスク調整）
- 監視（System / Trade / Risk のモニタリング、監視 DB 保存、LINE 通知、kill flag）
- 研究用モジュール（ファクター計算、特徴量探索、IC 計算）
- AI 補助（ニュースセンチメント評価、レジーム判定：OpenAI を利用）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード等）
- 設定管理（.env パーサ、環境切替: development / paper_trading / live）

主な機能
--------
- ExecutionEngine（run_execution.py）
  - ブローカー抽象化（実口座／MockBroker for paper_trading）
  - 注文状態管理、再送・再同期（Reconciler）
  - リスク管理（RiskManager の設定に基づく制限）
- 監視（run_monitoring.py / MonitoringEngine）
  - システム状態（CPU/メモリ/ディスク、プロセス生存判定）
  - 注文状態監視（滞留注文、約定価格異常）
  - リスク監視（ドローダウン、ポジション上限）
  - kill.flag による ExecutionEngine の安全停止
  - LINE への通知（AlertManager）
  - 監視データを SQLite（data/monitoring.db 等）へ永続化
  - Streamlit ダッシュボードで可視化
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等金額 / スコア重み付け、リスクベースのポジション決定
  - セクター上限・レジーム乗数の適用
- 研究（kabusys.research）
  - Momentum / Volatility / Value 等のファクター算出（DuckDB 上の prices_daily/raw_financials を使用）
  - 将来リターン計算、IC（Spearman rank）や統計サマリー
- AI モジュール（kabusys.ai）
  - ニュース記事のセンチメントを OpenAI（gpt-4o-mini）でスコア化して ai_scores に保存
  - マクロニュースと ETF (1321) MA を組み合わせた市場レジーム判定
- 運用ツール
  - paper_verification_report: Paper Trading ログから運用可否レポート生成
  - streamlit_dashboard: 監視 DB を可視化するダッシュボード

セットアップ
-----------
前提
- Python 3.10+ を推奨（typing の記法・型注釈に依存）
- DuckDB, psutil, requests, openai, streamlit などのパッケージが必要

例: 仮想環境作成と依存インストール
- 仮想環境作成
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- 依存インストール（requirements.txt がある場合）
  - pip install -r requirements.txt
- 直接インストール（主要パッケージ例）
  - pip install duckdb psutil requests openai streamlit

環境変数 / .env
- 設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主な環境変数（重要なものを抜粋）:
  - KABUSYS_ENV: 開発環境。development | paper_trading | live（デフォルト: development）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject、デフォルト: instant）
  - PID_FILE_PATH / KILL_FLAG_PATH: PID / kill flag のパス（デフォルト: data/execution.pid, data/kill.flag）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

使い方
------
起動スクリプト
- ExecutionEngine を起動（通常運用／Paper Trading 自動切替）
  - python -m kabusys.run_execution
  - 動作: Settings に基づきブローカーを生成。paper_trading 環境なら MockBroker を使い PAPER_TRADING_SQLITE_PATH に記録します。
- Monitoring（監視ループ）を起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path を使用して監視データを永続化します（環境にかかわらず本番 sqlite_path を使用する設計）。
  - Ctrl+C で安全に停止します。

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - データベース指定:
    - --db /path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- Streamlit ダッシュボード（監視 DB を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 引数 --db で監視 DB を指定可能

研究・AI の実行（プログラム的に利用）
- research モジュールは DuckDB 接続を受け取り純粋関数でファクターや forward return を計算します（例: calc_momentum(conn, date)）。
- AI モジュールは OPENAI_API_KEY が必要です。関数を直接呼び出すことで ai_scores や market_regime を更新できます（例: kabusys.ai.score_news(conn, date)）。

監視・フェイルセーフ
- KillSwitch: RiskMonitor 等の結果に応じて data/kill.flag を作成。ExecutionEngine は起動時に kill.flag をチェック・クリアする設計になっています（Settings.kill_flag_clear_on_start を参照）。
- AlertManager は LINE push をサポート。トークン未設定時はログにて警告し送信はスキップします。

ディレクトリ構成（主なファイル説明）
----------------------------------
src/kabusys/
- __init__.py
  - パッケージ情報（__version__ 等）
- config.py
  - 環境変数の読み込み・検証、Settings クラス
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper_trading 処理）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で制御）
- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ（psutil ベース）
- execution/
  - order_manager.py, reconciler.py, order_repository.py, execution_engine.py 等
  - 注文管理、ブローカー抽象化、リコンシリエーション
- monitoring/
  - monitoring_db.py — SQLite による監視ログ永続化
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種モニタリング
  - monitoring_engine.py — 複数モニタをまとめるループ
  - alert_manager.py — LINE 通知
  - kill_switch.py — kill.flag 制御
  - streamlit_dashboard.py — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 候補選定・重み付け・ポジション算出
- research/
  - factor_research.py, feature_exploration.py — ファクター計算・IC・統計
- ai/
  - news_nlp.py — ニュースの LLM スコアリング（ai_scores への書込）
  - regime_detector.py — ETF MA + マクロニュースでレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
  - __init__.py

運用上の注意
------------
- OpenAI を使う機能は API キーを必要とします。API の呼び出し失敗時はフェイルセーフ（多くのケースでスコアを 0.0 にフォールバック）を採っていますが、レート制限やコストに注意してください。
- Paper Trading は本番 DB から分離するため、KABUSYS_ENV=paper_trading 時は PAPER_TRADING_SQLITE_PATH を使用します。運用データの混在に注意してください。
- Settings は起動時に .env / .env.local を自動読み込みします（CWD ではなくプロジェクトルートを探索）。テスト等で自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視専用 DB（settings.sqlite_path）を使用します。monitoring DB の初期化は init_monitoring_db() が行います（冪等処理）。

拡張・開発メモ
---------------
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）はデータ取得パイプラインで整備する想定です。research モジュールは DuckDB を直接参照します。
- position_sizing の lot_size は将来的に銘柄別に拡張可能な設計です。
- AI 呼び出し部分（news_nlp._call_openai_api / regime_detector._call_openai_api）はユニットテスト時にモック差し替えが想定されています。

お問い合わせ / 貢献
------------------
- バグ報告や修正提案は issue / pull request を通してお願いします。
- 開発中の設計意図は各モジュールの docstring に詳細が含まれています。まずは該当ソースを参照してから実装・修正してください。

以上がこのコードベースの README 相当の概要です。必要であれば「環境変数の完全な一覧」「pip 用 requirements.txt の候補」「実行例スクリプト（systemd / docker-compose）」などを追加で作成します。どれを優先しますか？