# KabuSys — README

以下はこのコードベース（src/kabusys）の概要と利用手順です。

目次
- プロジェクト概要
- 主な機能
- 前提 / 依存関係
- セットアップ手順
- 環境変数（主要なもの）
- 実行方法（使い方）
  - 監視ループ（Monitoring）
  - 実行エンジン（ExecutionEngine）
  - 監視ダッシュボード（Streamlit）
  - 検証レポート（Paper Trading レポート）
  - AI 関連（ニュース/NLP・レジーム検出）
- ディレクトリ構成
- 補足・注意点

---

## プロジェクト概要
KabuSys は日本株自動売買システムの一部コンポーネント群です。  
主に以下の領域を実装しています：
- 注文管理・ExecutionEngine（ブローカーインターフェース経由での発注、リコンシリエーション等）
- リスク監視（ドローダウン、ポジション上限など）
- システム監視（CPU/メモリ/ディスク、Execution プロセスの生存確認、データ鮮度）
- ポートフォリオ構築（候補選定・ウェイト計算・ポジションサイズ決定）
- 研究／ファクター計算（DuckDB を使ったファクター計算）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定）
- モニタリング用ダッシュボード（Streamlit）および簡易ツール（Paper Trading 検証レポート）

設計方針としては、「外向き API への最小限の依存」「テストしやすい純粋関数」「フェイルセーフ（API 失敗時は安全側のフォールバック）」を重視しています。

---

## 主な機能
- SystemMonitor: CPU/MEM/Disk、Execution PID の存在確認、データ鮮度チェック、監視ログの永続化
- TradeMonitor: 滞留注文チェック、約定異常（価格乖離）検出
- RiskMonitor: ドローダウン監視、ポジション数監視、リスクログ記録
- KillSwitch: 条件に応じて data/kill.flag を書いて ExecutionEngine を停止させる仕組み
- MonitoringEngine: 上記 Monitor を束ねてポーリング実行、AlertManager 経由で LINE に通知
- ExecutionEngine 起動スクリプト: Broker クライアント生成、OrderManager / RiskManager / Reconciler の組立て
- Reconciler: 再起動時の注文・ポジション同期（ブローカー照合）
- Portfolio モジュール: 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- Research: DuckDB を用いたファクター計算・IC 計算・将来リターン計算
- AI: OpenAI を使ったニュースセンチメント（ai_scores への書き込み）・市場レジーム判定
- Streamlit ダッシュボード: monitoring.db を参照する監視 UI
- tools.paper_verification_report: Paper Trading DB を集計し検証レポートを出力

---

## 前提 / 依存関係
推奨 Python バージョン: 3.9+（コードは型アノテーション等を利用）

主な Python パッケージ（抜粋）:
- duckdb
- psutil
- requests
- streamlit (ダッシュボード利用時)
- openai（AI 機能利用時）
- sqlite3（標準ライブラリ）
- その他: logging, argparse, threading, datetime 等標準ライブラリ

※ requirements.txt は同梱されていないため、上記パッケージを個別にインストールしてください。

---

## セットアップ手順（ローカルでの例）
1. 仮想環境を作る（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil requests streamlit openai

3. プロジェクトルートに `data/` ディレクトリを準備
   - mkdir -p data

4. 環境変数の用意
   - プロジェクトルートに .env を置くか、OS 環境変数を設定します。
   - 自動ロードの仕様: .env （→ .env.local）をプロジェクトルートから自動読み込み（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須変数の一部は Settings クラスが参照します（下記参照）。

5. データベース等は初回起動時に自動でテーブル作成・マイグレーションが走ります（monitoring 用は init_monitoring_db）。

---

## 主要な環境変数（抜粋）
- KABUSYS_ENV: 開発環境を指定（development | paper_trading | live）。デフォルト: development
  - paper_trading では MockBrokerClient を使い、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（Settings.jquants_refresh_token は必須）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 関連機能を使う場合必須）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）、デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db） — Monitoring は環境に関わらず本番 sqlite_path を使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: data/kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

ログレベル:
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（Settings.log_level）

---

## 実行方法（使い方）

基本的にモジュールを -m で実行できます（プロジェクトルートから）。

1) 監視ループ（SystemMonitor を継続実行）
- 目的: システム状態を定期ログに残し、必要に応じてリスクイベント / kill.flag を発行
- 実行:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
- 停止方法:
  - data/stop_requested.flag を作成するとループが検知して終了します
  - また KeyboardInterrupt（Ctrl+C）で終了

注意: Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（"data/monitoring.db"）を使用して監視ログを記録します。

2) 実行エンジン（ExecutionEngine）
- 目的: ブローカー経由での注文処理を行うエンジンを起動
- 実行:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が既に存在すると起動をスキップ
  - 停止は外部から data/stop_requested.flag を作成することで検知して停止
- PID:
  - 実行時は data/execution.pid に PID を書き込む挙動（Settings.pid_file_path）

3) Streamlit ダッシュボード（監視 UI）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - monitoring.db を読み取り専用で開き、Dashboard / Positions / Orders / System 情報を表示

4) Paper Trading 検証レポート（CLI）
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD（開始日）
    - --to YYYY-MM-DD（終了日）
    - --db PATH（デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）
- 出力:
  - 稼働率・注文成功率・送信率・レイテンシ（P95）などの集計と PASS/FAIL 判定を標準出力に出す

5) AI 関連（ニュース NLP / レジーム判定）
- 関数:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続（duckdb.DuckDBPyConnection）を渡して利用。OPENAI_API_KEY 環境変数、または api_key 引数で指定。
    - raw_news / news_symbols / ai_scores テーブルを参照・更新
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを計算して market_regime テーブルに書き込み
- 注意:
  - API キーが無いと例外を投げる（関数側でチェック）
  - OpenAI API 呼び出しはリトライ/フォールバック実装あり（エラー時は安全側のデフォルト値で継続）
  - 呼び出す場合は DuckDB 接続を準備し、target_date を明示的に渡す（ルックアヘッド防止のため date.today() を内部参照しない設計）

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 配下の主なファイル・モジュール（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理（.env 自動ロード機能含む）
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - data/                           — （実行時に利用）data/kabusys.duckdb, monitoring.db, paper_trading.db 等
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite テーブル初期化・永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (エンジン本体は一部ファイルに分かれている想定)
    - broker_factory.py
    - broker_api.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - process_priority.py

（上記はリポジトリ内の主要ファイルを抜粋した構成です）

---

## 補足・注意点
- DB ファイルの分離
  - paper_trading 環境では paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 monitoring.db と完全に分離します。
  - Monitoring のログは常に Settings.sqlite_path（デフォルト data/monitoring.db）に書き込みます（KABUSYS_ENV に依存しない）。
- フラグファイル
  - 停止リクエスト: data/stop_requested.flag（run_* スクリプトが監視している）
  - kill.flag: KillSwitch が書き込むことで ExecutionEngine 停止を促す（Settings.kill_flag_path）
- 初期化 / マイグレーション
  - init_monitoring_db() が呼ばれるとテーブル作成・カラム追加（簡易マイグレーション）を行います。初回起動時に必要なテーブルが作成されます。
- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼び、可能であればプロセス優先度を上げます（psutil を使用）。失敗時は警告を出して続行します。
- ロギング
  - 各スクリプトは logging.basicConfig(level=logging.INFO) を設定しています。詳細に調査したい場合は LOG_LEVEL を DEBUG に設定してください。
- セキュリティ
  - API キーやパスワード等は .env に置くか OS 環境変数で管理してください。Settings._require は未設定時にエラーを出します。

---

必要であれば README に下記の追加情報も追記できます：
- 開発用のデータ初期化スクリプト（DuckDB / SQLite にサンプルデータを入れる手順）
- 各モジュール（ExecutionEngine, OrderRepository 等）の詳細な API/仕様ドキュメント
- 具体的な .env.example のテンプレート

ご要望があれば、.env.example のテンプレート作成や起動スクリプトの systemd ユニット例、CI 用のテストコマンドなども作成します。