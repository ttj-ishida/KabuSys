# KabuSys

KabuSys は日本株の自動売買／研究／監視を目的とした小規模なシステム群です。本リポジトリには、バックテスト／発注（Execution）、監視（Monitoring）、ファクター計算や特徴量探索（Research）、ニュース NLP / レジーム判定（AI）、ポートフォリオ構築ロジックなどのモジュールが含まれます。

---

## 概要

主なコンポーネントと役割:

- Execution（実取引 / Paper Trading）  
  発注エンジン、ブローカー抽象化、注文管理、リコンシリエーション等を含む。`run_execution.py` が実行エントリポイント。
- Monitoring（監視）  
  システム状態、注文滞留／約定異常、ドローダウン等の監視。ログは SQLite（monitoring.db）へ永続化。`run_monitoring.py` が監視ループ起動スクリプト。
- Research（リサーチ）  
  Momentum / Value / Volatility 等のファクター計算、将来リターン・IC 計算や統計サマリ。
- AI（ニュース NLP / レジーム判定）  
  OpenAI（gpt-4o-mini 等）を用いてニュースのセンチメントを算出し、ai_scores や market_regime に書き込む。
- Portfolio（銘柄選定・配分・株数決定）  
  候補選定、等金額／スコア加重、リスク調整、単元株丸め、投下資金のスケーリング。
- Tools  
  Paper Trading 検証レポート生成スクリプト（`paper_verification_report.py`）や Streamlit ベースの監視ダッシュボード。

---

## 機能一覧

- 発注エンジン起動（本番 / Paper Trading 切替）
  - Paper Trading 時はブローカーのモックを用い DB を分離（`data/paper_trading.db`）
- 監視ループ
  - CPU / メモリ / ディスク / 実行プロセス存在チェック
  - 注文滞留 (stale orders)、約定価格異常の検出
  - ドローダウン・ポジション上限監視と kill flag 生成（自動停止トリガー）
  - LINE への一方向通知（AlertManager）
  - Streamlit ダッシュボードによる可視化（read-only）
- AI 機能
  - ニュース記事をバッチで LLM（OpenAI）に投げて銘柄単位のセンチメントを取得・保存
  - マクロニュース + ETF（1321）MA200乖離の合成による市場レジーム判定
  - 再試行・バックオフやレスポンスのバリデーション実装済み
- リサーチ機能
  - Momentum / Volatility / Value ファクターの DuckDB ベース計算
  - 将来リターン・IC（スピアマン）・統計サマリ
- ポートフォリオ構築関数群
  - 候補選定、等配分・スコア加重、リスクベース発注株数算出（単元丸め・aggregate cap）
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定（Windows / POSIX 対応）
  - .env 自動読み込み機構（プロジェクトルートに基づく）

---

## 動作環境 / 依存

- Python 3.10+（| 演算子や型アノテーションの使用のため）
- 主な Python パッケージ:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
- 標準ライブラリ: sqlite3, logging, datetime, pathlib など

インストール例（仮）:
- 仮想環境を作成してから:
  - pip install duckdb psutil openai requests streamlit

またはリポジトリをパッケージとしてローカルインストール（開発）:
- PYTHONPATH を src に通す、または
- pip install -e . （pyproject.toml があれば）

---

## セットアップ手順

1. リポジトリをクローンし、src を Python path に通す（またはパッケージインストール）
   - export PYTHONPATH=$(pwd)/src など

2. 依存ライブラリをインストール
   - pip install duckdb psutil openai requests streamlit

3. data ディレクトリ作成（必要時）
   - mkdir -p data

4. 環境変数設定（.env を使用可能）
   - 必須（機能により）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI 機能を使う場合:
     - OPENAI_API_KEY
   - 運用環境:
     - KABUSYS_ENV : development | paper_trading | live（デフォルトは development）
   - DB パス（必要に応じて上書き）:
     - SQLITE_PATH (監視、デフォルト: data/monitoring.db)
     - DUCKDB_PATH (DuckDB ファイル、デフォルト: data/kabusys.duckdb)
     - PAPER_TRADING_SQLITE_PATH (Paper Trading 用 SQLite、デフォルト: data/paper_trading.db)
   - その他:
     - MONITOR_POLL_INTERVAL (監視ポーリング間隔秒、デフォルト 60)
     - PAPER_FILL_MODE (paper_trading の約定モード: instant|partial|never|reject)
     - PID_FILE_PATH / KILL_FLAG_PATH / LOG_LEVEL 等
   - .env 自動ロード:
     - プロジェクトルート（.git か pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
     - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 初回起動時の DB 初期化は各スクリプトで行われます（monitoring のテーブルは init_monitoring_db にて冪等に作成）。

---

## 使い方（実行例）

注意: package としてインストールされているか、src が PYTHONPATH に含まれている前提です。

- Execution（発注エンジン）を起動
  - 本番/デフォルト DB を使用:
    - python -m kabusys.run_execution
  - Paper Trading（環境変数で切替）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 停止: 実行中のプロセスに対して data/stop_requested.flag を作ると起動ループが検知して停止します（スクリプト内の停止フラグパス参照）。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30
  - 停止: data/stop_requested.flag を作成して監視ループを止めます。

- Streamlit ダッシュボード（読み取り専用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（スコア付与 / レジーム判定）はプログラム的に呼び出します。例:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

---

## 停止・制御（フラグファイル）

- stop flag（両スクリプトで参照）:
  - data/stop_requested.flag を作成すると監視 / 実行ループが検知して安全に終了します。
- kill flag（KillSwitch）:
  - 監視側の KillSwitch により重大イベント（ドローダウンやポジション上限）検知時に data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送る設計です。
  - Execution 起動時に kill.flag をチェックして起動を回避する運用も可能です。
  - Kill flag は KillSwitch クラスから clear() で削除できます。
- PID ファイル:
  - ExecutionEngine は data/execution.pid 等を PID ファイルに書きます。SystemMonitor はこの PID の存在検査でプロセス死活を判断します。

---

## 環境変数（主要）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能に必須
- SQLITE_PATH: 監視 DB path（default: data/monitoring.db）
- DUCKDB_PATH: DuckDB path（default: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

---

## 開発者向けメモ / トラブルシューティング

- .env の自動読み込みはプロジェクトルート (.git または pyproject.toml) を基準に行われます。テストや CI で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続を渡してファクター計算・AI 処理を行う設計です。prices_daily / raw_financials / raw_news 等のテーブルが期待されます。
- OpenAI 周りはリトライやレスポンスバリデーションを備えていますが、API キー未設定の場合は明示的に ValueError を投げます（呼び出し側で捕捉してください）。
- プロセス優先度設定は psutil を用いて行います。権限不足で設定できない場合は警告を出してスキップします。
- DuckDB の executemany で空リストを渡すとエラーになるバージョンがあるため、実装側で空チェックを入れています。
- Python の型ヒントや構文（PEP 604 の | 型合成）を使用しているため Python 3.10 以上を推奨します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py              — 環境変数 / 設定管理
- run_execution.py       — ExecutionEngine 起動スクリプト
- run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト

パッケージ群:
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - broker_api.py
  - ...（発注関連）
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
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
  - paper_verification_report.py
- utils/
  - process_priority.py

その他:
- data/                  — 実行時に生成される DB / PID / flag 等（data/monitoring.db, data/kabusys.duckdb など）

---

## 参考コマンドまとめ

- 監視起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 発注起動（Paper Trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に含める具体的な環境変数のテンプレート（.env.example）や、systemd / supervisor 用のサービスユニット例、データベース初期ダンプサンプル、API モックの使い方なども作成できます。どれを追加しますか？