README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量なフレームワークです。本コードベースは主に以下の機能群を提供します。

- 注文発行・管理と ExecutionEngine（発注周りのライフサイクル、再起動時のリコンシリエーション）
- リスク管理（ドローダウン監視、ポジション上限など）
- 監視（システム状態、注文滞留、約定異常、ダッシュボード）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、セクター制限）
- リサーチ（ファクター計算、将来リターン、IC 計算）
- AI 支援（ニュースの NLP によるセンチメントスコアリング、市場レジーム判定）
- 運用支援ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

主な設計方針
- 実運用と paper_trading（検証）を明確に分離（paper_trading は専用 SQLite を使用）
- DuckDB を用いた時系列/ファクタ計算（prices_daily / raw_financials など）
- 外部 API 呼び出し（OpenAI など）はリトライ・フェイルセーフ実装
- ルックアヘッドバイアス回避（内部で date.today()/datetime.now() を盲目的に参照しない設計）

機能一覧
--------
- 実行系
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録。
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）。
  - monitoring_engine, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager（LINE 通知）
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード（read-only）。
- リサーチ / ポートフォリオ
  - research.factor_research: momentum / volatility / value 等のファクター計算（DuckDB 使用）
  - portfolio.*: 候補選定、重み付け、ポジションサイズ計算、レジーム乗数、セクター上限適用
- AI 関連
  - ai.news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとの ai_scores を生成・書き込み
  - ai.regime_detector: マクロニュース + ETF MA 乖離から market_regime を算出して保存
- ツール
  - tools.paper_verification_report: Paper Trading DB から検証レポートを出力

セットアップ
----------
前提
- Python 3.10+（typing | 標準の現代的機能を利用）
- システム依存ライブラリ: duckdb, psutil, requests, streamlit, openai（必要に応じて）

推奨手順（開発環境）
1. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate（Windows）

2. 依存パッケージをインストール
   - pip install duckdb psutil requests streamlit openai

   （プロジェクトで requirements.txt がある場合は pip install -r requirements.txt を使用）

3. ソースを PYTHONPATH に追加（ローカル実行）
   - export PYTHONPATH=$(pwd)/src
   - Windows PowerShell: $env:PYTHONPATH = (Resolve-Path .\src).Path

4. 環境変数（.env）を用意
   - プロジェクトルートに .env / .env.local を配置すると自動読み込みされます（OS 環境変数が優先）。
   - 例 (.env.example として):
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - MONITOR_POLL_INTERVAL=60
     - PAPER_FILL_MODE=instant|partial|never|reject

   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

初期 DB 作成
- Monitoring 用 SQLite（init_monitoring_db が自動でテーブルを作成・マイグレーションを実施）
- DuckDB ファイル（prices_daily 等のテーブルはユーザ側で作成・ロードしてください）

使い方
------

実行エンジン（発注）
- 実行（本番 or 開発）
  - PYTHONPATH を設定した上で:
    - python -m kabusys.run_execution
  - 環境変数で環境を切り替え:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - paper_trading の場合、デフォルトで PAPER_TRADING_SQLITE_PATH=data/paper_trading.db を使用し、本番 DB と分離されます。

監視
- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - export MONITOR_POLL_INTERVAL=30
- Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視ログを記録します（paper_trading でも監視は本番 DB を参照する設計）。

Streamlit ダッシュボード (read-only)
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- このダッシュボードは監視用 SQLite を read-only モードで参照します（DB が存在しない場合は起動に失敗します）。

Paper Trading 検証レポート
- コマンドライン:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
- 出力: 稼働率、注文成功率、送信率、レイテンシ等のサマリと PASS/FAIL 判定

AI / レジーム判定・ニューススコアリング
- OpenAI API キーが必要（環境変数 OPENAI_API_KEY または引数で渡す）
- プログラム上の呼び出し例（Python API）:
  - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
- 動作: raw_news / news_symbols テーブルを参照し、ai_scores / market_regime テーブルへ結果を保存します。
- フェイルセーフ: API エラー時はリトライやゼロフォールバックを行い、致命的例外で停止しない設計です。

設定（Settings）
- 設定は環境変数から読み込まれます（.env/.env.local の自動ロードあり）
- 主要な環境変数:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の fill 動作）
  - PID_FILE_PATH / KILL_FLAG_PATH: 起動監視用ファイルパス
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
  - OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

運用上の注意
- run_monitoring は監視用 DB に監視ログを永続化します。起動直後に kill.flag を自動で消したい場合は Settings.kill_flag_clear_on_start = 1 を設定してください。
- run_execution は起動時に pid ファイルを書き、run_monitoring の SystemMonitor が PID 存在チェックを行います。stale PID を検出すると kill.flag 書き込みやログを生成します。
- paper_trading を使用する際は必ず専用 DB（PAPER_TRADING_SQLITE_PATH）を用いることで本番データと分離してください。

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py
- config.py                          — 環境変数 / 設定管理
- run_monitoring.py                  — SystemMonitor ポーリングランナー
- run_execution.py                   — ExecutionEngine 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py                    — SQLite 読み書き層（スキーマ・マイグレーション含む）
- system_monitor.py                   — CPU/メモリ/ディスク/データ鮮度/プロセス監視
- trade_monitor.py                    — 注文滞留 / 約定異常監視
- risk_monitor.py                     — ドローダウン・ポジション上限監視
- kill_switch.py                      — kill.flag 書き込みロジック
- alert_manager.py                    — LINE 通知
- monitoring_engine.py                — 各モニタを束ねるエンジン
- streamlit_dashboard.py              — Streamlit ダッシュボード

src/kabusys/execution/
- order_manager.py                    — 注文状態遷移 API
- reconciler.py                       — 起動時のリコンシリエーション（注文・ポジション整合）
- その他（broker_factory / order_repository 等が存在）

src/kabusys/portfolio/
- portfolio_builder.py                — 候補選定・重み計算
- position_sizing.py                  — 株数・割当計算（単元丸め・aggregate cap）
- risk_adjustment.py                  — セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py                  — momentum/volatility/value ファクター計算（DuckDB）
- feature_exploration.py              — 将来リターン / IC / 統計サマリ

src/kabusys/ai/
- news_nlp.py                         — ニュース集約 + OpenAI 呼び出し + ai_scores への書込み
- regime_detector.py                  — ETF MA + マクロニュースで市場レジーム判定

src/kabusys/tools/
- paper_verification_report.py        — Paper Trading 検証レポート生成

src/kabusys/utils/
- process_priority.py                 — プロセス優先度 / CPU affinity 設定ユーティリティ

既知の依存
- duckdb
- psutil
- requests
- streamlit (ダッシュボード用)
- openai (AI モジュール用)
- sqlite3（標準ライブラリ）

開発上のヒント
- ローカルでモジュールを実行する際は PYTHONPATH に src を追加するか、パッケージインストール（pip install -e .）してください。
- DuckDB 上のテーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime 等）は外部 ETL で準備する必要があります（このリポジトリは ETL スクリプトを含みません）。
- ログは標準 logging を使用。デバッグ時は LOG_LEVEL 環境変数を DEBUG に設定してください。

ライセンス / 貢献
----------------
（ここにライセンス情報や貢献方法を追記してください）

お問い合わせ
----------
バグ報告・要望等はリポジトリの Issue を利用してください。