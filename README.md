README
======

概要
----
KabuSys は日本株の自動売買および関連ツール群をまとめた軽量フレームワークです。  
主な目的は、戦略によるシグナル生成から発注、運用監視、Paper Trading の検証、研究向けのファクター計算、ニュースの自然言語処理（LLM）を用いたセンチメント解析までを一貫してサポートすることです。

本リポジトリに含まれる主なコンポーネント:
- ExecutionEngine（発注エンジン）と OrderManager / Reconciler（再同期機能）
- Monitoring（システム状態・注文状況・リスク監視・アラート）
- Portfolio モジュール（銘柄選定、重み計算、株数算出）
- Research モジュール（ファクター計算、将来リターン、IC 等）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- Utilities（プロセス優先度・CPU affinity など）
- CLI / スクリプト（監視ループ起動、エンジン起動、Paper Trading レポート、Streamlit ダッシュボード）

機能一覧
--------
主な機能の抜粋:
- 実運用/Paper Trading の実行エンジン起動（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に完全分離して記録
  - プロセス優先度自動設定、PID ファイル管理、停止フラグ対応
- 監視（run_monitoring.py / MonitoringEngine）
  - CPU / メモリ / ディスク使用率、プロセス生存、データ鮮度の監視
  - 注文滞留・約定異常価格の検出、ドローダウン・ポジション制限の監視
  - kill.flag による停止シグナル出力、LINE へのプッシュ通知（AlertManager）
  - Streamlit ダッシュボードによる可視化（streamlit_dashboard.py）
- Portfolio 構築ユーティリティ
  - 候補選定、等分/スコア重み、セクター上限適用、ポジションサイズ計算（単元丸め・スケールダウンロジック）
- Research / Factor 計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
  - 将来リターン計算、IC（Spearman）や統計サマリ
- AI（OpenAI）連携
  - ニュースを LLM（gpt-4o-mini 等）で評価し ai_scores に格納（バッチ、リトライ、レスポンスバリデーション）
  - マクロニュースとETFのMA200乖離を合成して市場レジーム判定
- Paper Trading 検証レポート生成
  - 注文成功率、送信率、P95 レイテンシ、稼働率などを集計して PASS/FAIL 判定を出力

セットアップ手順
----------------
前提:
- Python 3.10 以上を推奨
- DuckDB, psutil, requests, openai, streamlit などが必要（下記は例）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（requirements.txt がない場合は手動で）
   - pip install duckdb psutil requests openai streamlit

3. プロジェクトルートに data ディレクトリを作成
   - mkdir -p data

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くか、必要な値を OS 環境変数として設定します。
   - 自動 .env 読み込みは既定で有効。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須の環境変数（最低限）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（Settings.jquants_refresh_token）
- KABU_API_PASSWORD — kabu ステーション API パスワード
- OPENAI_API_KEY — OpenAI API を使用する場合

有用な環境変数（デフォルトあり）
- KABUSYS_ENV — 環境: development / paper_trading / live （デフォルト: development）
- PAPER_FILL_MODE — Paper Trading の約定モード: instant / partial / never / reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視のポーリング間隔（秒、デフォルト: 60）

.env の簡易例 (.env)
- JQUANTS_REFRESH_TOKEN=your_token
- KABU_API_PASSWORD=your_password
- OPENAI_API_KEY=sk-...
- KABUSYS_ENV=development
- PAPER_FILL_MODE=instant
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- LOG_LEVEL=INFO

使い方（主要スクリプト）
-----------------------

1) 監視ループ起動（Monitoring）
- デフォルトのポーリング間隔は 60 秒。変更するには MONITOR_POLL_INTERVAL を設定。
- 実行:
  - python -m kabusys.run_monitoring
- 監視プロセスは Settings.sqlite_path（監視用 DB）にログを書きます。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（意図的）。

2) エンジン起動（ExecutionEngine）
- Paper Trading 時は KABUSYS_ENV=paper_trading と設定すると専用の paper_sqlite_path を使用し MockBrokerClient を使います。
- 実行:
  - python -m kabusys.run_execution
- 起動時に data/execution.pid が作成され、stop フラグ（data/stop_requested.flag）や kill.flag（Settings.kill_flag_path）で停止できます。

3) Paper Trading 検証レポート
- data/paper_trading.db を参照して期間集計を行います。
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パス上書き可能

4) Streamlit ダッシュボード（監視の可視化）
- 実行例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only モードで SQLite を開きます。MonitoringEngine がデータを書き込んでいる前提です。

5) AI / レジーム・ニューススコアリング
- OpenAI API キーを環境変数 OPENAI_API_KEY に設定して、kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出します。
- LLM 呼び出しはバッチ処理・リトライ・レスポンス検証を行います。失敗時はフェイルセーフ（スコア=0 等）で継続します。

運用・停止
- stop のためのフラグ:
  - data/stop_requested.flag — run_monitoring / run_execution が監視している停止フラグ（存在を検知するとループを終了）
  - kill.flag（Settings.kill_flag_path）— KillSwitch が書き込む停止フラグ（ExecutionEngine に停止指示）
- kill.flag の確認・削除は KillSwitch API を通じてまたはファイル操作で行えます。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に既存フラグを自動クリアできます。

ディレクトリ構成（主要ファイル／パッケージ）
---------------------------------------
src/kabusys/
- __init__.py (パッケージ定義、バージョン)
- config.py — 環境変数読み込み・Settings 定義（.env 自動ロード、必須チェック）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

subpackages:
- ai/
  - news_nlp.py — ニュースを LLM でセンチメント化し ai_scores に格納
  - regime_detector.py — マクロ新聞 + ETF MA200 乖離で市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite への永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション数監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - alert_manager.py — LINE への通知実装
  - monitoring_engine.py — 複数モニタを束ねるループ
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- execution/
  - order_manager.py, reconciler.py, order_repository.py, execution_engine.py, broker_factory.py, ...
  - 発注ロジックとブローカー抽象
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数・投資額計算（単元丸め・スケーリング）
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート出力ツール
- utils/
  - process_priority.py — プロセス優先度と CPU affinity 設定ユーティリティ
- data/ (プロジェクトルートに作成する想定)
  - monitoring.db（監視用 SQLite、デフォルト）
  - paper_trading.db（Paper Trading 用 SQLite）
  - kabusys.duckdb（DuckDB ファイル）
  - execution.pid / stop_requested.flag / kill.flag など

実装上の注意点
--------------
- Settings（config.py）は .env を自動で読み込みますが、OS の環境変数を保護する仕組みになっています。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring の init_monitoring_db() は冪等的にテーブル・インデックスを作成します。既存 DB のマイグレーション（列追加）も実装されています。
- Monitoring は環境（KABUSYS_ENV）にかかわらず、監視用の sqlite_path を参照します（運用上の意図）。
- Paper Trading は本番 DB とデータを完全分離するため settings.is_paper の場合は paper_sqlite_path を使用します。
- OpenAI 連携は API キーが必須です。外部 API 呼び出しはリトライとバックオフ、レスポンスバリデーションを行い、失敗に対してはフェイルセーフ設計です。
- process_priority / set_cpu_affinity は psutil を使用します。権限がない場合は警告を出してスキップします。

トラブルシューティング（簡易）
-----------------------------
- DB が開けない/ファイルがない:
  - data ディレクトリと設定した DB パスが存在するかを確認してください。
- OpenAI 呼び出しでエラーが続く:
  - OPENAI_API_KEY が正しいか、API のレート制限にかかっていないか確認してください。news_nlp はリトライを行いますが、失敗時は該当チャンクをスキップします。
- 実行プロセスがすぐに停止する:
  - data/stop_requested.flag が存在していないか確認してください。

開発メモ
--------
- DuckDB を使った研究用クエリは prices_daily / raw_financials / raw_news 等のテーブルを前提としています。レコード形式や日付の取り扱いはモジュールの docstring を参照してください。
- ユニットテストや CI は本リポジトリに含まれていませんが、各モジュールは pure function として切り出されている箇所が多いので、個別テストが書きやすい設計です。

ライセンス / 貢献
-----------------
- 本 README は実装の抜粋に基づく説明です。実際のライセンスや貢献ルールがプロジェクトにある場合はそれに従ってください。

以上。必要があれば、インストール用の requirements.txt や .env.example、起動スクリプトの systemd ユニット例、または運用手順書（Runbook）を作成します。どれが必要か教えてください。