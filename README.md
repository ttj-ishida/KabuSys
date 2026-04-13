KabuSys — 日本株自動売買システム
=================================

※このドキュメントはリポジトリ内のソースコードに基づいて作成されています。

概要
----
KabuSys は日本株を対象とした自動売買システムのコアライブラリです。  
主な責務は以下の通りです。

- 発注エンジン（ExecutionEngine）による注文生成・送信・状態管理
- 監視コンポーネント（MonitoringEngine）によるシステム健全性チェック、アラート送信、Kill Switch
- ポートフォリオ構築（候補選定・重み付け・株数決定・リスク調整）
- 研究用モジュール（ファクター計算・特徴量解析）
- AI モジュール（ニュースセンチメント評価、レジーム判定） — OpenAI API を利用
- 開発/検証向けツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な機能
--------
- Execution
  - Broker クライアント抽象化（本番/モック切替 / paper_trading 分離）
  - OrderManager / OrderRepository による状態管理と永続化
  - 起動時のリコンシリエーション（Reconciler）で crash/restart 後の自動復旧
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス存在確認・データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とログ記録
  - KillSwitch: フラグファイルにより ExecutionEngine 停止指示
  - AlertManager: LINE Messaging API を用いた通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード（読み取り専用）
- Portfolio Construction
  - 候補選定（スコア順、タイブレーク）、等重・スコア重み、ポジションサイズ計算（単元丸め・リスクベース）
  - セクター上限適用、レジーム乗数
- Research
  - DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（スピアマン）や統計サマリ
- AI
  - ニュースを LLM（gpt-4o-mini 等）でスコア化し ai_scores に書き込み（score_news）
  - マクロニュース + ETF MA を用いた市場レジーム判定（score_regime）
- Tools
  - paper_verification_report: Paper Trading DB から運用検証レポートを生成
  - streamlit_dashboard: 可視化ダッシュボード起動スクリプト

セットアップ
------------

前提
- Python 3.10+
- SQLite（標準で Python に同梱）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボードを使う場合)
  - openai (AI 機能を使う場合)

例（venv を使用したセットアップ）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

2. 必要パッケージをインストール
   - pip install duckdb psutil requests streamlit openai

（プロジェクト内に requirements.txt があれば pip install -r requirements.txt を利用してください）

環境変数
- 自動ロード
  - パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、.env と .env.local を自動で読み込みます。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- 主な環境変数（Settings クラス参照）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能を使う場合)
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (アラート送信)
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、MockBrokerClient が使用され、Paper 専用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録されます
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の模擬約定挙動）
  - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - DUCKDB_PATH（時系列データ DB、デフォルト: data/kabusys.duckdb）
  - PID_FILE_PATH（ExecutionEngine 用 PID ファイル、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（kill.flag のパス、デフォルト: data/kill.flag）
  - その他: PID フラグの初期クリア設定やしきい値（CPU_THRESHOLD_PCT 等）、LOG_LEVEL

初期 DB 作成
- run_execution.py / run_monitoring.py は起動時に init_monitoring_db を呼び出し、必要テーブルを冪等に作成します。特別な初期化は不要です（ただし DuckDB の prices_daily/raw_financials 等のデータは別途用意してください）。

使い方
------

実行スクリプト
- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
  - 起動時に PID ファイルを書き、ExecutionEngine が稼働します。paper_trading 環境では MockBrokerClient を使用し、data/paper_trading.db に記録されます。

- Monitoring のポーリングループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は常に production 用 sqlite_path（Settings.sqlite_path）を参照します（KABUSYS_ENV にかかわらず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- Streamlit ダッシュボード（監視用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で DB にアクセスし、Overview / Positions / Orders / System タブを提供します

AI 機能の利用
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続と日付を渡すと ai_scores テーブルへ書き込みます（内部で OpenAI API を呼び出します）
- regime_detector.score_regime(conn, target_date, api_key=None)
  - マクロ記事 + ETF MA200 を用いて market_regime テーブルへ結果を書き込みます
- 両機能とも OPENAI_API_KEY（または引数 api_key）が必要です。API 呼び出しはリトライやフェイルセーフ（失敗時はデフォルト値で継続）を備えています。

注意点 / 運用メモ
- paper_trading 環境は本番 DB と分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- Process priority 設定（set_process_priority）は psutil を利用します。権限によっては設定が失敗することがあります（警告が出てスキップされます）。
- kill.flag による停止シグナルは Monitoring が判定して書き込みます。ExecutionEngine は起動時に kill.flag をクリアする挙動を設定できます（Settings.kill_flag_clear_on_start）。
- duckdb/psutil/requests/openai などの挙動やバージョンに依存します。運用時は想定バージョンでの動作確認を行ってください。
- Python の型ヒントに 3.10 の新構文（|）が使われているため Python 3.10+ を推奨します。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py                      — パッケージ定義、バージョン
- config.py                        — 環境変数 / 設定読み込みロジック（.env 自動ロード）
- run_execution.py                 — ExecutionEngine 起動スクリプト
- run_monitoring.py                — SystemMonitor ポーリングループ起動スクリプト

src/kabusys/execution/
- order_manager.py                 — 発注フロー API、Order 状態遷移管理
- reconciler.py                    — 起動時リコンシリエーション（注文 / ポジション照合）
- (その他 execution 関連モジュール: broker_factory, execution_engine, order_repository, ...)

src/kabusys/monitoring/
- monitoring_db.py                 — SQLite 監視テーブル定義 + DB 操作ラッパ
- system_monitor.py                — CPU/メモリ/ディスク・プロセス・データ鮮度監視
- trade_monitor.py                 — 注文滞留 / 約定異常監視
- risk_monitor.py                  — ドローダウン / ポジション上限監視
- kill_switch.py                   — kill.flag 書き込みロジック
- alert_manager.py                 — LINE 通知ラッパ
- monitoring_engine.py             — 各 Monitor を束ねる実行エンジン
- streamlit_dashboard.py           — Streamlit ダッシュボード

src/kabusys/portfolio/
- portfolio_builder.py             — 候補選定 / 重み付け
- position_sizing.py               — 株数計算 / aggregate cap / 単元丸め
- risk_adjustment.py               — セクターキャップ / レジーム乗数

src/kabusys/research/
- factor_research.py               — ファクター計算（momentum / volatility / value）
- feature_exploration.py           — 将来リターン / IC / 統計サマリ

src/kabusys/ai/
- news_nlp.py                      — ニュースを LLM でスコア化して ai_scores に書き込み
- regime_detector.py               — マクロ + MA を使った市場レジーム判定

src/kabusys/tools/
- paper_verification_report.py     — Paper Trading 検証レポート生成スクリプト

src/kabusys/utils/
- process_priority.py              — プロセス優先度 / CPU affinity ユーティリティ

DB スキーマ（監視 DB の主なテーブル）
- system_status
- trade_logs (latency_ms カラムあり)
- positions
- risk_logs
- dashboard

サンプルコマンド一覧
-------------------
- Execution 起動:
  - KABUSYS_ENV=development python -m kabusys.run_execution

- Monitoring 起動（デフォルト 60 秒間隔）:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

貢献 / 拡張ポイント
-------------------
- BrokerClient の増設（実ブローカー実装 / テスト用モックの強化）
- 単元サイズや手数料モデルを銘柄別にサポート（lot_map）
- DuckDB の prices_daily / raw_financials データ収集パイプラインの整備
- AI モデルやプロンプトの改善、API エラーハンドリングの強化

ライセンス / 免責
-----------------
この README はソースコードに基づく技術ドキュメントです。実際の運用では金融商品取引に関する法規制・リスク管理・十分なテストが必要です。自動売買による損失については責任を負いません。

補足や README に追記して欲しい情報（例: 具体的な依存バージョン、運用手順、CI/CD 設定等）があれば教えてください。README を更新して反映します。