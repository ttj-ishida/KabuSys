KabuSys — 日本株自動売買システム（README）
==================================

概要
----
KabuSys は日本株向けの自動売買フレームワークの一部です。本リポジトリには以下の主要コンポーネントが含まれます。

- 実行エンジン起動スクリプト（ExecutionEngine）
- 監視（Monitoring）コンポーネント（System / Trade / Risk / Kill Switch / Alerts）
- ポートフォリオ構築（候補選定・重み付け・サイズ算出）
- 研究用モジュール（ファクター計算、特徴量探索）
- ニュース NLP / レジーム判定（OpenAI を用いたスコアリング）
- 各種ユーティリティ（プロセス優先度、DB 初期化、レポート生成、Streamlit ダッシュボード）

目的は、取引エンジンの安全な稼働（自動復旧・監視・アラート）と、戦略研究 / ポートフォリオ構築のための再利用可能なユーティリティを提供することです。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは Mock ブローカーを使い、paper_trading 用 DB に記録
  - ブローカー抽象化、リスク管理・注文管理・リコンシリエーション機能
- Monitoring（run_monitoring.py / MonitoringEngine）
  - システム負荷・プロセス監視、データ鮮度チェック、注文滞留・約定異常監視
  - ダッシュボード用 DB（SQLite）への永続化、Kill Switch（flag ファイルで ExecutionEngine 停止）
  - LINE 通知（AlertManager）によるプッシュ通知（トークンが設定されている場合）
  - Streamlit ベースの監視ダッシュボード
- ポートフォリオ構築（portfolio モジュール）
  - 候補選定 / 等重・スコア重み付け / ポジションサイズ計算 / セクター上限・レジーム乗数
- 研究用（research モジュール）
  - Momentum/Value/Volatility ファクター計算、将来リターン、IC 計算、統計サマリー
  - DuckDB を使った高速なローカル分析（prices_daily / raw_financials テーブル参照）
- AI（ai モジュール）
  - news_nlp: OpenAI を用いたニュースセンチメント（銘柄別）スコアリング（ai_scores テーブルへ）
  - regime_detector: ETF の MA とマクロニュースのセンチメントを合成して市場レジーム判定
- ツール
  - paper_verification_report: paper_trading DB を集計して検証レポートを生成

環境変数 / 設定（主要）
-----------------------
Settings クラスで多数の設定を環境変数として取得します。自動で .env / .env.local をプロジェクトルートからロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須（実行に応じて）
- JQUANTS_REFRESH_TOKEN — J-Quants API（使用する場合）
- KABU_API_PASSWORD — kabu ステーション API パスワード

推奨 / 重要
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp, regime_detector）に必須
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。paper_trading は専用 DB を使用します。
- PAPER_FILL_MODE — paper_trading の注文約定モード（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視ログ等の SQLite（デフォルト: data/monitoring.db）※Monitoring は環境にかかわらず本番 sqlite_path を使用
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH — ExecutionEngine の PID 管理ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch が書き込むフラグ（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL — ログレベル（DEBUG / INFO / …）

セットアップ
----------
1. Python（推奨: 3.10+）を用意します。
2. 必要パッケージをインストールします（例）:
   pip install duckdb psutil openai requests streamlit
   （プロジェクトに requirements.txt があればそれを使用してください）
3. プロジェクトルートに .env を用意（.env.example を参考に）。主に上記の環境変数を設定します。
   - 自動ロード: .env / .env.local はプロジェクトルート（.git や pyproject.toml の位置）から読み込まれます。
   - 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

注意:
- Monitoring は監視ログを保存する SQLite（data/monitoring.db）を使用します。初回実行時にテーブルを自動作成・マイグレーションします。
- Paper trading は本番 DB と分離して data/paper_trading.db を使います（KABUSYS_ENV=paper_trading）。

使い方（主要コマンド）
--------------------

1) 監視ループ起動
- デフォルトポーリング 60 秒（MONITOR_POLL_INTERVAL で変更可能）
- 実行:
  python -m kabusys.run_monitoring
- 例（ポーリング 30 秒）:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 補足:
  - run_monitoring は起動時にプロセス優先度を高く設定し、monitoring DB の初期化を行います。
  - Monitoring は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します。

2) 実行エンジン（ExecutionEngine）起動
- 実行:
  python -m kabusys.run_execution
- Paper trading モード:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  （この場合、MockBrokerClient を使って PAPER_TRADING_SQLITE_PATH に記録されます）
- 補足:
  - 起動時にプロセス優先度を高く設定します。
  - 起動直後に Reconciler による同期が行われ、未確定注文のリコンシリエーションが試行されます。
  - Kill Switch（data/kill.flag）があれば ExecutionEngine 停止のトリガーになります。起動時に KILL_FLAG_CLEAR_ON_START が真なら自動でクリアされます。

3) Streamlit ダッシュボード
- 実行:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 読み取り専用で SQLite の最新状態を表示します。MonitoringEngine を先に起動してデータを流すと有用です。

4) Paper Trading 検証レポート
- 実行:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション:
  --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

5) AI / レジーム関連（OpenAI API 必須）
- ニュースの銘柄別センチメントスコアを生成:
  - スクリプト経由または kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
- 市場レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

運用上の注意
-------------
- kill.flag（Settings.kill_flag_path）を書き込むと ExecutionEngine 停止を促す仕組みです。KillSwitch は冪等にファイルを書きます（既存なら書き直さない）。
- Monitoring のチェックは system_status / trade_logs / risk_logs 等に記録します。monitoring_db.init_monitoring_db() が DB スキーマ初期化と簡易マイグレーションを行います（列の追加など）。
- Process priority / CPU affinity の設定は utils.process_priority で行われます。権限不足や未対応 OS の場合は警告が出てスキップされます。
- OpenAI 呼び出しはリトライロジック・JSON バリデーションが組み込まれていますが、API キーがない場合は該当処理は失敗します（例外またはフォールバック）。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / Settings 管理（.env 自動読み込み）
- run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                — ExecutionEngine 起動スクリプト

- monitoring/
  - __init__.py
  - monitoring_db.py               — SQLite スキーマ初期化・永続化層
  - system_monitor.py              — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py               — 注文滞留・約定異常監視
  - risk_monitor.py                — ドローダウン / ポジション上限監視
  - kill_switch.py                 — フラグファイルによる停止シグナル書き込み
  - alert_manager.py               — LINE API による通知
  - monitoring_engine.py           — 各 Monitor を束ねるループ
  - streamlit_dashboard.py         — Streamlit ダッシュボード

- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - ...（ブローカー抽象・エンジン構成等）

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - factor_research.py
  - feature_exploration.py

- ai/
  - news_nlp.py                    — OpenAI を使ったニューススコアリング
  - regime_detector.py             — マクロ + ETF MA によるレジーム判定

- tools/
  - paper_verification_report.py

- utils/
  - process_priority.py
  - ...（補助ユーティリティ）

補足・実装上のメモ
-----------------
- DuckDB を分析用のローカルデータベースとして使用しています（prices_daily / raw_financials / raw_news 等のテーブル想定）。
- 多くの関数は「外部 API に依存しない」ことを意図しており、DuckDB / SQLite 接続を渡すことで副作用を限定しています（テスト容易性を配慮）。
- .env のパースは強めに実装されており、クォート・エスケープ・コメント等に対応しています。
- Paper trading モードは本番 DB と完全に分離するよう設計されています。

問い合わせ / 貢献
-----------------
- 仕様や拡張についてはソースの docstring を参照してください（各モジュールに詳細なコメントがあります）。
- バグ修正や機能追加の際はユニットテストと簡単なローカル検証を推奨します（特にブローカー API や DB 書き込み周り）。

以上。必要であれば README に実行例・.env.example のテンプレートや systemd / supervisor 用の起動スクリプト例を追加できます。どの情報を追記したいか教えてください。