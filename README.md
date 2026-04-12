KabuSys
======

日本株自動売買システムのコードベース（抜粋）向け README。  
このドキュメントはリポジトリ内の主要モジュールをもとに、プロジェクト概要、機能、セットアップ手順、実行例、ディレクトリ構成を日本語でまとめたものです。

概要
----
KabuSys は日本株の自動売買システムのコンポーネント群（実行エンジン、監視、リサーチ、ポートフォリオ構築、AI ベースのニュース解析等）を含む Python パッケージです。  
設計方針の例として、以下が挙げられます。

- 環境依存の設定は環境変数 / .env ファイルから読み込む（自動ロード機能あり。無効化可能）。
- DuckDB／SQLite を用いた時系列・ログ保存と分析。
- 実行（ExecutionEngine）と監視（MonitoringEngine）はプロセス優先度調整や PID / kill-flag を用いて安全運用を支援。
- Paper Trading モードで本番 DB と分離して検証可能。
- OpenAI 等の外部 API を用いたニュース NLP、レジーム判定機能を搭載（APIキー必要）。

主な機能一覧
--------------
- Execution（発注）周辺
  - 起動スクリプト: run_execution.py
  - ブローカークライアントの抽象化（Paper Trading 時はモックを使用）
  - OrderManager / OrderRepository / Reconciler による注文管理・再同期ロジック
  - RiskManager による資金・ポジション制約チェック

- Monitoring（監視）
  - 起動スクリプト: run_monitoring.py
  - SystemMonitor: CPU/メモリ/ディスク、プロセス状態、データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格監視
  - RiskMonitor: ドローダウン・ポジション上限監視
  - MonitoringDB: SQLite ベースの監視ログ永続化（テーブル自動作成・マイグレーション）
  - AlertManager: LINE Push による通知（設定あれば送信）
  - KillSwitch: 条件により ExecutionEngine 停止フラグを書き込み

- Research / Portfolio
  - factor_research: モメンタム・バリュー・ボラティリティ等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）等の統計ツール
  - portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制限・レジーム乗数など

- AI
  - news_nlp: raw_news を LLM（OpenAI）でスコアリングし ai_scores に保存
  - regime_detector: ETF MA とマクロニュースを組み合わせ市場レジーム判定（LLM を使用可）

- ツール
  - paper_verification_report: Paper Trading DB の検証レポート生成スクリプト（期間指定可）
  - streamlit_dashboard: 監視 DB を可視化する Streamlit ダッシュボード

セットアップ（開発環境）
-------------------
前提
- Python 3.10 以上（型指定で | 合成表記を使用）
- SQLite は標準ライブラリ、DuckDB は外部依存

推奨パッケージ（例）
- duckdb
- psutil
- openai
- requests
- streamlit

インストール例
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージインストール（requirements.txt がある想定）
   - pip install -r requirements.txt
   あるいは個別インストール:
   - pip install duckdb psutil openai requests streamlit

環境変数 / .env
- プロジェクトは起動時に自動的にプロジェクトルート（.git または pyproject.toml を探索）にある .env / .env.local を読み込みます（OS 環境変数が優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 重要な環境変数（例）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須: Settings.jquants_refresh_token）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定モード、デフォルト: instant）
  - LOG_LEVEL: DEBUG/INFO/...
  - PID_FILE_PATH / KILL_FLAG_PATH: PID / kill-flag のファイルパス
- .env のパースはシェル風（export KEY=val、引用符、コメント等）にある程度対応します。

セットアップ補足
- monitoring 用の SQLite テーブルは init_monitoring_db()（run_monitoring.py / run_execution.py 内で呼ばれる）で自動作成・マイグレーションされます。特段手動操作は不要です。
- Paper Trading モード（KABUSYS_ENV=paper_trading）は本番 DB と分離して data/paper_trading.db を使用します（実行スクリプトが選択）。

使い方（実行例）
----------------

- 監視ループを起動
  - 環境変数でポーリング間隔を上書き可: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 実行:
    - python -m kabusys.run_monitoring
    - あるいは PYTHONPATH を通して直接実行可能な場合: python src/kabusys/run_monitoring.py
  - 起動時にプロセス優先度を "high" に設定し、監視用 SQLite / DuckDB に接続してループしました。

- ExecutionEngine（発注エンジン）を起動
  - Paper Trading と本番を切り替え:
    - 本番: export KABUSYS_ENV=live
    - Paper: export KABUSYS_ENV=paper_trading
  - 実行:
    - python -m kabusys.run_execution

- Streamlit ダッシュボード（監視）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only で開き、Overview / Positions / Orders / System タブを表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを直接指定できます（PAPER_TRADING_SQLITE_PATH 環境変数でも可）。

- AI / リサーチ機能（プログラム的利用）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...") など
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

注意事項 / 運用メモ
-----------------
- run_monitoring.py 内では MONITOR_POLL_INTERVAL が 0 以下または不正のときデフォルト（60秒）にフォールバックします。
- Settings モジュールはプロジェクトルートを探索して .env を自動ロードします。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process priority / CPU affinity の設定は psutil を利用し、実行環境により権限が必要な場合や未対応 OS の場合はスキップされます（警告ログ）。
- OpenAI 呼び出しはリトライとフォールバックを実装していますが、API キー未設定の場合は ValueError を送出します（AI 機能を使う場合は OPENAI_API_KEY を必ず設定してください）。
- Paper Trading 用 DB は本番とは分離されるため検証時の誤操作リスクが低い設計です。ただし paper_fill_mode 等の設定により挙動が変わります。

ディレクトリ構成（抜粋）
----------------------
以下は src/kabusys 以下のおおまかな構成（本 README で扱ったファイルを中心に抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env ローディングと Settings
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite テーブル作成・永続化 API
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
    - reconciler.py
    - execution_engine.py         — （存在は確認されるが本リストでは省略）
    - broker_factory.py
    - broker_api.py
    - ...
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
  - utils/
    - __init__.py
    - process_priority.py

付録: よく使うコマンド例
-----------------------
- 監視起動（デフォルト 60秒）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行（Paper Trading）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Paper 検証レポート（指定期間）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

以上が主要な使い方と構成の説明です。追加で README に追記したい事項（例: CI / テスト方法、デプロイ手順、詳細な API ドキュメント等）があれば教えてください。必要に応じて追補します。