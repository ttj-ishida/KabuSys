# KabuSys

日本株向け自動売買システムのコードベース（抜粋）に対する README。  
本 README はこのリポジトリ内の主要コンポーネント・起動スクリプト・設定方法・使い方を日本語でまとめたものです。

> 注: 本リポジトリは実運用を想定したコンポーネント群（ExecutionEngine、Monitoring、AI スコアリング、ポートフォリオ構築等）を含みます。実際に資金を投入しての運用前に十分な検証（Paper Trading / テスト）を行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な役割は以下：

- シグナルに基づく発注と注文状態管理（Execution）
- 発注・約定ログ、ダッシュボードの永続化（SQLite / DuckDB）
- 監視（System / Trade / Risk）とアラート（LINE Push）／KillSwitch（停止フラグ）
- Paper Trading 用検証ツール
- 研究用ファクター計算（DuckDB を利用）
- ニュースを LLM（OpenAI）で解析して銘柄別センチメントを算出する AI モジュール
- Streamlit ベースの監視ダッシュボード

設計思想としては、DB/外部 API へのアクセスを明確に分離し、テストしやすい純粋関数群と外向けラッパーを組み合わせています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（起動スクリプト: run_execution.py）
  - OrderManager / OrderRepository / Reconciler（起動時の自動リコンシリエーション）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）で本番 DB と分離
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク・プロセス生存・データ鮮度監視）
  - TradeMonitor（滞留注文 / 約定価格異常検出）
  - RiskMonitor（ドローダウン検出・ポジション上限）
  - MonitoringEngine（これらをまとめてポーリングするループ）
  - AlertManager（LINE Push による通知）
  - KillSwitch（条件を満たしたら data/kill.flag を書き込み ExecutionEngine に停止を促す）
  - 起動スクリプト: run_monitoring.py
  - Streamlit ダッシュボード: src/kabusys/monitoring/streamlit_dashboard.py
- Research / Portfolio
  - ファクター計算（momentum/value/volatility 等）
  - 特徴量探索、IC 計算、統計サマリツール
  - ポートフォリオ構築（候補選定、重み算出）、ポジションサイズ計算（単元株丸め、リスク制限）
- AI
  - news_nlp: raw_news を LLM に投げて銘柄別センチメントを ai_scores に書き込む
  - regime_detector: ETF (1321) の MA200 とマクロニュースの LLM 結果を合成して市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading の検証レポート生成（成功率、稼働率、レイテンシ等）

---

## 前提・依存関係

推奨 Python バージョン: 3.10+（型ヒントの構文等を利用）。

主な Python パッケージ（抜粋）:
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
- (標準ライブラリ: sqlite3, threading, datetime, pathlib, logging など)

requirements.txt はリポジトリにない可能性があるため、必要なパッケージを個別にインストールしてください。

例:
pip install duckdb psutil requests openai streamlit

（実運用ではバージョン固定の requirements.txt を用意することを推奨します）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install duckdb psutil requests openai streamlit

4. データディレクトリの準備
   - data ディレクトリを作成する（DB・フラグファイル等を置く）
     - mkdir -p data

5. 環境変数の設定
   - .env または環境変数で必要な設定を行う（自動ロード機能あり）
   - 自動ロードを無効化したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

代表的な環境変数（主要）:
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- OPENAI_API_KEY — News / Regime の LLM 呼び出しで必要
- KABUSYS_ENV — one of: development, paper_trading, live  (デフォルト: development)
- PAPER_FILL_MODE — paper_trading の執行モード: instant|partial|never|reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト data/paper_trading.db）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager で通知する場合に必要
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など

例（.env の一部）:
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

---

## 使い方（主なスクリプト・コマンド）

- 監視ループを起動（SystemMonitor をポーリングして monitoring DB に書き込む）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）。例: MONITOR_POLL_INTERVAL=30

- Execution エンジンを起動（実際の発注処理を行うエンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading とすると MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します
  - 実行中、data/execution.pid がプロセス ID を保持し、data/stop_requested.flag や data/kill.flag によって停止制御が行われます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 画面から監視データ・ポジション・注文履歴・リスクログ等を確認できます（読み取り専用推奨）

- AI / レジーム判定（プログラムから呼ぶ）
  - kabusys.ai.score_news — ニュースセンチメントを ai_scores テーブルへ反映（OpenAI API キー必須）
  - kabusys.ai.regime_detector.score_regime — レジーム判定を market_regime テーブルへ書き込み
  - これらは programmatic API（関数呼び出し）として利用できます（DuckDB 接続 + target_date + api_key を渡す）

- モニタリング周りの注意
  - run_monitoring は Monitoring 用 DB（Settings.sqlite_path）を使用します。Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path を使用する設計です（ログ一元化）。
  - run_execution は KABUSYS_ENV=paper_trading の場合に専用 paper DB を使用します（本番 DB と分離）。

---

## キルスイッチ / 停止制御

- data/kill.flag — KillSwitch が書き込むファイル。存在すると run_execution は停止判定や起動時に検出できます。
  - KillSwitch は RiskMonitor やその他の条件に応じて書き込みを行う
- data/stop_requested.flag — 外部的に監視／実行ループを終了させたいときにファイルを作成すると、run_monitoring / run_execution が検知して終了処理します
- run_execution は data/execution.pid に PID を書き込みます（開始時の重複検知や stale PID 検出で使用）

---

## 設定・環境変数一覧（主なもの）

- 必須/重要:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- LLM 関連:
  - OPENAI_API_KEY
- DB 関連:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- 実行環境:
  - KABUSYS_ENV (development | paper_trading | live)
  - LOG_LEVEL (DEBUG, INFO, ...)
- Monitoring:
  - MONITOR_POLL_INTERVAL (秒)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（Monitoring の閾値）
- Paper Trading:
  - PAPER_FILL_MODE (instant|partial|never|reject)

Settings クラス（kabusys.config）で多くの値はデフォルトやバリデーションが実装されています。未設定の必須値は Settings が ValueError を投げます。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要ファイル・モジュールは以下のような構成になっています（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / .env の読み込みと Settings
    - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート生成
    - monitoring/
      - __init__.py
      - monitoring_db.py       — SQLite スキーマ定義 / 永続化 API
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - execution/
      - reconciler.py
      - order_manager.py
      - order_repository.py     — (一部ファイルは省略されている可能性あり)
      - execution_engine.py
      - broker_factory.py
      - broker_api.py
      - order_record.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - data/                     — 実行時に生成される想定（DB, flag, pid など）
    - utils/
      - process_priority.py     — psutil を利用したプロセス優先度 / CPU affinity 設定
      - __init__.py

（実際のツリーはリポジトリ内のファイル一覧に従ってください）

---

## 開発・運用に関する注意事項 / トラブルシューティング

- Python のバージョン & 依存関係を固定することを推奨します（requirements.txt / Poetry 等）。
- psutil によるプロセス優先度設定は権限が必要な場合があります。権限エラー時は警告ログを出して無視されます。
- MonitoringDB は起動時に必要なテーブルを作成し、軽微なマイグレーション（カラム追加）を行います。既存の DB による互換性は注意してください。
- OpenAI 呼び出しはレート制限やネットワーク障害に対してリトライロジックを実装していますが、API キーの管理とコストに注意してください。
- run_execution/run_monitoring はフラグファイル（stop_requested.flag）や kill.flag を用いた停止制御を採用しています。自動運用時はこれらファイルの存在・管理に注意してください。
- Paper Trading を行う場合、必ず KABUSYS_ENV=paper_trading を設定して専用 DB に記録することで本番データと分離してください。

---

## 参考コマンド例

- 短時間ポーリングで監視起動（30秒間隔）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading モードでエンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード（監視 DB を参照）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

この README はコードベースの主要点をまとめたものです。実装の詳細や追加のモジュール（broker 実装、ExecutionEngine の詳細ロジック、OrderRepository 等）はソースコード内の docstring / コメントを参照してください。必要であれば、各モジュールごとの詳細なドキュメント（API 仕様、シーケンス図、運用手順）も作成できます。