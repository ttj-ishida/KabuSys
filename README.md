# KabuSys — README

このリポジトリは「KabuSys」という日本株自動売買システムの一部です。監視・執行・ポートフォリオ構築・リサーチ・AI（ニュースセンチメント／レジーム判定）などのモジュールが含まれています。本READMEはコードベース（src/kabusys/*）を元にした導入・利用ガイドです。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 環境変数 / 設定
- 実行方法（主要コマンド）
- ファイル / ディレクトリ構成（概要）
- 運用上の注意点

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤の一部実装です。主な責務は次のとおりです。

- ExecutionEngine：ブローカーとの発注・注文管理（本番 / Paper Trading 切替）
- Monitoring：システム稼働状況／注文状況／リスク監視のポーリング・ログ永続化
- Portfolio construction：銘柄選定・重み付け・ポジションサイズ算出
- Research：DuckDB を用いたファクター計算・特徴量探索
- AI モジュール：ニュースのセンチメント（OpenAI）や市場レジーム判定
- 運用ツール：Paper Trading 検証レポート生成・Streamlit ダッシュボード

設計上のポイント：
- DB は SQLite（監視ログ等）・DuckDB（時系列 / ファクタ計算）を使用
- .env / .env.local による環境変数自動読み込み（config.py）
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
- OpenAI 呼び出しはフェイルセーフ（API失敗時は安全側にフォールバック）

---

## 主な機能一覧

- monitoring
  - system_monitor: CPU/メモリ/ディスク、Execution プロセス存在確認、データ鮮度チェック
  - trade_monitor: 滞留注文・約定異常価格検出
  - risk_monitor: ドローダウンおよびポジション数の監視、kill flag の生成
  - alert_manager: LINE push による通知（クールダウンあり）
  - streamlit_dashboard: 監視情報の可視化
- execution
  - ExecutionEngine 起動・停止管理、リコンサイル（再起動後の同期）
  - Broker クライアントの抽象化（paper_trading 用 Mock を含む）
- portfolio
  - 候補選定、等配分／スコア重み、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算
- research
  - Momentum、Volatility、Value ファクター計算
  - 将来リターン計算、IC（情報係数）等の分析ユーティリティ
- ai
  - news_nlp.score_news: ニュースをOpenAIでスコアリングして ai_scores に保存
  - regime_detector.score_regime: ETF・マクロニュースを元にレジーム判定して DB に書込
- tools
  - paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順

前提：Python 3.9+（型アノテーションなどを利用しているため推奨バージョンを使ってください）

1. リポジトリをクローン／配置
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（代表例）
   - pip install duckdb psutil requests openai streamlit
   - 追加の依存がある場合は適宜インストールしてください（プロジェクトに requirements.txt があればそれを使う）
4. .env を作成（プロジェクトルートに配置）
   - config.py はプロジェクトルート（.git または pyproject.toml を基準）で `.env` / `.env.local` を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 例（最低限）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...  （AI機能を使う場合）
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 環境変数 / 設定（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - execution: paper_trading の場合は MockBroker を使用し、専用の paper_sqlite_path を使います
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant / partial / never / reject）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか (1/0)
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

config.py によって .env と .env.local が自動読み込みされます（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 実行方法（主要なコマンド）

以下は src 配下のモジュールをモード切替で実行する例です。プロジェクトパッケージとして実行できる前提です（カレントをリポジトリルートにしてください）。

- Monitoring（監視ループ）
  - 環境変数でポーリング間隔を変更可能:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止方法:
    - プロセスを止めるか、プロジェクトルートの data/stop_requested.flag ファイルを作成するとループが検知して終了します。
  - 補足:
    - Monitoring は Settings.env にかかわらず SQLITE_PATH の本番 DB を使用します（監視は本番 DB を参照する想定）。

- ExecutionEngine（発注エンジン）
  - 本番:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合は settings.paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）に書き込まれ、本番 DB と分離されます。
  - 停止/制御:
    - 実行中は data/execution.pid に PID を保持（設定で変更可）。
    - data/stop_requested.flag を作成すると起動ループが検知して停止します。
    - kill.flag は KillSwitch が作成し、Execution 停止のために利用されます（KILL_FLAG_PATH）。

- Streamlit ダッシュボード（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開きます。MonitoringEngine を先に起動してデータを作成してください。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI モジュール（プログラムから呼び出す）
  - ニューススコアリング（例）
    - from openai と接続済みの DuckDB コネクションを渡す必要があります。呼び出し例（単発）:
      - from kabusys.ai.news_nlp import score_news
      - cnt = score_news(conn, target_date, api_key="...")  # conn は duckdb.connect() の接続
  - レジーム判定:
      - from kabusys.ai.regime_detector import score_regime
      - score_regime(conn, target_date, api_key="...")

---

## 運用上の注意点 / 実装の挙動

- Monitoring と Execution は stop_requested.flag（data/stop_requested.flag）による協調的停止をサポートします。運用時に安全に停止させるために利用してください。
- Monitoring は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。paper_trading モードでも監視は本番の監視 DB を参照する設計です。
- Execution の paper_trading は DB を分離して安全に検証できます（PAPER_TRADING_SQLITE_PATH）。
- process_priority（utils/process_priority.py）は psutil を使ってプロセス優先度を設定します。権限不足などで設定できない場合は警告を出してスキップします。
- OpenAI API 呼び出しはリトライ・バックオフを実装しており、JSON の検証・クリッピング等の安全策が入っています。APIキーがないと例外になるので注意してください。
- config.py の .env パーサは export KEY=val 形式やクォート、インラインコメントに対応しています。

---

## ディレクトリ構成（抜粋）

以下は主要ファイルの一覧（src/kabusys 以下）。完全なファイルはリポジトリを参照してください。

- src/kabusys/
  - __init__.py
  - config.py
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - data/                    — （実行時に使うデータディレクトリ例: monitoring.db, paper_trading.db, stop_requested.flag 等）
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）処理
    - regime_detector.py     — レジーム判定（ETF + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ + 永続層（MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - (その他発注関連モジュール)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py

---

## 参考例（よく使うコマンド）

- 監視ループを 30 秒間隔で起動：
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading で Execution を起動：
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード起動：
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート（直近）：
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 最後に

本README はソースコード（src/kabusys）からの抜粋に基づく概要ドキュメントです。実運用や本番接続に移る際は、環境変数・APIキーの管理、DBバックアップ、監視設定（閾値）などを慎重に運用してください。実装や仕様の詳細は該当ファイルの docstring / コメントを参照してください。ご不明点があれば特定箇所を指定して質問してください。