KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買およびリサーチ基盤です。本リポジトリは以下の機能群を含みます：

- 注文作成・発注・状態管理を行う ExecutionEngine
- システム稼働状況・注文異常・リスク監視の Monitoring
- ポートフォリオ構築（候補選定・重み付け・株数計算）
- ファクター計算・リサーチヘルパー（DuckDB を使用）
- ニュースを LLM（OpenAI）で評価する AI モジュール（ニュース NLP / レジーム判定）
- Paper Trading 用の検証ツール・レポート、Streamlit ダッシュボード

この README はプロジェクトの利用開始方法、主要コンポーネント、実行例、ディレクトリ構成をまとめています。

主な機能
--------
- ExecutionEngine
  - ブローカークライアントを抽象化し、本番 / Paper Trading の切替をサポート
  - リスク管理（ポジション上限、最大投下率、ドローダウン等）
  - 再起動時のリコンシリエーション（注文・ポジション同期）
- Monitoring
  - システムリソース（CPU/メモリ/ディスク）と Execution プロセスの監視
  - 注文滞留 / 約定価格の異常検知
  - リスクイベント記録（risk_logs）とダッシュボード更新
  - Kill Switch（閾値到達時に data/kill.flag を書き込み Execution を停止）
  - Streamlit による監視ダッシュボード
- Portfolio コンポーネント（純粋関数群）
  - 候補選定、等重・スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）
  - 単元株丸め・利用可能現金に合わせた株数決定
- Research / Factor
  - DuckDB を用いたモメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）や統計サマリ
- AI（OpenAI）
  - ニュースのセンチメント集約（ai_scores テーブルへ書き込み）
  - マクロニュース + ETF (1321) MA200乖離を使った市場レジーム判定（market_regime テーブル）
  - API 呼び出しは冪等・フェイルセーフ設計（リトライ、部分失敗の保護）
- ツール
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）
  - streamlit_dashboard: 監視 DB を参照する UI

セットアップ手順
----------------

前提
- Python 3.10+
- Git
- システムに sqlite3 は標準で含まれます
- 必要ライブラリ（下記参照）

仮想環境作成（推奨）
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\Scripts\activate)

依存ライブラリのインストール（例）
- pip install duckdb psutil requests openai streamlit
- （将来的に requirements.txt がある場合は pip install -r requirements.txt を使用）

環境変数 / .env
- プロジェクトルートの .env/.env.local を自動で読み込みます（OS 環境変数が優先）
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（必須 / 任意）
- 必須（稼働に必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必要であれば）
  - KABU_API_PASSWORD — kabuステーションAPIパスワード
- OpenAI
  - OPENAI_API_KEY — ニュース NLP / レジーム判定で利用
- 実行環境切替
  - KABUSYS_ENV — development | paper_trading | live （デフォルト: development）
    - paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に書き込みます（本番 DB と分離）
- Paper Trading 設定
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB パス（デフォルト: data/paper_trading.db）
- DB パス
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- ログ / PID / フラグ
  - PID_FILE_PATH — ExecutionEngine の pid ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch のフラグパス（デフォルト: data/kill.flag）
- モニタリング間隔
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）

初期 DB 作成
- 監視テーブル等は run_execution.run や run_monitoring.main 内で init_monitoring_db() によって自動作成されます。
- DuckDB のテーブル（prices_daily, raw_news 等）はデータ収集パイプライン側での準備が必要です（この README に含まれない ETL コンポーネントを想定）。

実行方法
--------

Execution Engine（注文実行）
- 本番（またはデフォルト）
  - KABUSYS_ENV=live python -m kabusys.run_execution
- Paper Trading（Mock ブローカー、専用 DB）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 実行前に必要な環境変数（KABU_API_PASSWORD 等）を設定してください。
- 実行中は data/execution.pid に PID が書き込まれ、停止は data/stop_requested.flag（run_execution のループが検知）または data/kill.flag（Kill Switch）で行えます。

Monitoring（監視ループ）
- python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可（例: export MONITOR_POLL_INTERVAL=30）
- 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します
- 停止は data/stop_requested.flag を作成するか Ctrl+C

Streamlit ダッシュボード
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 監視 DB を read-only で開き、Overview / Positions / Orders / System のタブを表示します。

Paper Trading 検証レポート
- 起動:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH の代替）
- 出力: 稼働率・注文成功率・送信率・レイテンシ（P95）等のサマリと PASS/FAIL 判定

AI 機能（ニューススコア / レジーム判定）
- ニューススコア（ai_scores へ書き込み）
  - kabusys.ai.score_news を呼び出し。OpenAI API キーが必要。
- レジーム判定（market_regime へ書き込み）
  - kabusys.ai.regime_detector.score_regime を呼び出し。OpenAI API キーが必要。
- 両機能とも API の部分失敗に対するリトライ・フェイルセーフを備えています。

停止・Kill 操作
- 手動で ExecutionEngine を停止したい場合:
  - data/stop_requested.flag を作成すると run_execution が検出して停止します
  - Kill Switch（監視による自動停止）は data/kill.flag を書き込みます
- kill.flag のクリア:
  - 実行前に KillSwitch.clear() を呼ぶかファイルを削除してください

開発時の注意事項
- Settings モジュールはプロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を自動読み込みします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Python の型ヒントに 3.10 の構文（|）を使用しているため Python 3.10 以上を推奨します。
- OpenAI 利用部分は外部 API へ依存するため、API キーと利用制限に注意してください。

ディレクトリ構成（抜粋）
---------------------
下記は当リポジトリ内の主要ファイル／モジュール一覧（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — システム監視ループ起動スクリプト
  - data/                    — 実行時に使うファイル（db, pid, flag 等）
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py     —（エンジン本体、他ファイルあり）
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - ... (その他 Execution 関連)
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - monitoring/ (再掲) — DB / ログ / アラート周り

よくある質問 / Tips
-------------------
- DB スキーマは init_monitoring_db() によって必要なテーブルを自動作成します。既存 DB に対する簡易マイグレーション（列追加）も含まれます。
- Paper Trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- run_execution/run_monitoring はプロセス優先度を high に設定しようとします（psutil による実装）。権限により失敗する場合はログに警告が出て継続します。
- Streamlit ダッシュボードは監視 DB を read-only で開きます。監視デーモンを起動していないとデータは空のことがあります。

ライセンス・貢献
----------------
（ここにライセンス表記・貢献ガイドラインを追記してください）

サポート
-------
不明点や実行上のトラブルがあれば、使用している環境（OS、Python バージョン、主要な環境変数、実行コマンドとログ）を添えて問い合わせてください。

以上。必要であれば README にサンプル .env.example、requirements.txt、起動スクリプトの systemd ユニット例、より詳細なアーキテクチャ図などを追加できます。どの情報を追記しますか？