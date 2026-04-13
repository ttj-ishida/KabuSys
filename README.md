# KabuSys

KabuSys は日本株の自動売買システムのコアライブラリ群です。バックエンドの実装（発注、リスク管理、監視、ファクター計算、AI によるニュース評価など）をモジュール化して提供します。本リポジトリはライブラリ / 実行スクリプト群を含み、ローカルや本番での実行を想定しています。

---

主な特徴・目的
- 注文管理、再突合（Reconciliation）、リスク管理を備えた ExecutionEngine
- システム監視（プロセス死活、データ鮮度、滞留注文、約定異常など）とアラート送信（LINE）
- Paper Trading 用の分離された SQLite DB と検証レポート生成
- DuckDB を用いたファクター計算・リサーチ（モメンタム・ボラティリティ・バリューなど）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価と市場レジーム判定
- Streamlit ベースの監視ダッシュボード
- プラットフォーム差分を吸収するプロセス優先度 / CPU affinity ユーティリティ

---

機能一覧（抜粋）
- 実行関連
  - OrderManager（注文生成・送信・同期）
  - Reconciler（再起動時の注文 / ポジション照合）
  - ExecutionEngine 起動スクリプト（run_execution.py）
- 監視関連
  - SystemMonitor / TradeMonitor / RiskMonitor（定期チェック）
  - MonitoringDB（SQLite に対する永続化層・スキーマ管理）
  - MonitoringEngine（複数モニタの統合ポーリング）
  - kill.flag による ExecutionEngine 停止シグナル
  - LINE 通知（AlertManager）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
  - run_monitoring.py（監視ポーリングループ起動スクリプト）
- ポートフォリオ構築
  - 候補選定、重み付け（等金額 / スコア重み）、ポジションサイズ計算、セクター上限、レジーム乗数
- リサーチ
  - DuckDB を用いたファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI（OpenAI）
  - ニュースのセンチメント評価（score_news）
  - 市場レジーム判定（score_regime）
  - 両者とも JSON モードで堅牢に処理、リトライ実装あり
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- ユーティリティ
  - 設定管理（kabusys.config）
    - .env/.env.local の自動読み込み（プロジェクトルート検出）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - プロセス優先度 / CPU affinity（psutil ベース）

---

セットアップ手順（ローカル開発向け、例）
1. リポジトリをクローン
   - git clone <repo_url>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要な主なパッケージ（本コードで参照されているもの）:
     - duckdb, psutil, requests, openai, streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   ※requirements.txt がある場合はそれを使ってください（本コードスニペットには同梱されていません）。

4. 環境変数（最低限）
   - 本番的な機能を使うには以下の環境変数が必要です（config.Settings を参照）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - LINE 通知を使う場合:
     - LINE_CHANNEL_ACCESS_TOKEN
     - LINE_USER_ID
   - その他（任意・デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - SQLITE_PATH, DUCKDB_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, PAPER_FILL_MODE など

5. .env の自動読み込み
   - プロジェクトルートに .env / .env.local を置くと自動で読みこまれます。OS 環境変数が優先され、.env.local は .env を上書きします。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

使い方（主要コマンド例）
- 監視ループを起動（production 監視は常に sqlite_path を参照）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 実行時にプロセス優先度を "high" に設定します（psutil が許可する場合）。

- ExecutionEngine を起動（実注文 / Paper Trading 切替）
  - 本番（KABUSYS_ENV=live）:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - Paper Trading（MockBrokerClient を使用し data/paper_trading.db に記録）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

  - 注意: run_execution は Settings.is_paper を見て paper 用の SQLite を使用します（本番 DB と完全分離）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB が存在しない/読み取り不可な場合はエラーが出ますので MonitoringEngine を先に起動してください。

- プログラム的利用（サンプル）
  - AI ニューススコア:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")
  - リサーチ関数:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

---

設定（主な環境変数と振る舞い）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - paper_trading の場合、ExecutionEngine は MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。run_monitoring のデフォルトは 60 秒。無効値（≤0）ならデフォルトにフォールバック。
- SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH: DB ファイルパス（デフォルトは data ディレクトリ下）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）。KillSwitch は条件を満たすとこのファイルを書き ExecutionEngine に停止を促す。
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）で通知する場合に必要

自動読み込みの挙動
- プロジェクトルートに .env / .env.local を置くと自動で読み込みます（OS 環境変数が保護され、.env.local は .env を上書き）。
- プロジェクトルートは .git または pyproject.toml を基準に探索します。見つからない場合は自動ロードをスキップします。

---

設計上の注意
- 監視（monitoring）は KABUSYS_ENV にかかわらず設定上の sqlite_path（本番用）を使用します。paper_trading とは分離しておく設計意図です。
- Paper Trading は paper 用 SQLite に記録するため、本番 DB を汚染しません。
- OpenAI 呼び出しはリトライ・パース堅牢性を組み込んでいますが、API キー未設定時は ValueError を送出します。
- DuckDB をデータ分析用に利用します。prices_daily / raw_financials / raw_news 等のテーブルを前提としています。
- 並列・性能チューニング: process priority / CPU affinity 設定関数を備えていますが、権限や OS により動作しない場合があります（警告ログ）。

---

ディレクトリ構成（主要ファイル・モジュール）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定の管理（.env ロード含む）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite スキーマ初期化・CRUD ラッパー
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE 通知（クールダウン管理）
    - streamlit_dashboard.py — 監視ダッシュボード（Streamlit）
  - execution/
    - order_manager.py — 注文状態遷移の外向き API
    - reconciler.py — 起動時のリコンシリエーション
    - （その他: broker 関連・execution_engine 等が存在する想定）
  - portfolio/
    - __init__.py
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント評価（OpenAI）
    - regime_detector.py — マクロ + ETF MA によるレジーム判定（OpenAI）
  - monitoring_db.py etc. (上記と重複しないよう構成)
  - utils/
    - __init__.py
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - data/ (デフォルトの DB 保存先、コードリポジトリに含めないこと推奨)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (デフォルト PAPER_TRADING_SQLITE_PATH)

---

付録：よく使うコマンド一覧
- 監視（ローカル）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行（Paper トレード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

問い合わせ・貢献
- バグ報告や機能要望は Issue に記載してください。
- パッチや改善提案は Pull Request を歓迎します。

以上。README の内容はソースを元に要点をまとめたものです。実際の運用では .env の管理、API キーの保護、DB バックアップやアクセス権限に十分ご注意ください。