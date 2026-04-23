KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・モニタリングを目的とした小規模なシステム群です。本リポジトリは以下の主要機能を含みます。

- 実行エンジン (ExecutionEngine) — 発注・約定管理・リスク管理
- 監視 (Monitoring) — システム稼働状況・取引状態・リスク監視、Kill Switch 発動
- ポートフォリオ構築モジュール — 候補選定、重み付け、株数計算、セクター制限
- リサーチ機能 — ファクター計算、特徴量探索、IC 計算
- AI モジュール — ニュースの NLP スコアリング、レジーム判定（OpenAI API 使用）
- ユーティリティ — 設定ウィザード、設定検証、ログ設定、プロセス優先度設定
- ツール — ペーパートレード検証レポート生成スクリプト 等

主な設計方針として、DB（DuckDB / SQLite）をデータ格納に利用し、リサーチやポートフォリオ計算は副作用のない純粋関数で実装されています。AI 機能は OpenAI API を利用しますが、API キーが未設定の場合はフェイルセーフでスキップする設計になっています。

主な機能一覧
--------------
- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading のときは MockBroker を使い paper_trading.db に記録（本番 DB と分離）。
- run_monitoring.py
  - SystemMonitor をポーリングして system_status 等を記録。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。
- config_setup.py
  - .env を対話式に生成・更新するウィザード。
- validate_config.py
  - .env や config/*.yaml の基本チェックを行う CLI（--strict モードあり）。
- tools/paper_verification_report.py
  - ペーパートレード用 SQLite を読みレポートを生成（稼働率・成功率・レイテンシ等）。
- portfolio/*
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数などの純粋関数群。
- research/*
  - DuckDB の prices_daily / raw_financials を使ったファクター計算、将来リターン、IC、統計サマリ等。
- ai/*
  - news_nlp: raw_news を集約して OpenAI に投げ、ai_scores に書き込む処理。
  - regime_detector: ETF + マクロニュースを元に市場レジームを判定して書き込む処理。
- monitoring/*
  - DB スキーマ定義 / 永続化層 (monitoring_db)
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine 等

セットアップ手順
----------------

1. 前提
   - Python 3.10 以上（PEP 604 の型構文などを使用）
   - SQLite は標準ライブラリで利用
   - 外部依存パッケージ（例）:
     - duckdb
     - psutil
     - openai
   - 実際の環境では requirements.txt / poetry 等で管理してください。
     例（簡易）:
       python -m venv .venv
       source .venv/bin/activate
       pip install duckdb psutil openai

2. リポジトリルートで初期ディレクトリ作成（logs / data）
   - データやログの格納ディレクトリを作る:
       mkdir -p data logs

3. .env を作成
   - 対話式ウィザードを使う（推奨）:
       python -m kabusys.config_setup
   - または .env を直接作成して環境変数を設定:
     - 必須:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
     - 推奨 / 任意:
       - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
       - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
       - SQLITE_PATH（デフォルト data/monitoring.db）
       - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
       - OPENAI_API_KEY（AI 機能を使う場合）
       - LOG_LEVEL（DEBUG/INFO/...）
     - .env の自動ロードはデフォルトで有効（config.Settings モジュールが根拠）。

4. 設定検証（任意だが推奨）
       python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります。

使い方（よく使うコマンド）
-------------------------

- 実行エンジン起動
  - 本番・ペーパー切替は KABUSYS_ENV で指定:
      KABUSYS_ENV=paper_trading python -m kabusys.run_execution
      KABUSYS_ENV=live python -m kabusys.run_execution
  - paper_trading では専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
  - 実行中に data/stop_requested.flag が作成されるとエンジンは安全に停止します。
  - 実行はバックグラウンドスレッドで行われ、PID は data/execution.pid に保存されます。

- 監視プロセス起動
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を指定できます（デフォルト 60 秒）。
  - 監視プロセスは実行プロセスの健全性（CPU/メモリ/ディスク/プロセス存在）やデータ鮮度を監視し、SQLite（monitoring.db）へ記録します。
  - 監視ループは data/stop_requested.flag を検知すると終了します。

- .env 編集ウィザード
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを直接指定可能（環境変数 PAPER_TRADING_SQLITE_PATH を上書き）。

- AI 関連（ライブラリ的に利用）
  - ニュース NLP スコアリングをプログラムから呼ぶ例（DuckDB 接続を渡す）:
      from kabusys.ai import score_news
      import duckdb
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
  - レジーム判定:
      from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date=date(2026,4,1), api_key="sk-...")

運用上の注意
-------------
- Kill Switch
  - RiskMonitor がトリガー条件を満たすと data/kill.flag が書き込まれます。ExecutionEngine は起動時にこのフラグを検出すると起動を停止し、実行中は監視プロセスから停止シグナルで停止します。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動で kill.flag をクリアしますが、本番環境では 0 を推奨します。

- ログ
  - デフォルトでは logs/<app_name>.log に日次ローテートで出力されます。ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理されています。
  - コンソール出力は stdout に出ます（cron / systemd などでのリダイレクトを想定）。

- DB
  - DuckDB は分析データ用（デフォルト data/kabusys.duckdb）。
  - SQLite は監視・トレードログ用（デフォルト data/monitoring.db）。
  - Paper Trading は分離される（data/paper_trading.db）。KABUSYS_ENV=paper_trading で切替。

ディレクトリ構成（主なファイル）
--------------------------------
以下は src/kabusys 以下の主要ファイルと説明（抜粋）です。

- kabusys/__init__.py
- kabusys/config.py
  - 環境変数管理と自動 .env 読み込みロジック
- kabusys/config_setup.py
  - .env 対話式ウィザード
- kabusys/validate_config.py
  - 設定検証 CLI
- kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト
- kabusys/run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト
- kabusys/utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity
- kabusys/monitoring/
  - monitoring_db.py — SQLite テーブル定義と永続化ラッパー
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py
- kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- kabusys/research/
  - factor_research.py, feature_exploration.py
- kabusys/ai/
  - news_nlp.py, regime_detector.py
- kabusys/tools/
  - paper_verification_report.py

例: 最低限の運用フロー
---------------------
1. 仮想環境を用意して依存をインストール
2. data/ と logs/ を作成
3. python -m kabusys.config_setup で .env を作成（JQUANTS_REFRESH_TOKEN・KABU_API_PASSWORD は必須）
4. python -m kabusys.validate_config で設定確認
5. KABUSYS_ENV を設定して ExecutionEngine を起動:
     KABUSYS_ENV=paper_trading python -m kabusys.run_execution
6. 監視プロセスを別プロセスで起動:
     python -m kabusys.run_monitoring

補足
----
- この README はソースコードの内容に基づく概要ドキュメントです。実行に必要なパッケージ一覧（requirements.txt）や systemd / supervisor 用のユニットファイル、より詳細な運用手順（バックアップ、DB マイグレーション、監視ポリシー）等は別途整備してください。
- AI 機能 (OpenAI) を利用する場合は API コスト・レートリミットに注意して実行してください。API キーは .env に格納するか、関数呼び出し時に明示的に渡してください。

以上。必要であれば、インストール用の requirements.txt の候補や systemd サービスファイルのテンプレート、よくある運用手順（デプロイ手順・ログローテーション設定・バックアップ）も作成します。どれが必要か教えてください。