# KabuSys — README

このリポジトリは日本株向け自動売買プラットフォーム「KabuSys」の一部実装です。  
この README ではプロジェクト概要、主要機能、セットアップ手順、実行方法、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は以下のような機能群を備えた自動売買基盤のコンポーネント群です。

- 注文管理・実行エンジン（ExecutionEngine / OrderManager 等）
- 監視（MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor）
- リコンシリエーション（Reconciler）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算）
- 研究用モジュール（ファクター計算、特徴量探索）
- AI（OpenAI を利用したニュースセンチメント、レジーム判定）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針として、DB（SQLite / DuckDB）を利用したデータ永続化、外部 API（kabu API / OpenAI 等）との抽象化、監視と自動停止（kill flag）による安全性確保が意識されています。

---

## 機能一覧（主なコンポーネント）

- 設定管理: `kabusys.config.Settings`（.env 自動読み込み機能あり）
- 実行:
  - `run_execution.py`：ExecutionEngine を起動（本番 / Paper Trading 切替）
  - Broker クライアントは環境に応じて切替（paper_trading は Mock を使用）
- 監視:
  - `run_monitoring.py`：SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔指定）
  - MonitoringEngine：System / Trade / Risk モニタを束ね、アラート送信や KillSwitch 評価を実行
  - AlertManager：LINE Push を用いた通知（トークン未設定時はログのみ）
  - Streamlit ダッシュボード（`monitoring/streamlit_dashboard.py`）
- リサーチ / データ処理:
  - DuckDB を使ったファクター計算（momentum, volatility, value 等）
  - 将来リターン、IC 計算、統計サマリ
- AI:
  - `ai.news_nlp.score_news`：ニュースを OpenAI（gpt-4o-mini）でスコア化し `ai_scores` テーブルへ
  - `ai.regime_detector.score_regime`：ETF MA とマクロニュースセンチメントを組み合わせて日次レジーム判定
- 運用ツール:
  - `tools.paper_verification_report`：Paper Trading DB の検証レポート出力

---

## セットアップ手順

以下は開発・運用環境の一般的な手順例です。

1. Python 仮想環境の作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil requests openai streamlit
   - その他、実運用に必要なパッケージを追加してください。

   （注）requirements.txt は本リポジトリで提供していません。上記は本コード内で使用されているライブラリの例です。

3. プロジェクトルートに `.env` を作成
   - `.env.example` がある想定（無ければ環境変数で設定）
   - 主要な環境変数（下記「環境変数一覧」を参照）

   自動読み込みについて:
   - `kabusys.config` はプロジェクトルート（.git または pyproject.toml）を探索し、`.env` と `.env.local` を自動読み込みします。
   - テスト等で自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. data ディレクトリ等の作成（必要に応じて）
   - デフォルトの DB パス等は `data/` 以下を想定しています。事前にディレクトリを作成しておくと良いです。
   - 例: mkdir -p data

---

## 環境変数（主なもの）

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - デフォルト: development
  - 実行モードを切替。`paper_trading` 時は mock broker と専用 SQLite を使用。

- SQLITE_PATH
  - デフォルト: data/monitoring.db
  - 監視用 SQLite DB パス（Monitoring）

- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb
  - DuckDB ファイルパス（時系列データ・raw_financials 等）

- PAPER_TRADING_SQLITE_PATH
  - デフォルト: data/paper_trading.db
  - paper_trading 用 SQLite（ExecutionEngine 起動時に `KABUSYS_ENV=paper_trading` で使用）

- PAPER_FILL_MODE
  - デフォルト: instant
  - 有効値: instant | partial | never | reject
  - MockBroker の約定挙動を制御

- OPENAI_API_KEY
  - OpenAI API 利用時に必須（ai.news_nlp, ai.regime_detector）

- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
  - AlertManager が LINE Push を行うために使用

- MONITOR_POLL_INTERVAL
  - 監視ループのポーリング間隔（秒）
  - デフォルト: 60（run_monitoring の挙動を上書き可能）

- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
  - PID や kill flag のパス / 起動時の kill.flag クリア有無（Settings 経由で参照）

---

## 使い方（主要な実行例）

1. 監視ループの起動（system monitor）
   - デフォルトで本番の sqlite_path を使用して監視を行います（環境に関係なく monitoring 用 DB は本番パスを使う実装）。
   - 実行:
     - python src/kabusys/run_monitoring.py
   - ポーリング間隔指定:
     - MONITOR_POLL_INTERVAL=30 python src/kabusys/run_monitoring.py

   - 停止:
     - プロセスに SIGINT（Ctrl+C）を送るか、プロジェクトルート `data/stop_requested.flag` を作成するとループが終了します。

2. ExecutionEngine の起動（注文実行）
   - 実行（デフォルト environment に依存）:
     - python src/kabusys/run_execution.py
   - Paper Trading モードで起動:
     - KABUSYS_ENV=paper_trading python src/kabusys/run_execution.py
     - この場合、MockBroker を用い、データは `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）へ書き込まれます。

   - 停止:
     - `data/stop_requested.flag` を作成するとエンジンの停止処理がトリガーされます。
     - `kill.flag`（Settings.kill_flag_path, デフォルト data/kill.flag）は ExecutionEngine に対する緊急停止命令（KillSwitch の判定・書き込みにより作成）です。

3. Streamlit ダッシュボード
   - 起動方法（監視 DB を読み取り専用で開く）:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4. Paper Trading 検証レポート生成
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

5. AI スコアリング / レジーム判定（プログラム API）
   - news_nlp.score_news(conn, target_date, api_key=None)
   - regime_detector.score_regime(conn, target_date, api_key=None)
   - どちらも OPENAI_API_KEY が必要（または api_key 引数で指定）

---

## 運用上の注意

- process priority の設定: 起動スクリプトは `kabusys.utils.process_priority.set_process_priority("high")` を呼びます。psutil による優先度変更は OS と権限に依存します。権限不足時は警告を出してスキップされます。
- DB マイグレーション: `init_monitoring_db` は実行時にテーブルとカラムの存在確認・簡単なマイグレーション（カラム追加）を行います。
- フェイルセーフ: OpenAI API 呼び出しや外部 API の失敗は多くの箇所でフォールバック（ログ出力・スキップ）されます。重要なマルチステップ処理ではトランザクション（BEGIN / COMMIT / ROLLBACK）を利用しています。
- ローカルファイルによる制御:
  - data/stop_requested.flag: 起動ループの常時チェックで使用（停止指示）
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine の即時停止を要求可能
  - data/execution.pid: ExecutionEngine の PID 管理に使用

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor 起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py                  — ニュースセンチメントの取得/DB 書き込み
  - regime_detector.py           — 市場レジーム判定

- monitoring/
  - __init__.py
  - monitoring_db.py             — SQLite 永続化層（init / CRUD）
  - system_monitor.py            — システム死活 / データ鮮度チェック
  - trade_monitor.py             — 注文滞留 / 約定異常検出
  - risk_monitor.py              — ドローダウン・ポジション上限監視
  - kill_switch.py               — kill.flag 書き込みユーティリティ
  - alert_manager.py             — LINE API でのアラート送信
  - monitoring_engine.py         — 各 Monitor を束ねる
  - streamlit_dashboard.py       — Streamlit 監視ダッシュボード

- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - ...（ブローカー抽象等）

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
  - __init__.py
  - paper_verification_report.py

- utils/
  - __init__.py
  - process_priority.py

（注）上記はこの README に含まれるファイル群を抜粋したものです。詳細は各モジュールの docstring を参照してください。

---

## 開発・拡張メモ

- DuckDB のテーブル（prices_daily, raw_financials, raw_news 等）はリサーチ・AI モジュールで参照されます。これらのテーブルを事前に用意しておく必要があります。
- Broker クライアントや ExecutionEngine の実装は抽象化されているため、実際のブローカー接続を追加実装して差し替え可能です。
- 単体テスト・モック:
  - OpenAI 呼び出しはテストの際にモック可能（内部の _call_openai_api を patch）です。
  - DB を使うコンポーネントはテスト用に一時 SQLite を用いると容易にテストできます。

---

必要に応じて README の補足（依存関係の固定、CI 設定、提供する CLI の拡張など）を作成します。追加で欲しい情報（例: systemd ユニットファイル例、Docker 化手順、requirements.txt の生成など）があれば教えてください。