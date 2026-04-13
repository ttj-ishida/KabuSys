KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株自動売買システム「KabuSys」の主要コンポーネントを切り出したコードベースです。
本 README はコードベース（src/kabusys 以下）を使い始めるための概要、機能、セットアップ、使い方、ディレクトリ構成をまとめたものです。

要点
- Python パッケージとして設計（src/kabusys/...）
- SQLite（監視ログ / Paper Trading 用 DB）と DuckDB（時系列・リサーチ用データ）を利用
- 実行エンジン（ExecutionEngine）と監視ループ（MonitoringEngine）を分離
- Paper Trading 向けモック、LLM（OpenAI）を使ったニュースセンチメント／レジーム判定、Streamlit ダッシュボード等のユーティリティあり

プロジェクト概要
----------------
KabuSys は以下の役割を持つコンポーネント群で構成されています（抜粋）：

- execution: 発注フロー（OrderManager、ExecutionEngine、Broker クライアントファクトリ、リコンシリエーション）
- monitoring: システム状態・注文状態・リスク監視（DB 永続化、アラート、Kill Switch、Streamlit ダッシュボード）
- portfolio: 銘柄候補選定・重み付け・単元丸め・リスク調整（純粋関数群）
- research: DuckDB を使ったファクター計算・特徴量探索（モメンタム・ボラティリティ・バリュー等）
- ai: OpenAI を使ったニュース NLP（センチメント）と市場レジーム判定
- tools: 検証レポート生成スクリプトなど運用支援ツール
- utils: プロセス優先度設定やユーティリティ

主要な実行エントリ
- 実行エンジン（本番 / Paper Trading）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 専用 SQLite（data/paper_trading.db）に記録します。
- 監視ループ（SystemMonitor のポーリング）:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

主な機能一覧
--------------
- Execution
  - 注文生成 → ブローカー送信 → 状態管理（OrderManager / OrderRepository）
  - 再起動時のリコンシリエーション（Reconciler）
  - Risk Manager（最大ポジション比・利用率・サーキットブレーカー等）
- Monitoring
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルによる監視ログ永続化
  - SystemMonitor（CPU / メモリ / ディスク / PID チェック / データ鮮度チェック）
  - TradeMonitor（滞留注文 / 約定価格異常検出）
  - RiskMonitor（ドローダウン／ポジション上限監視と kill.flag 発行）
  - AlertManager（LINE への一方向通知）
  - Streamlit ダッシュボードによる可視化
- Portfolio Construction
  - 候補選定（score/ rank ベース）、等金額／スコア加重、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算（単元丸め、aggregate cap）
- Research
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン、IC（情報係数）、統計要約
- AI（OpenAI）
  - ニュース集合のセンチメントスコア化（batch 呼び出し、リトライロジック、JSON バリデーション）
  - マクロニュース + ETF MA200 による日次市場レジーム判定（冪等書き込み）
- Tools
  - Paper Trading データの検証レポート生成（uptime / fill rate / latency / pass/fail 判定）

セットアップ手順
-----------------
1. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2. 必要な Python パッケージをインストール
   - 以下は本コードベースで使用される主な外部依存です。requirements.txt は同梱されていないため、適宜インストールしてください。
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

3. データディレクトリ作成（必要に応じて）
   - mkdir -p data

4. 環境変数 / .env の準備
   - Settings クラスに記載の環境変数を設定します（下記「重要な環境変数」参照）。
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

重要な環境変数（主なもの）
-------------------------
（Settings クラスより抜粋、必須は実行内容により異なります）

- 必須（実行時に参照される可能性あり）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行/データ
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動、デフォルト: instant）
  - PID_FILE_PATH: 実行エンジン PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアする場合は "1"
  - OPENAI_API_KEY: OpenAI API を使う場合は必須（ai.score_news, regime_detector など）

- 監視・閾値
  - CPU_THRESHOLD_PCT (例: "90.0")
  - MEMORY_THRESHOLD_PCT
  - DISK_THRESHOLD_PCT
  - LOG_LEVEL: DEBUG|INFO|...

- その他
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（AlertManager による LINE 通知を有効にする場合）

.env 自動ロードについて
- プロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動読み込みします。
  - 読み込み優先順位: OS環境 > .env.local > .env
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（よく使うコマンド）
------------------------

1. 実行エンジン（通常 / paper_trading）
   - 本番モード例:
     - export KABUSYS_ENV=live
     - python -m kabusys.run_execution
   - Paper Trading（モックブローカー）例:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
   - 注意: Paper Trading の DB は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離されます。

2. 監視ループ
   - python -m kabusys.run_monitoring
   - ポーリング間隔を変更:
     - export MONITOR_POLL_INTERVAL=120  # 秒
   - 監視は monitoring DB（settings.sqlite_path）へ書き込みます。init_monitoring_db が起動時にテーブルを作成します。

3. Streamlit ダッシュボード（ローカルで監視 DB を読み取り専用で確認）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB を明示する場合:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5. AI 関連（プログラムから呼ぶ）
   - kabusys.ai.score_news(conn, target_date, api_key=None)  # OPENAI_API_KEY を参照
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

運用上の注意
-------------
- init_monitoring_db は冪等で実行可能です。実行時に監視テーブルがなければ作成し、既存スキーマへのマイグレーション（カラム追加）も行います。
- run_execution / run_monitoring 起動時は set_process_priority("high") が実行され、プロセス優先度を試みます（権限により失敗することがあります）。
- KillSwitch は data/kill.flag に書き込むことで ExecutionEngine に停止シグナルを送ります。ExecutionEngine 側でこのフラグを監視している設計を想定しています。
- OpenAI API 呼び出しはリトライ・バックオフ・レスポンス検証が入っていますが、API キーの取り扱いには十分注意してください（レート制限・請求）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / .env 自動読み込み / Settings 定義
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

- ai/
  - news_nlp.py              — ニュースセンチメント（OpenAI）
  - regime_detector.py       — 市場レジーム判定（ETF MA + マクロセンチメント）
  - __init__.py

- monitoring/
  - monitoring_db.py         — monitoring DB スキーマ＆永続化 API（MonitoringDB）
  - system_monitor.py        — CPU/メモリ/ディスク/PID/データ鮮度監視
  - trade_monitor.py         — 注文滞留・約定異常検出
  - risk_monitor.py          — ドローダウン / ポジション上限監視
  - kill_switch.py           — kill.flag 管理
  - alert_manager.py         — LINE 送信
  - monitoring_engine.py     — 各 Monitor を束ねる Engine
  - streamlit_dashboard.py   — Streamlit ダッシュボード
  - __init__.py

- execution/
  - reconciler.py            — 起動時リコンシリエーション
  - order_manager.py         — 注文の外向き API
  - order_repository.py      — （未掲示だが）Order 永続化
  - ...                      — Broker / Engine / RiskManager 等（コードベースに依存）

- portfolio/
  - portfolio_builder.py     — 候補選定、重み計算
  - position_sizing.py       — 発注株数計算、aggregate cap
  - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - __init__.py

- research/
  - factor_research.py       — momentum / volatility / value ファクター
  - feature_exploration.py   — 将来リターン・IC・統計サマリー
  - __init__.py

- tools/
  - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - __init__.py

- utils/
  - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - __init__.py

その他（DB / データ）
- data/
  - kabusys.duckdb           — DuckDB（デフォルトパス）
  - monitoring.db            — 監視ログ SQLite（デフォルトパス）
  - paper_trading.db         — Paper Trading 用 SQLite（任意）

開発・拡張のポイント
--------------------
- DuckDB は大規模時系列解析に用いられ、research / ai モジュールは DuckDB 接続を引数に取り SQL と Python を組み合わせて処理します。テストの際はインメモリ接続やテスト用 DB を用意してください。
- AI モジュールは API 呼び出しを直接行いますが、テスト時には _call_openai_api のパッチやモックが用意されています（ユニットテストで差し替え可能）。
- ポートフォリオ構築関数群は純粋関数（副作用なし）で設計されており、ユニットテストが容易です。
- monitoring_db.py の MonitoringDB はビジネスロジックを持たず、DB の読み書きを提供します。migration 処理も含まれています。

ライセンス・貢献
----------------
この README 内にライセンス情報は含めていません。実際の運用にあたっては pyproject.toml やプロジェクトルートの LICENSE を確認してください。
貢献やバグ報告はリポジトリの issue / pull request にてお願いします。

最後に
------
この README はコードベース（src/kabusys 以下）を元に要点をまとめたドキュメントです。実運用前に必ず設定（特に API キー・ブローカー接続設定・DB パス）とローカルでの動作検証を行ってください。必要であればこの README を元に更に運用マニュアルやデプロイ手順を追加していくことを推奨します。