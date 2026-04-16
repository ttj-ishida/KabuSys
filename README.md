# KabuSys

日本株自動売買システムの一部（ライブラリ＋運用スクリプト群）。  
このリポジトリはトレーディングロジック、モニタリング、バックテスト／リサーチ補助、AI を用いたニュース分析などのモジュールで構成されています。

注意: 本 README はコードベース（src/kabusys 配下）から作成しています。実行には Python3.9+ 相当と外部ライブラリ（duckdb / psutil / openai / requests / streamlit など）が必要です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト／コマンド例）
- 環境変数（主なもの）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システム（取引実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI ニュース解析など）を構成するモジュール群です。
- DuckDB を用いた時系列価格・財務データの分析、SQLite を用いた監視・発注ログ永続化、OpenAI API を用いたニュースセンチメント評価などの機能を備えています。
- 実運用向けにプロセス優先度・PID 管理・kill フラグによる安全停止等のオペレーション機能が組み込まれています。

---

機能一覧
- Execution（発注）
  - ExecutionEngine（run_execution.py）でブローカー接続・注文管理を実行
  - Paper trading モードあり（KABUSYS_ENV=paper_trading）：MockBrokerClient を使用して本番 DB と分離（data/paper_trading.db）
  - Reconciler：再起動時の注文／ポジション突合
  - OrderManager / OrderRepository：注文状態管理と SQLite 永続化
- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク/プロセスの監視、データ鮮度チェック
  - TradeMonitor：滞留注文検出、約定異常検出
  - RiskMonitor：ドローダウン／ポジション上限監視
  - KillSwitch：リスクトリガーで execution の停止フラグを作成
  - AlertManager：LINE へのプッシュ通知（任意設定）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- Portfolio（構築）
  - 候補選定、等比重／スコア重み配分、ポジションサイズ計算、セクター上限、レジーム乗数
- Research（リサーチ）
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリ）
- AI
  - news_nlp: raw_news を OpenAI に送って銘柄別センチメントを ai_scores に書き込む
  - regime_detector: ETF MA とマクロニュースを LLM で判定して market_regime を更新
- Tools
  - paper_verification_report: Paper Trading DB を解析して検証レポートを出力

---

セットアップ手順（例）
1. Python 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要ライブラリのインストール（最低限）
   - pip install duckdb psutil requests openai streamlit
   ※ 実際にはプロジェクトの運用要件に応じて追加の依存が必要な場合があります。

3. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込み（デフォルト）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
     - PAPER_TRADING_SQLITE_PATH（paper トレード DB）
     - SQLITE_PATH（監視 DB, デフォルト data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル, デフォルト data/kabusys.duckdb）
     - LOG_LEVEL（DEBUG/INFO/...）
     - MONITOR_POLL_INTERVAL（秒、監視ポーリング間隔、デフォルト 60）

4. データディレクトリ準備
   - data/ 配下に SQLite / DuckDB ファイルが作成されます（初回起動時に Monitoring DB のテーブル作成が行われます）。
   - 必要に応じて権限やディスク容量を確認してください。

注意: process priority を変更する処理があるため一部操作は管理者権限やプラットフォームに依存します（psutil を使用）。

---

使い方（主要スクリプト・コマンド例）

1) Execution Engine の起動
- 本番 / Paper 環境判定は KABUSYS_ENV で行われます（paper_trading の場合は専用 DB を使用）。
- 実行:
  - python -m kabusys.run_execution
  - スクリプトは data/execution.pid、data/stop_requested.flag を参照します。
  - stop の仕組み: data/stop_requested.flag を作成するとループが停止します。KillSwitch は data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります。

2) Monitoring の起動
- run_monitoring.py は SystemMonitor のポーリングループを実行します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視を本番 DB に対して行う設計）。
- 実行:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）。
  - 停止は data/stop_requested.flag を置くか Ctrl+C。

3) Streamlit ダッシュボード（監視 UI）
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 現在のダッシュボード / ポジション / 注文 / システム状態を閲覧できます（読み取り専用モード推奨）。

4) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

5) AI 機能（ニュース NLP / レジーム判定）
- OPENAI_API_KEY が必要です。
- ニューススコアリング:
  - 呼び出し API: kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡して実行します（ライブラリ関数として）。
- レジーム判定:
  - 呼び出し API: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

主な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（必須ではないが妥当な値を設定）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）、正の整数（デフォルト 60）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper トレード用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（AI 機能）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: API 認証用（必須）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
- PID_FILE_PATH, KILL_FLAG_PATH: PID / kill flag のパスをカスタマイズ可能
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 に設定すると .env 自動ロードを無効化

.env の自動ロード処理について:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env`→`.env.local` の順で読み込みます。OS 環境変数は保護されます。

---

運用上の注意
- Monitoring は監視ログ（system_status / trade_logs / risk_logs / positions / dashboard）を SQLite に出力します。run_monitoring 実行時に init_monitoring_db によりテーブルが作成されます（冪等処理あり）。
- run_monitoring は監視用 DB を常に本番 sqlite_path（Settings.sqlite_path）で接続します（KABUSYS_ENV に依存しない設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と完全分離されます。
- process priority / CPU affinity 設定は psutil に依存し、実行プラットフォームで権限不足だと警告が出ますが処理は続行します。
- kill.flag / stop_requested.flag による外部停止フラグがあり、安全停止のために使用してください。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定読み込みロジック
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄スコア化ロジック
    - regime_detector.py — 市場レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB 初期化 / ラッパー
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各モニタ
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE 通知送信
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - streamlit_dashboard.py — 監視ダッシュボード（Streamlit）
  - execution/
    - order_manager.py, reconciler.py, ... — 発注・再突合ロジック
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築
  - research/
    - factor_research.py, feature_exploration.py — ファクター計算・統計
  - data/ (実行時に使用する想定)
    - monitoring.db (SQLite, デフォルト)
    - paper_trading.db (paper 用 SQLite)
    - kabusys.duckdb (DuckDB)
    - stop_requested.flag, kill.flag, execution.pid などのフラグ/管理ファイル
  - utils/
    - process_priority.py — プロセス優先度設定ユーティリティ

---

補足 / 開発者向けメモ
- DuckDB 接続（duckdb.connect）を関数に渡して直接 SQL を叩く設計です。テストでは in-memory DB を用いると容易です。
- OpenAI 呼び出しは外部 API なので、テスト時は _call_openai_api の差し替え（モック）を推奨します（コード内にも注記あり）。
- .env パーサーはクォートやコメント処理を考慮した独自実装があり、エスケープや export 形式に対応します。

---

問題報告・貢献
- 本 README はコードから抽出した要点をまとめたものです。実際の運用・追加機能実装時はユニットテスト・統合テスト・セキュリティ／API キー管理を整備してください。

必要であれば、README に含めるサンプル .env を作成したり、起動スクリプトの運用手順（systemd ユニット例や Dockerfile や docker-compose 設計）を追加で作成します。どの情報を優先して追記しますか？