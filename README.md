README
======

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした Python ベースの小規模なシステムです。本コードベースは以下の主要機能を含みます。

- 注文発行・管理（ExecutionEngine / OrderManager）
- 取引ログ・監視（MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor）
- ポートフォリオ構築・サイズ計算（portfolio モジュール）
- リサーチ用ファクター計算（research）
- ニュース NLP（OpenAI を用いたセンチメントスコア算出）
- 市場レジーム判定（regime_detector）
- Paper Trading 検証用レポート生成ツール
- Streamlit による監視ダッシュボード

主な特徴
--------
- 設定は環境変数（.env / .env.local の自動ロードをサポート）で管理
- 本番・Paper Trading 環境を分離（DB パス等を切り替え）
- DuckDB を用いた履歴・ファクター計算、SQLite を監視ログ/注文ログに使用
- OpenAI（gpt-4o-mini 等）を使ったニュース解析・レジーム判定（API キー必須）
- プロセス優先度設定・CPU affinity ユーティリティ（Windows / POSIX 対応）

前提条件
--------
- Python 3.10+（typing の一部表記を含むため）
- 必要パッケージ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- （任意）virtualenv / venv の利用を推奨

セットアップ手順
----------------
1. リポジトリをクローン／配置
   - プロジェクトルート（pyproject.toml または .git があるディレクトリ）が自動検出に使われます。

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 例:
     pip install duckdb psutil requests openai streamlit

   （プロジェクトが requirements.txt を提供していない場合は上記の主要パッケージをインストールしてください）

4. 環境変数設定
   - プロジェクトルートに .env を作成するか、必要な環境変数を OS 側に設定します。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主な環境変数（代表）
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp, regime_detector 使用時に必須）
- PAPER_FILL_MODE: Paper Trading の約定ルール（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB パス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH, その他監視閾値（CPU_THRESHOLD_PCT 等）

使い方
------
以下は代表的な実行例です。いずれのスクリプトもパッケージのモジュールとして実行できます。

1. 監視ループの起動 (Monitoring)
   - デフォルトではプロセス優先度を "high" に設定し、SQLite の監視 DB を初期化してポーリングを行います。
   - 実行:
     python -m kabusys.run_monitoring
   - ポーリング間隔を変更する:
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     （単位: 秒。1 未満の値や 0 は無効扱いされデフォルト 60 秒にフォールバック）
   - 停止:
     - プロジェクトルートの data/stop_requested.flag ファイルを作成するとループは検出して終了します。

2. ExecutionEngine の起動（発注エンジン）
   - 実行:
     python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient が使われ、Paper Trading 専用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
   - 起動前に data/stop_requested.flag が存在する場合、起動せずに終了します。
   - 実行中に停止させたい場合は data/stop_requested.flag を作成すると ExecutionEngine が検出して停止処理を行います。

3. Streamlit ダッシュボード（監視表示）
   - 実行:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは監視 DB を読み取り専用で開き、ポートフォリオ集計・ポジション・最近の注文・システム状態・リスクログを表示します。

4. Paper Trading 検証レポート生成
   - 実行:
     python -m kabusys.tools.paper_verification_report
   - 期間を指定:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルトの DB パスは data/paper_trading.db。--db オプションまたは PAPER_TRADING_SQLITE_PATH 環境変数で指定できます。

5. AI（ニュース NLP / レジーム判定）
   - news_nlp.score_news / regime_detector.score_regime は OpenAI API を利用します。
   - 実行には OPENAI_API_KEY が環境変数か引数で必要です。
   - これらはライブラリ関数として呼び出す設計（CLI の簡易ラッパーは含まれていません）。例:
     from kabusys.ai.news_nlp import score_news
     score_news(duckdb_conn, target_date, api_key="sk-...")

運用上の注意
-------------
- 監視（monitoring）は Settings.env にかかわらず本番 sqlite_path を使用して監視ログを書きます（run_monitoring 内の設計）。
- ExecutionEngine は paper_trading 環境で DB を分離します（PAPER_TRADING_SQLITE_PATH を使用）。
- kill flag（Settings.kill_flag_path = data/kill.flag による停止シグナル）:
  - KillSwitch はリスクイベント（ドローダウンやポジション上限）に応じて kill.flag を書き、ExecutionEngine の停止をトリガーします。kill.flag の存在は再起動時にクリーンアップが必要です（Settings.kill_flag_clear_on_start オプションで起動時に自動クリア設定可能）。
- OpenAI を利用する機能は API 失敗時にフォールバックや一部スキップを行うよう設計されていますが、API キーとコスト管理に注意してください。
- process_priority.set_process_priority は Windows と POSIX で実装が分かれています。権限不足や未対応 OS の場合は警告を出して継続します。

主要ファイル / コマンド一覧
---------------------------
- 実行スクリプト
  - src/kabusys/run_monitoring.py     — 監視ループ起動
  - src/kabusys/run_execution.py      — ExecutionEngine 起動

- ツール
  - src/kabusys/tools/paper_verification_report.py — Paper Trading レポート
  - src/kabusys/monitoring/streamlit_dashboard.py — Streamlit ダッシュボード

- 主要モジュール
  - kabusys/config.py                  — 環境変数/設定管理（.env 自動ロード機能）
  - kabusys/monitoring/*               — 監視関連（MonitoringDB, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager, MonitoringEngine）
  - kabusys/execution/*                — 注文・リコンシリエーション等（OrderManager, Reconciler, ExecutionEngine など）
  - kabusys/portfolio/*                — 銘柄選定・重み・サイズ計算
  - kabusys/research/*                 — ファクター計算・特徴量探索
  - kabusys/ai/*                       — news_nlp, regime_detector（OpenAI 利用）
  - kabusys/utils/*                    — process priority 等のユーティリティ

ディレクトリ構成（抜粋）
--------------------
src/
  kabusys/
    __init__.py
    config.py
    run_monitoring.py
    run_execution.py
    tools/
      __init__.py
      paper_verification_report.py
    monitoring/
      __init__.py
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
    execution/
      order_manager.py
      reconciler.py
      ...（broker, engine, repository 等）
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py
    research/
      factor_research.py
      feature_exploration.py
      __init__.py
    ai/
      news_nlp.py
      regime_detector.py
      __init__.py
    utils/
      process_priority.py
      __init__.py
    data/  (実行時に生成・使用されるファイル例)
      monitoring.db
      kabusys.duckdb
      paper_trading.db
      execution.pid
      stop_requested.flag
      kill.flag

設計上の注記 / 開発メモ
---------------------
- Settings モジュールはプロジェクトルートを .git / pyproject.toml で探索して .env を自動読み込みします。テスト時や特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効にできます。
- DuckDB ベースのリサーチ機能は prices_daily / raw_financials / raw_news テーブルに依存しており、これらの準備（ETL）なしにはファクター計算や AI スコアリングは動作しません。
- 監視 DB のスキーマ変更（マイグレーション）は monitoring_db.init_monitoring_db 内で簡易的に扱われています（既存列がなければ ALTER TABLE で追加する処理あり）。
- OpenAI 呼び出しは比較的保守的なリトライ・レスポンス検証を行う設計です。テスト時は _call_openai_api をモックすることを想定しています。

ライセンス / 貢献
----------------
（この README にはライセンス情報は含まれていません。必要に応じてプロジェクトに LICENSE ファイルを追加してください。）

サポート / 問い合わせ
--------------------
実装上の細かい動作や拡張についてはソースコード内の docstring / コメントに詳細が書かれています。まずは該当モジュールの docstring を参照してください。質問がある場合は開発チームへお問い合わせください。