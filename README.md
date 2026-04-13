README — KabuSys
=================

概要
----
KabuSys は日本株の自動売買プラットフォームのコアライブラリ群です。  
このリポジトリには以下の主要機能を提供するモジュール群が含まれます。

- 注文管理・発注（ExecutionEngine、OrderManager、Reconciler）
- リスク監視・監視エンジン（MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor）
- ポートフォリオ構築ロジック（候補選定、重み計算、ポジションサイジング、セクター制限）
- リサーチ向けファクター計算（モメンタム、ボラティリティ、バリューなど）
- ニュースNLP（OpenAI を用いたニュースセンチメント／レジーム判定）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）
- ユーティリティ（設定管理、プロセス優先度設定など）

主な設計方針：
- DuckDB/SQLite を用いたローカル DB ベースのデータ処理
- 本番・ペーパートレードの分離（KABUSYS_ENV）
- ルックアヘッドバイアスを避ける設計（日時の直接参照を制限）
- フェイルセーフ：外部 API 失敗時は安全側にフォールバック

機能一覧
--------
- 実行関連
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - ブローカークライアント分離（paper_trading では MockBroker を使用）
  - 起動時リコンシリエーション（Reconciler）で注文・ポジションの同期

- 監視関連
  - SystemMonitor: CPU/Memory/Disk、プロセス PID、データ鮮度の監視
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch: 条件発動で ExecutionEngine 停止フラグをファイルに書き込む
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
  - Monitoring DB 初期化ユーティリティ（init_monitoring_db）

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等金額 / スコア重み計算（calc_equal_weights / calc_score_weights）
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（calc_position_sizes）

- リサーチ
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン、IC 計算、統計サマリー

- AI（OpenAI）
  - ニュースをまとめて LLM に投げ、銘柄単位の ai_score を生成（news_nlp.score_news）
  - マクロニュース + ETF MA200 を用いて日次レジーム判定（regime_detector.score_regime）
  - API 呼び出しはリトライ／バックオフ・レスポンス検証を備える

セットアップ手順
----------------

前提
- Python 3.10+（コードは型注釈に Python 3.10+ の機能を使用）
- SQLite（標準で同梱）、DuckDB、外部パッケージ

推奨パッケージ（pip インストール例）
- duckdb
- psutil
- requests
- openai
- streamlit

例:
1. 仮想環境作成 / 有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係インストール（例）
   - pip install duckdb psutil requests openai streamlit

3. プロジェクトルートに .env を作成（下記「環境変数」を参照）

重要な環境変数
----------------
KabuSys は .env ファイルまたは環境変数から設定を読み取ります。プロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動検出して .env を読み込みます。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要なキー（例 / デフォルト）:
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - paper_trading の場合、Execution は MockBrokerClient を使い DB は data/paper_trading.db を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必要）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード専用 DB）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- LOG_LEVEL: "INFO" 等
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）用

注意:
- Settings クラスは未設定の必須キーに対して ValueError を投げます（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
- .env のパースは bash 風の export/コメント/クォートを扱います（config._load_env_file を参照）。

DB 初期化
--------
監視用 SQLite DB（デフォルト: data/monitoring.db）は起動スクリプトが自動で init_monitoring_db を実行します（必要テーブルがなければ作成）。手動で初期化したい場合は Python REPL 等で以下を呼ぶことも可能です。

例（簡易）:
- python -c "from kabusys.config import Settings; import sqlite3; from kabusys.monitoring.monitoring_db import init_monitoring_db; s=Settings(); conn=sqlite3.connect(str(s.sqlite_path)); init_monitoring_db(conn); conn.close()"

使い方
------

1) ExecutionEngine を起動（本番 / ペーパー切替）
- 本番（KABUSYS_ENV=live）
  - KABUSYS_ENV=live python -m kabusys.run_execution
- ペーパートレード（KABUSYS_ENV=paper_trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - この場合、settings.paper_sqlite_path を使い data/paper_trading.db に記録され、本番 DB と分離されます。

起動時の挙動:
- set_process_priority("high") を呼び出してプロセス優先度を上げます（OS の権限に依存して失敗する場合はログ警告のみ）。
- DB（SQLite + DuckDB）に接続して ExecutionEngine.run_session() を実行します。
- PID ファイル（settings.pid_file_path）に PID を書き、kill.flag をチェックします。

2) 監視ループの起動
- python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト: 60）
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

監視で行うこと:
- SystemMonitor, TradeMonitor, RiskMonitor を定期実行し、MonitoringDB にログを残す
- KillSwitch 条件（ドローダウン等）で data/kill.flag を書き込んで Execution 停止を指示
- LINE 通知は AlertManager 経由（トークン未設定時はログのみ）

3) Streamlit ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only URI を使って SQLite を開き、ダッシュボードを表示します。

4) Paper Trading 検証レポート
- 期間指定して検証レポートを標準出力へ出力:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB: data/paper_trading.db。--db で別パス指定可。

5) AI 関連（ニューススコア・レジーム判定）
- OpenAI API キーが必要（OPENAI_API_KEY）
- news_nlp.score_news(conn, target_date, api_key=None) を呼び出して ai_scores テーブルを書き換え
- regime_detector.score_regime(conn, target_date, api_key=None) を呼び出して market_regime に書き込み
- 実行はスクリプトや定期ジョブ（cron）で日次運用する想定

その他の注意点
- KABUSYS_ENV=paper_trading のときは発注関連が本番 API を叩かないように設計されています（DB も分離）。
- run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使って監視ログを残します（モニタは本番 DB を監視する仕様）。
- DB マイグレーション（列追加等）は init_monitoring_db 内で冪等に実行されます（例: trade_logs.latency_ms, dashboard.peak_value）。

ディレクトリ構成
-----------------
（抜粋: src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定管理（.env 読込）
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py          — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite 監視 DB 層（テーブル作成・読み書き）
    - monitoring_engine.py         — 各モニタを束ねるランナー
    - system_monitor.py            — CPU/Mem/Disk・PID・データ鮮度チェック
    - trade_monitor.py             — 注文滞留、約定価格異常チェック
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag の作成/管理
    - alert_manager.py             — LINE 通知（Push）
    - streamlit_dashboard.py       — Streamlit ダッシュボード
  - execution/
    - (order_manager.py, reconciler.py, order_repository.py, broker_factory 等)
    - reconciler.py                — 起動時の注文/ポジション同期ロジック
    - order_manager.py             — 発注ワークフロー（DB, broker 呼び出し）
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数計算・上限・単元丸め
    - risk_adjustment.py           — セクター制限・レジーム乗数
  - research/
    - factor_research.py           — モメンタム/ボラ/バリュー等ファクター計算（DuckDB）
    - feature_exploration.py       — 将来リターン・IC/統計処理
  - ai/
    - news_nlp.py                  — ニュースの LLM スコアリング + ai_scores 書込
    - regime_detector.py           — ETF MA200 + マクロニュースでレジーム判定
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - data/ (想定 — 実運用ではプロジェクトルートの data/ 下に DB 等を置く)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db

ライセンス・セキュリティ
-----------------------
- OpenAI API キーやブローカー認証情報などの機密情報は .env または環境変数で管理してください。
- .env ファイルはリポジトリにコミットしないでください（.gitignore に追加すること）。

開発者向けメモ
----------------
- 単体関数群（portfolio/*, research/*）は副作用を持たない純粋関数で設計されており、ユニットテストが書きやすくなっています。
- 外部 API 呼び出し部分（OpenAI, broker）は抽象化されており、テスト時にモックで差し替え可能です（例: _call_openai_api のパッチ等）。
- Settings は起動時に重要設定の妥当性チェックを行います。実行前に必須変数が設定されていることを確認してください。

お問い合わせ
----------
リポジトリ内のモジュールコメント（docstring）に詳細な設計意図・挙動が記載されています。機能や実装に関する質問は該当モジュールの docstring を先にご参照ください。