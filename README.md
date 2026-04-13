KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買システム（KabuSys）の主要コンポーネント群を含みます。
設計方針として「テストしやすい純粋関数・DB分離」「ルックアヘッドバイアス回避」「外部API失敗時のフェイルセーフ」を重視しています。

主な機能
--------
- Execution（注文実行）
  - OrderManager / ExecutionEngine による注文作成・送信・再同期（Reconciler）
  - Paper trading モード（MockBrokerClient）と本番モードの切替
  - リスク管理（RiskManager）とオーダーリポジトリ（SQLite）
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - system_status / trade_logs / risk_logs / positions / dashboard を永続化する SQLite ベースの監視DB
  - kill.flag による安全停止（KillSwitch）
  - LINE による通知（AlertManager）
  - Streamlit ダッシュボード（監視 UI）
- Portfolio construction（銘柄選定・配分・株数算出）
  - 候補選定、等金額/スコア加重配分、セクター制限、リスクベースサイズ算出
- Research（ファクター計算・特徴量解析）
  - Momentum / Volatility / Value ファクター計算（DuckDB を利用）
  - Forward return / IC / 統計サマリー
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント集計と ai_scores への登録
  - マクロ記事を用いた市場レジーム（bull/neutral/bear）判定
  - API 呼び出しはリトライ・フェイルセーフ実装
- ツール
  - paper_verification_report: Paper Trading の検証レポート生成

セットアップ
----------
前提
- Python 3.9+
- DuckDB, SQLite を利用
- ネットワーク接続（OpenAI / LINE 等を使う場合）

依存パッケージ（例）
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)

pip でインストールする例:
pip install duckdb psutil requests openai streamlit

環境変数・.env
- 設定は .env または OS 環境変数から読み込まれます。プロジェクトルートに .env/.env.local を置くと自動読み込みされます。
- 自動読み込みを無効にする場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
主な環境変数
- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant | partial | never | reject）デフォルト: instant
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- PID_FILE_PATH / KILL_FLAG_PATH: pid / kill flag のパス
注意: 必須のキーが未設定だと Settings が ValueError を投げます（config.py 内 _require）。

使い方（主要スクリプト）
----------------------

1) 監視ループ（MonitoringEngine 単体起動）
- デフォルトは本番 sqlite_path を使って監視を行います（KABUSYS_ENV に依存せず本番 DB を参照）。
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒。デフォルト 60）。
起動例:
python -m kabusys.run_monitoring

2) 実行エンジン（ExecutionEngine）
- KABUSYS_ENV=paper_trading の場合、専用の Paper Trading DB を使用し MockBroker を利用します（本番 DB と分離）。
起動例:
python -m kabusys.run_execution
（必要な環境変数を設定してください。Paper モードでは PAPER_TRADING_SQLITE_PATH を指定できます）

3) Streamlit 監視ダッシュボード
- 起動例:
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードは監視用 SQLite を読み取り専用で開きます。

4) Paper Trading 検証レポート
- ツール: paper_verification_report
- 起動例:
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db オプションでデータベースパスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）。

5) AI 機能（ニューススコア / レジーム判定）
- 関数: kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime
- DuckDB 接続を渡して呼び出す設計です。OpenAI API キー（OPENAI_API_KEY）を環境変数か引数で指定してください。
- 例（簡易）:
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect("data/kabusys.duckdb")
score_news(conn, target_date=date(2026,4,10), api_key="...")

注意点・挙動
- プロセス優先度: run_monitoring/run_execution 起動時に set_process_priority("high") を試行します。権限がない場合は警告ログを出してスキップします。
- DB スキーマのマイグレーション: init_monitoring_db は冪等にテーブル作成と簡単なカラム追加（migration）を行います。
- AI モジュール: 失敗時はフェイルセーフ（スコアを 0 にする／書き込みをスキップ）する設計です。OpenAI API の制限やエラーはリトライ実装があります。
- time.now / date.today の扱い: AI モジュール等はルックアヘッドバイアス回避のため外部状態（日付）を直接参照しないよう注意してあります（関数引数に target_date を取ります）。

設定およびトラブルシューティング
--------------------------------
- .env の構文は shell ライク（export を許容、クォート・コメント処理あり）。自動読み込みはプロジェクトルート (.git または pyproject.toml を起点) が見つかった場合のみ実行されます。
- 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- MONITOR_POLL_INTERVAL が 0 や非整数ならデフォルト 60 秒にフォールバックします。
- Paper Trading と本番の DB は分離されています。Paper モード時は PAPER_TRADING_SQLITE_PATH を使用します。

ディレクトリ構成（src/kabusys の主要ファイル）
--------------------------------------------
- __init__.py
- config.py — 環境変数 / .env 管理（Settings クラス）
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト（paper/live 切替）
- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, risk_logs, positions, dashboard）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度 / pid チェック
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の作成・管理
  - alert_manager.py — LINE 通知（クールダウン機能付き）
  - monitoring_engine.py — 監視コンポーネントを束ねる実行ループ
  - streamlit_dashboard.py — Streamlit 監視 UI
- execution/
  - order_manager.py — 注文作成・送信の高レベル API
  - reconciler.py — 起動時リコンシリエーション（OrderSent 等の同期）
  - （その他：broker_factory, execution_engine, risk_manager, order_repository 等が存在）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数算出、最大・aggregate cap 適用
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB を使用）
  - feature_exploration.py — 将来リターン・IC・統計サマリー等
- ai/
  - news_nlp.py — ニュースの LLM センチメント集計と ai_scores 書き込み
  - regime_detector.py — ETF ma200 + マクロニュースでレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート出力ツール

開発メモ / 設計メモ
-------------------
- DuckDB は価格・財務テーブル等の高速分析用に用います。research モジュールは DuckDB 接続を受け取り SQL と Python で計算します（外部 API は呼ばない設計）。
- SQLite は永続化（監視ログ、注文履歴、positions 等）に使用します。監視用 DB は monitoring モジュールで扱います。
- LLM（OpenAI）呼び出しは JSON Mode を用いて厳密な JSON を期待し、レスポンスのバリデーション・トリミング・クリップを行います。
- フェイルセーフ: 多くの箇所で API 失敗時にスキップ・デフォルト値で継続する実装が入っています（運用で致命的停止を避けるため）。

ライセンス
----------
（リポジトリにライセンス情報がない場合はここに追記してください。）

最後に
------
この README はコードベースから抽出した振る舞いと意図をまとめたものです。実運用前に .env の設定・依存パッケージ・API キーの管理・監視アラート設定を必ず確認してください。必要であれば、特定の機能（例: ExecutionEngine の詳細な設定、Broker API のモック化方法、DuckDB スキーマ定義）についての追記ドキュメントを作成します。必要な箇所を教えてください。