KabuSys — 日本株自動売買システム（抜粋）
====================================

このリポジトリは日本株の自動売買システム KabuSys の一部実装です。ここに含まれるモジュールは取引実行、モニタリング、ポートフォリオ構築、ファクター計算、LLM を用いたニュース評価などの主要機能を提供します。本 README は提供コードベースの概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
----------------
- 自動売買エンジン（ExecutionEngine）の起動/実行補助
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）によるシステム健全性チェックとアラート
- ポートフォリオ構築／ポジション算出ロジック（候補選定、重み付け、単元丸め、リスク調整）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- OpenAI（GPT）を使ったニュースのセンチメント評価、マクロセンチメントを使った市場レジーム判定
- Paper Trading 用検証レポート生成ツール、Streamlit ベースの監視ダッシュボード

主な特徴（機能一覧）
------------------
- Execution 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB に分離して記録
  - 起動時にプロセス優先度を上げる（set_process_priority）
  - リコンシリエーション（Reconciler）や RiskManager、OrderManager 組み立て済み

- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor のポーリングループ（デフォルト 60 秒、MONITOR_POLL_INTERVAL で上書き可）
  - 監視データは SQLite（monitoring.db）に永続化、DuckDB はリサーチ用途などで使用

- モニタリングサブシステム
  - SystemMonitor: CPU/メモリ/ディスクの取得、プロセス PID ファイルチェック、データ鮮度チェック
  - TradeMonitor: 滞留注文（stale orders）・約定異常（price anomaly）検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ記録
  - KillSwitch: kill.flag ファイルを生成して ExecutionEngine に停止シグナルを送る
  - AlertManager: LINE Push による一方向通知（トークン設定がある場合）

- ポートフォリオ関連（純粋関数）
  - 銘柄候補選定、等金額/スコア加重の重み計算
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（単元丸め、リスクベース配分、aggregate cap）

- リサーチ／ファクター計算
  - モメンタム／ボラティリティ／バリューのファクター計算（DuckDB 接続を受け取る）
  - 将来リターン計算、IC（Spearman）や統計サマリ関数

- AI モジュール
  - news_nlp.score_news: raw_news をまとめて OpenAI に送信し銘柄別スコアを ai_scores に書き込む
  - regime_detector.score_regime: ETF の MA 乖離とマクロニュースの LLM スコアを合成して market_regime を算出
  - API 呼び出しはリトライ・バックオフ・バリデーション実装済み

- ツール
  - paper_verification_report: Paper Trading DB を解析して稼働率・注文成功率・レイテンシ等のレポートを生成
  - streamlit_dashboard: monitoring DB を read-only で表示する簡易 UI（streamlit）

セットアップ手順
----------------

前提
- Python 3.10+ を想定（typing の | 記法や from __future__ annotations を使用）
- SQLite / DuckDB をデータ永続化に使用
- OpenAI を利用する機能を使う場合は OpenAI API key が必要

推奨インストール（最低限の依存）
- 必要なパッケージ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit

例（pip）
- 仮想環境を作成して有効化:
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- パッケージをインストール:
  - pip install duckdb psutil openai requests streamlit

環境変数/.env
- プロジェクトルート（.git または pyproject.toml のある場所）に .env / .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要な環境変数（主要）
- KABUSYS_ENV: 起動環境。値: development | paper_trading | live（デフォルト: development）
  - paper_trading: 発注は MockBroker、DB 分離（PAPER_TRADING_SQLITE_PATH を使用）
- SQLITE_PATH: 監視用 SQLite ファイル (デフォルト data/monitoring.db)
- DUCKDB_PATH: DuckDB ファイルパス (デフォルト data/kabusys.duckdb)
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite (デフォルト data/paper_trading.db)
- PAPER_FILL_MODE: paper_trading の MockBroker の fill モード:
  - instant / partial / never / reject（デフォルト "instant"）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 実運用で API を使う場合に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE通知）を有効にする場合

サンプル .env（最小）
- .env.example を参考にする想定ですが、手早く動かす例:
  KABUSYS_ENV=development
  SQLITE_PATH=data/monitoring.db
  DUCKDB_PATH=data/kabusys.duckdb
  OPENAI_API_KEY=sk-...
  LINE_CHANNEL_ACCESS_TOKEN=...
  LINE_USER_ID=...

使い方（主要なコマンド）
----------------------

1) 監視を起動（SystemMonitor の単純なポーリング）
- 環境変数 MONITOR_POLL_INTERVAL で秒間隔を変更（デフォルト 60）
- 実行:
  - python -m kabusys.run_monitoring
- 補足:
  - 監視は Settings から sqlite_path を取得します。monitoring は常に本番 sqlite_path を使う設計になっています（環境にかかわらず）。

2) Execution（実行エンジン）を起動
- Paper Trading モード（KABUSYS_ENV=paper_trading）の場合は MockBroker を使用して data/paper_trading.db に記録
- 実行:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - または KABUSYS_ENV=live python -m kabusys.run_execution

3) Paper Trading 検証レポート
- 例（期間指定と DB 指定）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
- 引数:
  - --from / --to: レポート期間（YYYY-MM-DD）
  - --db: SQLite DB パス（PAPER_TRADING_SQLITE_PATH が優先されるが --db で上書き可能）

4) Streamlit ダッシュボードを起動（監視 DB を読み取り専用で表示）
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

5) AI 関連（ニュース評価 / レジーム判定）
- OpenAI API キーが必要（OPENAI_API_KEY）
- モジュール関数をプログラムから呼ぶ（例）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="sk-...")
- 同等に regime_detector.score_regime を呼べます。

実運用上の注意
- run_execution と run_monitoring はそれぞれ PID ファイル（Settings.pid_file_path）を扱います。monitoring は Execution の PID を監視してプロセス死活を検出します。
- KillSwitch は data/kill.flag を書き込み、Execution 側でそれを検出して安全に停止させる設計になっています。
- .env の読み込み優先順は OS 環境 > .env.local > .env（必要により KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
- DuckDB / SQLite のファイルパスは Settings で制御されます。Paper Trading は本番 DB と分離するよう配慮されています。
- OpenAI 呼び出しにはリトライや応答バリデーションが実装されていますが、API 使用量やコストに注意してください。

ディレクトリ構成（抜粋）
----------------------
（src/kabusys 配下の主要ファイルと役割）
- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数の読み込み・Settings クラス（自動 .env ロード、必須項目チェック等）
- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト
- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（Paper Trading 時は MockBroker を使用）
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ初期化 / 永続化用ラッパー（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / PID チェック
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みロジック
  - alert_manager.py — LINE Push 送信（クールダウン管理）
  - monitoring_engine.py — 複数 Monitor をまとめるランナー
  - streamlit_dashboard.py — Streamlit ダッシュボード
- src/kabusys/execution/
  - order_manager.py, reconciler.py, ...（OrderState 管理、リコンシリエーション等）
- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（ポートフォリオ構築）
- src/kabusys/research/
  - factor_research.py（mom/vol/value ファクター）, feature_exploration.py（IC・統計）
- src/kabusys/ai/
  - news_nlp.py（ニュース NLP スコアリング）, regime_detector.py（市場レジーム判定）
- src/kabusys/utils/
  - process_priority.py（プロセス優先度 / CPU affinity 設定）
- その他: data/ 以下に DB ファイルを置くことを想定（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）

開発・拡張のヒント
- DuckDB 接続を渡す設計のため、リサーチ関数は副作用がなくテストしやすいことが意図されています。
- モジュール間の依存を抑え、AI 呼び出しは各モジュールで独立して実装されているため、ユニットテストやモックが容易です（内部の API 呼び出し関数はテストで差し替え可能）。
- monitoring_db.init_monitoring_db は冪等（テーブル作成とマイグレーションを行う）です。初回実行または DB 変更時に安全に呼べます。

ライセンス・貢献
----------------
- ここに示された README はコードスニペットに基づく説明です。実際のリポジトリに LICENSE ファイルや貢献ガイドがある場合はそちらを参照してください。

付録 — 便利なコマンド集
------------------------
- 監視開始:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン開始（paper_trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

必要があれば、README にサンプル .env.example、requirements.txt、systemd ユニット例、あるいは各モジュールの API 使用例（コードスニペット）を追加して詳細化できます。どの情報を優先して追加しますか？