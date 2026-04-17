README
======

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買システムの一部実装です。本リポジトリには以下の主要コンポーネントが含まれます。

- 実行エンジン起動スクリプト（ExecutionEngine 起動 / 発注管理）
- 監視（Monitoring）コンポーネント（システム状態、注文監視、リスク監視、Kill Switch、アラート）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- 研究用モジュール（ファクター計算・特徴量探索）
- AI 関連モジュール（ニュースセンチメント / 市場レジーム判定）
- 運用・検証ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針の要点：
- 本番と paper_trading は DB を分離（paper_trading は data/paper_trading.db に記録）
- ルックアヘッドバイアス回避のため、日付参照は外部引数ベース（date.today() を避ける箇所あり）
- フェイルセーフ：外部 API 失敗時は安全側にフォールバックして継続する設計

主な機能一覧
-------------
- 実行管理
  - OrderManager / ExecutionEngine（発注・状態管理・リスク制御）
  - Reconciler（再起動時の自動復旧・ブローカー照合）
- 監視
  - SystemMonitor：CPU / メモリ / ディスク / Execution プロセス稼働確認 / データ鮮度確認
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン監視・ポジション上限監視
  - KillSwitch：条件で kill.flag を書き ExecutionEngine を停止させる
  - AlertManager：LINE Messaging API による通知（クールダウン管理付き）
  - MonitoringEngine：上記モニターを束ねたポーリング実行
  - monitoring_db：監視ログ永続化（SQLite）
  - Streamlit ダッシュボード（監視ビュー）
- ポートフォリオ構築
  - 候補選定、等分・スコア加重、セクターキャップ、レジーム乗数、ポジションサイズ算出
- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン・IC・統計サマリー
- AI（OpenAI）
  - ニュースセンチメント（ai_scores への書き込み）
  - 市場レジーム判定（market_regime への書き込み）
- 運用ツール
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード（監視データ可視化）

セットアップ手順
----------------

前提
- Python 3.9+（typing の | 型等を使用）
- SQLite（組み込み）
- 必要な外部ライブラリ：duckdb, psutil, requests, openai, streamlit など

推奨（仮の例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（requirements.txt が無い場合は個別に）
   - pip install duckdb psutil requests openai streamlit

3. プロジェクトルートに .env/.env.local を配置（自動ロード機能あり）
   - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

重要な環境変数（主なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START : 実行制御用
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring で上書き可能）

例（.env 断片）
- KABUSYS_ENV=development
- OPENAI_API_KEY=sk-...
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PAPER_FILL_MODE=instant

DB 初期化
- 監視用 DB のテーブルは init_monitoring_db() により作成されます。run_monitoring / run_execution 実行時に自動作成（冪等）。
- monitoring_db は起動時に必要な列がなければ ALTER TABLE による軽微マイグレーションを行います（peak_value, latency_ms など）。

使い方（起動・ツール）
---------------------

1) 監視ループ起動（Monitoring）
- デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（例: 30）。
- 実行:
  - python -m kabusys.run_monitoring
- 停止:
  - data/stop_requested.flag を作成するとループは検知して終了します（または Ctrl+C）。

2) 実行エンジン起動（Execution）
- 本番・paper_trading に応じて DB とブローカークライアントが切り替わります。
- paper_trading の場合は MockBroker を使い、データは data/paper_trading.db に保存され本番 DB と分離されます。
- 実行:
  - python -m kabusys.run_execution
- 停止:
  - data/stop_requested.flag を作成すると実行中のエンジンが停止要求を受けます。
- 実行中は execution.pid（data/execution.pid など）に PID を書きます。SystemMonitor はこの PID をチェックしてプロセス継続性を確認します。

3) Streamlit ダッシュボード（監視）
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードは監視用 SQLite を読み取り専用で開き、ポジション／注文／システム状態／リスクログを表示します。

4) Paper Trading 検証レポート
- 使い方:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも可）
- 出力: 標準出力に稼働率、注文成功率、送信率、レイテンシ指標、総合判定（PASS/FAIL）を表示

5) AI 機能（ニュース NLP / レジーム判定）
- OPENAI_API_KEY が必要です（引数で渡すことも可）。
- kabusys.ai.score_news(conn, target_date, api_key=None) — ニュースを解析して ai_scores テーブルを更新
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — レジーム判定して market_regime に書込
- API 呼び出しはリトライや失敗時のフォールバック処理を備えています。API キー未設定時は ValueError。

プロセス優先度 / リソース設定
- 起動スクリプト run_monitoring/run_execution は起動時に set_process_priority("high") を呼び出します（psutil 必須）。権限不足時は警告ログを出してスキップします。
- CPU affinity 設定機能 set_cpu_affinity() あり（psutil のサポートに依存）。

停止 / Kill Switch
- リスク条件（ドローダウン超過やポジション上限超過）により KillSwitch が data/kill.flag を書き込み、外部から ExecutionEngine を停止させる運用が可能です。
- Kill flag の存在は Settings.kill_flag_path（デフォルト data/kill.flag）で管理されます。KillSwitch.clear() で削除可能。

注意事項・運用メモ
-----------------
- paper_trading モードは本番 DB を汚さないよう設計されています。運用時は KABUSYS_ENV を適切にセットしてください。
- OpenAI API を使う機能はトークンの取り扱いに注意してください。コスト・レート制限に注意。
- monitoring_db は起動時に必要なテーブル／列を作成するマイグレーション処理を含みますが、大きなスキーマ変更は慎重に。
- .env 自動ロード機能はプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主なファイルと役割）
-------------------------------------
（src/kabusys 以下を想定）

- src/kabusys/__init__.py
  - パッケージ定義（__version__ 等）

- 起動スクリプト
  - src/kabusys/run_monitoring.py         — SystemMonitor ポーリングループ起動
  - src/kabusys/run_execution.py          — ExecutionEngine 起動

- 設定
  - src/kabusys/config.py                 — 環境変数読み込み・Settings クラス

- monitoring
  - src/kabusys/monitoring/monitoring_db.py    — SQLite 永続層（テーブル作成 / CRUD ユーティリティ）
  - src/kabusys/monitoring/system_monitor.py   — システム状態・データ鮮度監視
  - src/kabusys/monitoring/trade_monitor.py    — 注文滞留・約定異常の検出
  - src/kabusys/monitoring/risk_monitor.py     — ドローダウン・ポジション上限監視
  - src/kabusys/monitoring/kill_switch.py      — kill.flag の生成・管理
  - src/kabusys/monitoring/alert_manager.py    — LINE 通知
  - src/kabusys/monitoring/monitoring_engine.py— 複数モニターを束ねる
  - src/kabusys/monitoring/streamlit_dashboard.py — Streamlit ダッシュボード

- execution
  - src/kabusys/execution/order_manager.py      — 発注ロジック（OrderManager）
  - src/kabusys/execution/reconciler.py         — 再起動時リコンシリエーション
  - （その他 broker / engine / repository モジュールが想定される）

- portfolio
  - src/kabusys/portfolio/portfolio_builder.py  — 候補選定・重み計算
  - src/kabusys/portfolio/position_sizing.py    — 株数算出・資金配分
  - src/kabusys/portfolio/risk_adjustment.py    — セクターキャップ・レジーム乗数

- research
  - src/kabusys/research/factor_research.py     — ファクター計算（Momentum / Value / Volatility）
  - src/kabusys/research/feature_exploration.py — 将来リターン / IC / 統計サマリー

- ai
  - src/kabusys/ai/news_nlp.py                  — ニュース NLP（OpenAI 呼び出し・スコア保存）
  - src/kabusys/ai/regime_detector.py           — マーケットレジーム判定（ma200 + macro sentiment）

- tools
  - src/kabusys/tools/paper_verification_report.py — Paper Trading 検証レポート生成
  - src/kabusys/tools/__init__.py

- utils
  - src/kabusys/utils/process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ

付録：よく使うコマンド例
------------------------
- 監視起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

以上。必要であれば .env.example を作成したり、requirements.txt を追記する README の拡張版も作成できます。必要があれば教えてください。