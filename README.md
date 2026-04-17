KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。取引実行（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築、ファクター研究、ニュース NLP によるセンチメント評価など、実運用を想定したコンポーネント群を含みます。  
設計方針として「本番側の注文処理とは分離した paper trading モード」「DuckDB を用いたリサーチ」「OpenAI によるニュース解析（任意）」などが採用されています。

主な特徴
--------
- ExecutionEngine（発注・注文状態管理・リスク管理・再同期）
  - 本番 / paper_trading（モックブローカー）を切り替え可能
  - Reconciler による起動時の注文/ポジション同期
- Monitoring（system / trade / risk モニタ）
  - system: CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade: 滞留注文（stale）・約定価格異常検出
  - risk: ドローダウンやポジション上限の監視と kill flag 書き込み
  - LINE Push によるアラート送信（AlertManager）
  - Streamlit ダッシュボード用のエントリポイントを準備
- Portfolio モジュール（候補選定・重み算出・ポジションサイズ計算・セクター制限）
  - 等金額 / スコア加重 / リスクベース等の配分方式をサポート
- Research（DuckDB ベースのファクター計算／特徴量解析）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン、IC、ファクター統計量の算出ユーティリティ
- AI （ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini 等）でニュースをスコアリングし ai_scores に書き込み
  - マクロニュース + ETF MA200 乖離から市場レジーム判定
  - API 呼び出しは冗長制御・バックオフを実装（フェイルセーフ設計）
- 運用ユーティリティ
  - process priority / cpu affinity 設定ユーティリティ
  - paper trading の検証レポート生成ツール

セットアップ手順
----------------
前提
- Python 3.10+ を推奨（typing や依存ライブラリの互換性のため）
- SQLite（標準ライブラリ）およびファイル書き込み権限

1. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. プロジェクトルートに .env を用意（任意）
   - リポジトリに .env.example がある場合は参考に作成
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

主要な環境変数（代表）
- KABUSYS_ENV: 実行モード（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須の場合あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（本番接続時必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時必須）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject） — デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite ファイルパス（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒。run_monitoring で参照）

ファイル・権限について
- data ディレクトリ（デフォルト）に DB や PID / フラグファイルを作成します。実行ユーザに書き込み権限があることを確認してください。

使い方
------
1. ExecutionEngine を起動する
- 本番／paper_trading の切り替え:
  - paper_trading モード例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading 時は MockBrokerClient を使い、別 DB (data/paper_trading.db) に記録します（本番 DB と分離）
  - 本番モード例:
    - KABUSYS_ENV=live python -m kabusys.run_execution

- 実行時の挙動:
  - 起動時に process priority を "high" にし、DB を接続します
  - 停止は外部から data/stop_requested.flag を作成すると実行ループが終了します
  - ExecutionEngine は data/execution.pid (デフォルト) に PID を書きます

2. MonitoringEngine を起動する
- python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を調整できます（デフォルト 60 秒）
- 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず監視 DB は本番パス）
- 監視ループの停止も data/stop_requested.flag によって行われます

3. Streamlit ダッシュボード（監視用）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードは読み取り専用で DB を開きます（監視プロセスで書き込み中でも可）

4. Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 別 DB 指定:
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

5. AI 関連（ニュース NLP / レジーム判定）
- OpenAI API キー（OPENAI_API_KEY）が必要
- news_nlp.score_news(conn, target_date, api_key) や regime_detector.score_regime(conn, target_date, api_key) をスクリプトやジョブから呼び出して利用できます
- API 呼び出しはバックオフ・リトライを備え、失敗時は安全側のデフォルトで継続する設計です

停止・キルの仕組み
- run_execution.py / run_monitoring.py はプロジェクト内の data/stop_requested.flag を監視します。ファイルが存在するとループを終了します（運用上の安全な停止方法）。
- KillSwitch（監視側）は条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止指示を与える運用を想定しています（実際の Engine 側は kill.flag を検出して停止処理を行います）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数/.env の読み込みと Settings
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring ポーリング起動スクリプト

サブパッケージ（主要）
- execution/
  - order_manager.py
  - reconciler.py
  - (その他 broker_factory, execution_engine, order_repository 等)
  - 役割: ブローカーインタフェース、注文状態管理、実行エンジン
- monitoring/
  - monitoring_db.py         — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - 役割: 銘柄選定、重み付け、株数決定、セクター制限・レジーム調整
- research/
  - factor_research.py
  - feature_exploration.py
  - 役割: DuckDB ベースのファクター計算・IC・統計ユーティリティ
- ai/
  - news_nlp.py              — OpenAI を使ったニュースセンチメント集約／ai_scores 書き込み
  - regime_detector.py       — MA200 とマクロセンチメントで日次レジーム判定
- tools/
  - paper_verification_report.py — paper_trading の検証レポート出力スクリプト
- utils/
  - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ
- data/                      — 実行時に生成される DB / PID / flag ファイルを置く想定ディレクトリ（デフォルト）

運用上の注意点
-------------
- paper_trading モードは本番 DB と完全分離されますが、設定によりファイルパスを上書きできます。運用時はパスを必ず確認してください。
- OpenAI 等の外部 API を利用する機能は API キー漏洩に注意し、利用量・コストの管理を行ってください。
- monitoring_db.init_monitoring_db は既存 DB に対して必要なマイグレーション（列追加など）を冪等で試みますが、重大なスキーマ変更時はバックアップを推奨します。
- process priority / cpu affinity の設定はプラットフォーム依存で失敗する場合があるため、ログで警告が出ても致命的ではありません。

開発・拡張ガイド（短く）
-----------------------
- DuckDB を使ったデータフェーズ（research）と、SQLite を使った実行/監視ログは明確に分離されています。新しいリサーチ機能は DuckDB の prices_daily / raw_financials 等テーブルを参照して実装してください。
- ブローカー実装は BrokerAPIProtocol を実装することで差し替え可能です（MockBrokerClient をテスト/検証用に提供）。
- AI 呼び出し部分は _call_openai_api 等を patch / mock することで単体テスト可能に設計されています。

問い合わせ・貢献
----------------
バグ報告や機能提案は Issue を通してください。プルリク歓迎です。開発者向けにテストや CI、requirements の整備を進めると導入が容易になります。

---
この README はリポジトリ内の主要モジュールを元に作成しています。実行前に .env の確認、data ディレクトリの作成、および必要なパッケージのインストールを行ってください。