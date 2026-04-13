KabuSys — 日本株自動売買システム
=================================

本リポジトリは日本株の自動売買／研究／監視に必要なコンポーネント群を提供します。
コードはモジュール化されており、監視（Monitoring）、発注実行（Execution）、
ポートフォリオ構築（Portfolio）、ファクター計算・研究（Research）、AI（ニュースNLP）などの
機能が含まれます。

主な特徴
--------
- 実行エンジン（ExecutionEngine）と監視エンジン（MonitoringEngine）を分離
- SQLite（監視ログ）＋ DuckDB（時系列・ファクタ計算）を利用したデータ基盤
- Paper Trading モード（完全に本番 DB と分離された専用 SQLite）をサポート
- NEWS → LLM（OpenAI） を用いたニュースセンチメント評価（ai.news_nlp）
- 市場レジーム判定（ai.regime_detector）によりレジーム乗数を適用可能
- Streamlit ベースの監視ダッシュボード（read-only 接続）
- リスク監視（ドローダウン・保有数上限）、アラート（LINE Push）や kill.flag による
  Execution 停止シグナル機能
- ポートフォリオ構築・配分・ポジションサイジング等の純粋関数群（テスト容易）

セットアップ
-----------

前提
- Python 3.10 以上（typing の | などを利用しているため）
- SQLite（Python 標準に含まれます）
- DuckDB（Python パッケージ）
- ネットワーク接続（OpenAI API を使う場合）

推奨パッケージ（最低限）
- duckdb
- psutil
- requests
- openai
- streamlit

仮想環境作成例
- Unix/macOS:
  python -m venv .venv
  source .venv/bin/activate
- Windows (PowerShell):
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1

パッケージインストール例
- pip install duckdb psutil requests openai streamlit

（プロジェクト配布に requirements.txt があればそちらを利用してください）

環境変数（.env）
- プロジェクトルートの .env / .env.local を自動読み込み（OS 環境変数を優先）。
- 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

よく使う環境変数（.env 例）
- KABUSYS_ENV=development|paper_trading|live
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PAPER_FILL_MODE=instant|partial|never|reject
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- LOG_LEVEL=INFO
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...

初期データディレクトリ作成
- mkdir -p data

使い方（主要コマンド）
--------------------

1) 監視ループ（Monitoring）起動
- python -m kabusys.run_monitoring
  - 監視ループはデフォルト 60 秒間隔で実行されます。
  - ポーリング間隔は環境変数で上書き可能: MONITOR_POLL_INTERVAL（秒、1 以上）
  - 監視 DB（SQLite）は Settings.sqlite_path を使用（KABUSYS_ENV に関わらず本番 monitoring DB を使用する設計）
  - 起動時にプロセス優先度を high に設定（set_process_priority）

2) Execution（発注エンジン）起動
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、
    PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録して本番 DB と分離されます。
  - 起動時にプロセス優先度を high に設定
  - ブローカークライアントは設定に応じて Factory で生成されます

3) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを指定可能（デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）
  - レポートには稼働率、注文成功率、送信率、レイテンシなどが出力されます

4) Streamlit 監視ダッシュボード起動
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only で SQLite に接続し、Overview / Positions / Orders / System 情報を表示します

5) AI（ニューススコア・レジーム判定）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キーは引数または OPENAI_API_KEY 環境変数で指定
  - raw_news / news_symbols / ai_scores を参照・更新
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF (1321) の MA200 とマクロニュースセンチメントを合成して
    market_regime テーブルへ冪等書き込みします

注意事項 / 運用メモ
- Settings クラスは .env / OS 環境変数を読み込み、必須値がないと ValueError を投げます（JQUANTS_REFRESH_TOKEN 等）
- run_monitoring は監視専用 DB を初期化する（init_monitoring_db）
- run_execution は paper_trading モードであれば paper 用 SQLite を使う（本番とは分離）
- kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）を監視して ExecutionEngine に停止シグナルを送る仕組みがあります。KillSwitch は冪等にファイルを書き込みます。起動時に既存の kill.flag をクリアする挙動は設定で制御できます（Settings.kill_flag_clear_on_start）
- LINE 通知は AlertManager 経由。channel token / user id が未設定なら送信はスキップされログのみ出力されます
- OpenAI API 呼び出しはリトライ／バックオフを備えていますが、API キーや利用上限に注意してください
- DuckDB 側のテーブル（prices_daily, raw_financials, raw_news 等）が揃っていることが前提です（研究・ファクタ計算モジュール）

ディレクトリ構成（抜粋）
----------------------

src/kabusys/
- __init__.py
- config.py                          — 環境変数 / Settings 管理（.env 自動ロード）
- run_monitoring.py                  — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                   — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py                       — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py                — MA200 + マクロニュースで市場レジーム判定
- monitoring/
  - monitoring_db.py                  — SQLite テーブル初期化・CRUD 層（MonitoringDB）
  - system_monitor.py                 — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py                  — 注文滞留・約定異常監視
  - risk_monitor.py                   — ドローダウン・ポジション上限監視
  - kill_switch.py                     — kill.flag 書き込み・評価
  - alert_manager.py                  — LINE 通知（cooldown 管理）
  - monitoring_engine.py              — 各モニタを束ねる実行ループ
  - streamlit_dashboard.py            — Streamlit 監視ダッシュボード
- execution/
  - order_manager.py                  — 発注管理（OrderState 機械）
  - reconciler.py                     — 起動時リコンシリエーション
  - （その他 broker_factory 等。実行エンジン関連）
- portfolio/
  - portfolio_builder.py              — 銘柄選定（スコア・等配分）
  - position_sizing.py                — 株数決定・集計・lot 単位切捨て・スケールダウン
  - risk_adjustment.py                — セクターキャップ・レジーム乗数
- research/
  - factor_research.py                — Momentum / Volatility / Value 等ファクター計算（DuckDB）
  - feature_exploration.py            — 将来リターン / IC / 統計サマリー
- tools/
  - paper_verification_report.py      — Paper Trading 検証レポート（CLI）
- utils/
  - process_priority.py               — プロセス優先度・CPU affinity 設定ユーティリティ

開発者向けメモ
---------------
- 型アノテーションと純粋関数設計によりユニットテストが書きやすい構造になっています
- DuckDB を使う関数は接続を受け取る設計（副作用の最小化）
- LLM 呼び出しのロジックはリトライ・バリデーションを厳密に行い、部分失敗でも安全に継続する方針です
- watchdog / systemd などで run_monitoring/run_execution を常駐化すると運用しやすくなります
- DB スキーマ変更時は monitoring_db.init_monitoring_db のマイグレーション部分を更新してください

ライセンス・貢献
----------------
（ここにライセンス情報や貢献ルールを追記してください）

お問い合わせ
------------
不明点やバグ報告・提案は Issue を作成してください。

以上。必要であれば README に含める環境変数のサンプル .env や起動例の具体的な systemd ユニット / docker-compose 設定例も作成できます。どの形式がよいか教えてください。