README — KabuSys（日本語）

概要
- KabuSys は日本株の自動売買 / リサーチ / 監視を行うためのモジュール群です。
- DuckDB を用いた時系列データ処理、SQLite による監視ログ、ExecutionEngine による発注フロー、AI（OpenAI）を使ったニュースセンチメント評価、ポートフォリオ構築ユーティリティなどを含みます。
- 設計方針として「ルックアヘッドバイアス防止」「本番／ペーパートレードの分離」「フェイルセーフ（API失敗時のフォールバック）」を重視しています。

主な機能
- Execution
  - ExecutionEngine（発注の作成・送信・同期・再起動時リコンシリエーション）
  - Broker クライアントファクトリ（本番 / mock 切替、KABUSYS_ENV に依存）
  - リスク管理（最大ポジション比率、利用率、ドローダウン等）
- Monitoring
  - SystemMonitor（プロセス生存・CPU/メモリ/ディスク・データ鮮度監視）
  - TradeMonitor（滞留注文・約定異常価格監視）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - MonitoringDB（SQLite に監視ログを永続化）
  - KillSwitch（フラグファイルによる ExecutionEngine 停止）
  - AlertManager（LINE によるプッシュ通知）
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等配分・スコア加重配分、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - news_nlp: ニュースを OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に書き込み
  - regime_detector: MA200 とマクロニュースセンチメントを合成して市場レジームを判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順（ローカル開発用）
1. Python 環境
   - Python 3.10+ を推奨
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール（プロジェクトの requirements.txt があればそれを利用）
   - 例（最小セット）:
     - pip install duckdb psutil requests openai streamlit

3. データディレクトリ
   - デフォルトで data/ 以下にファイルを保存します（duckdb: data/kabusys.duckdb, monitoring SQLite: data/monitoring.db, paper trading DB: data/paper_trading.db）
   - 必要に応じて環境変数でパスを変更できます（下記参照）。

4. 環境変数 / .env
   - プロジェクトはプロジェクトルートの .env / .env.local を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 重要な環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN — （必須）J-Quants トークン
     - KABU_API_PASSWORD — （必須）kabuステーション API パスワード
     - KABUSYS_ENV — development | paper_trading | live （デフォルト: development）
       - paper_trading の場合、MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に書き込みます
     - OPENAI_API_KEY — OpenAI を利用する機能に必須
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE — paper_trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
     - PID_FILE_PATH, KILL_FLAG_PATH など（デフォルト値あり）
     - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（代表的な起動方法）
- ExecutionEngine を起動（本番／ペーパーは KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
  - ペーパートレードで起動する例:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

- Monitoring（単独の監視プロセス）
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 例:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

- Streamlit ダッシュボード（監視DB を読み取り専用で可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニューススコアリング / レジーム判定）
  - OPENAI_API_KEY を環境変数に設定してから、モジュール関数を呼び出して利用します（CLI ラッパーはありません）。
  - 例: kabusys.ai.score_news(conn, target_date, api_key=None) — api_key を None にすると環境変数を使用します。

重要な挙動・注意点
- 設定の自動読み込み:
  - .env ファイルはプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）から読み込まれます。OS 環境変数は上書きされません（.env.local は上書き可）。
- データ分離:
  - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使い、本番監視DB とは分離されます。
  - Monitoring（監視）は常に Settings.sqlite_path（デフォルトの production path）を使用します（run_monitoring のドキュメント参照）。
- PID / kill.flag:
  - ExecutionEngine は pid ファイルを書きます（Settings.pid_file_path）。Monitoring はプロセスの生存を PID で確認し、stale PID を検知すると削除してリスクログを記録します。
  - KillSwitch は kill.flag（Settings.kill_flag_path）を書き込むことで ExecutionEngine に停止シグナルを送ります（冪等）。
- OpenAI API:
  - API 呼び出しはリトライ・バックオフを実装していますが、API キーは必須です（機能によりフォールバックやスキップが設計されている場所もあります）。
- DB スキーマ変更:
  - init_monitoring_db は冪等でテーブルを作成し、既存 DB に対する軽微なマイグレーション（列追加）処理も含みます。
- フェイルセーフ設計:
  - LLM 呼び出し失敗や一部の DB 操作失敗時は例外を上位に伝播させず、可能な限りフェイルセーフな振る舞い（フォールバック値やログ出力）で継続する箇所が多数あります。

ディレクトリ構成（主なファイルと役割）
- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン等）
  - config.py — 環境変数 / 設定管理（.env 自動読込、Settings クラス）
  - run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV による挙動切替）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - execution_engine.py (未表示) — 実際の ExecutionEngine 実装（発注ループ等）
    - broker_factory.py — ブローカークライアント生成
    - order_manager.py — 発注の外向き API（作成・送信・同期）
    - order_repository.py — 注文永続化（SQLite）
    - reconciler.py — 再起動時のリコンシリエーション
    - risk_manager.py — 発注前リスクチェック
    - order_record.py — 注文状態のドメインモデル
  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブル定義と永続化 API
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE Push 通知ラッパー
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・資金配分・端数処理
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Value / Volatility ファクター算出（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - ai/
    - news_nlp.py — ニュースの LLM によるセンチメントスコア化（ai_scores 書き込み）
    - regime_detector.py — MA200 とマクロニュースを合成してレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

開発・テストに関する補足
- DuckDB 接続は関数に注入され、prices_daily / raw_financials / raw_news 等のテーブルを参照します。ローカルでの research 実行には事前に DuckDB にテーブルを用意する必要があります。
- ユニットテストでは OpenAI への実際の API 呼び出しはモックされる設計です（_call_openai_api を patch する等）。
- process priority / cpu affinity の設定は psutil によるため、権限不足や非対応 OS では警告ログを出してスキップします。

ライセンス・注意事項
- この README はコードベースから得られる情報に基づく概要説明です。実運用する際は broker API 周りの実装、注文ロジック、リスクパラメータを十分に確認し、ペーパートレードで検証してから本番運用してください。
- 金融取引に関する責任は利用者にあります。

問題や不明点があれば、ソースコードの該当モジュール（config.py / run_execution.py / run_monitoring.py / monitoring/* / ai/* / portfolio/* / research/*）を参照してください。README にない実行引数や追加設定は各ファイルの docstring に記載されています。