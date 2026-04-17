KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買／研究・監視用ライブラリ群です。本リポジトリは以下の主要機能を含みます。

- ExecutionEngine（発注／リスク管理／リコンシリエーション）起動スクリプト
- Monitoring（システム監視／注文監視／リスク監視／アラート）および監視 DB
- Portfolio 構築ユーティリティ（候補選定・重み付け・サイズ決定・セクター制約）
- Research（ファクター計算・将来リターン・IC計算・統計サマリ）
- AI 支援モジュール（ニュースの NLP スコアリング、レジーム判定）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な特徴
--------
- 環境変数/.env での柔軟な設定読み込み（プロジェクトルートの .env / .env.local を自動取り込み）
- Execution と Monitoring の DB は運用環境に応じた分離（paper_trading 用に専用 DB を利用）
- DuckDB を用いたバッチ/研究用集計、SQLite を用いた軽量永続化（監視・発注ログ）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価と市場レジーム判定（フェイルセーフ実装）
- LINE Push によるアラート通知（クールダウン付き）
- 停止はフラグファイル（data/kill.flag）を書き込むことで安全に指示可能

セットアップ
------------

前提（推奨）
- Python 3.10+
- SQLite（OS 標準で OK）
- インターネット接続（OpenAI / LINE / ブローカ API 利用時）

必須パッケージ（例）
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）

インストール（例）
- 仮想環境作成・有効化後に必要パッケージをインストールしてください（requirements.txt は本リポジトリに含まれていないため、手動でインストール）:

  pip install duckdb psutil requests openai streamlit

環境変数 / .env
- 自動読み込み順序: OS 環境変数 > .env.local > .env（プロジェクトルートを .git/.pyproject.toml から自動検出）
- 自動読み込みを無効化する場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

代表的な環境変数（.env に設定する例）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- KABUSYS_ENV=development|paper_trading|live
- PAPER_FILL_MODE=instant|partial|never|reject
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- LOG_LEVEL=INFO

使い方
------

1) 監視プロセスを起動（Monitoring）
- デフォルトは MONITOR_POLL_INTERVAL=60 秒間隔。環境変数で上書きできます（秒）。
- 起動方法:

  python -m kabusys.run_monitoring

  （必要に応じて MONITOR_POLL_INTERVAL を設定）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring

- 備考:
  - 監視は Settings.sqlite_path（data/monitoring.db 既定）に接続します。init_monitoring_db() が必要テーブルを自動生成します。
  - run_monitoring 起動時にプロセス優先度を "high" に設定しようとします（psutil による設定で失敗しても安全にスキップします）。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成するとループを抜けます。

2) 実行エンジンを起動（Execution）
- KABUSYS_ENV が paper_trading の場合は Broker の Mock 実装を使い、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に書き込みます（本番 DB と完全分離）。
- 起動方法:

  python -m kabusys.run_execution

- 備考:
  - 起動時に ExecutionEngine が data/execution.pid を生成します。プロセス監視は SystemMonitor が行います。
  - 起動前に data/stop_requested.flag が存在すると起動をスキップします。

3) Streamlit ダッシュボード
- 監視 DB を読み込み、Overview / Positions / Orders / System を可視化します。
- 起動方法（例: 開発環境）:

  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート生成ツール
- paper_trading DB のトレードログ・監視データから検証レポートを作成します。
- 起動方法:

  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5) AI 関連（ニュース NLP / レジーム判定）
- OpenAI API キー（OPENAI_API_KEY）を設定してください。
- ニューススコアリング（ai.score_news）やレジーム判定（ai.regime_detector.score_regime）は DuckDB 接続と target_date を渡して呼ぶ API です（ライブラリ的に利用する想定）。
- エラーや API 障害時はフェイルセーフ（0.0 等でスコアにフォールバック）します。

運用上の注意・フラグ制御
- 強制停止（Execution 停止）は data/kill.flag を作成することで KillSwitch により検出されます。KillSwitch はリスク条件（ドローダウン・ポジション上限）によって自動的に書き込まれることがあります。
- 停止フラグを手動で解除するには KillSwitch.clear() を呼ぶか、data/kill.flag を削除してください。
- 実行中の強制停止要求は data/stop_requested.flag により行えます（run_monitoring / run_execution はこのフラグを監視して安全終了します）。

ディレクトリ構成（主要ファイル）
--------------------------------
ここでは src/kabusys 以下の主要モジュールを抜粋します：

- src/kabusys/
  - __init__.py                — パッケージメタデータ
  - config.py                  — Settings クラス（環境変数読み込み・検証）
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト

- src/kabusys/monitoring/
  - monitoring_db.py           — SQLite テーブル初期化・CRUD（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py          — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py           — 注文滞留・約定異常監視
  - risk_monitor.py            — ドローダウン・ポジション上限監視（ダッシュボード更新・リスクログ）
  - kill_switch.py             — kill.flag の書込み・評価ロジック
  - monitoring_engine.py       — 各 Monitor を組み合わせたポーリングエンジン
  - alert_manager.py           — LINE push 通知の送信（クールダウン管理）
  - streamlit_dashboard.py     — Streamlit による監視ダッシュボード
  - __init__.py                — 公開 API

- src/kabusys/execution/
  - order_manager.py           — 注文作成・キャンセル・同期の外向き API
  - reconciler.py              — 起動時の注文／ポジション照合ロジック
  - （その他 execution 関連: broker_api, execution_engine, order_repository 等は同階層に存在）

- src/kabusys/portfolio/
  - portfolio_builder.py       — 候補選定・等重／スコア重み
  - position_sizing.py         — 株数決定（単元丸め・risk_based 等）
  - risk_adjustment.py         — セクターキャップ・レジーム乗数
  - __init__.py

- src/kabusys/research/
  - factor_research.py         — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py     — 将来リターン計算・IC・統計要約
  - __init__.py

- src/kabusys/ai/
  - news_nlp.py                — raw_news を LLM で評価して ai_scores に書込む
  - regime_detector.py         — ETF + マクロニュースで市場レジーム判定
  - __init__.py

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
  - __init__.py

- src/kabusys/utils/
  - process_priority.py        — cross-platform プロセス優先度 / CPU affinity ユーティリティ
  - __init__.py

監視 DB（monitoring_db）主要テーブル
- system_status(recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs(logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions(code, qty, avg_price, current_price, updated_at)
- risk_logs(logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard(id=1, updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

補足・実装メモ
---------------
- Settings クラスは環境変数の検証を行います（KABUSYS_ENV の有効値は development / paper_trading / live）。
- Paper Trading の振る舞い:
  - KABUSYS_ENV=paper_trading の場合、run_execution は paper_sqlite_path（既定 data/paper_trading.db）を使用して発注ログを分離します。
  - PAPER_FILL_MODE により MockBroker の約定挙動を制御できます（instant/partial/never/reject）。
- OpenAI に関する実装はリトライ・レスポンス検証等の堅牢化処理が組み込まれていますが、API 利用時はコストとレート制限に注意してください。
- process_priority / cpu_affinity の設定は OS に依存します。権限不足や未対応 OS の場合は警告を出してスキップします。

ライセンス・貢献
----------------
- 本 README にはライセンス情報は含まれていません。実際のプロジェクトでは LICENSE を確認してください。
- 追加のユニットテスト、ドキュメント拡充、運用手順書（systemd サービス定義やコンテナ化等）を提案します。

以上。必要であれば、README をさらに詳しく（systemd / docker-compose 用の実行例、.env.example のテンプレート、各コンポーネントの API 使用例等）拡張します。どの部分を詳細化しますか？