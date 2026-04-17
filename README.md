# KabuSys — README

KabuSys は日本株向けの自動売買・リサーチ基盤のモジュール群です。戦略のポートフォリオ構築、ポジションサイジング、発注実行・リコンシリエーション、監視・アラート、Paper Trading 用の検証ツール、LLM を使ったニュースセンチメント解析などを含みます。

---

## プロジェクト概要

- 設計方針
  - DuckDB / SQLite を用いたオフライン集計・永続化（本番データと Paper Trading を分離）
  - モジュールは純粋関数（Portfolio / Risk / PositionSizing 等）と I/O 層（DB / Broker API / OpenAI / LINE）を分離
  - ルックアヘッドバイアス防止のため、日付参照は明示的に与える設計
  - フェイルセーフ重視：外部 API の失敗はデフォルト値にフォールバックし例外でプロセスを止めない

---

## 主な機能一覧

- execution（発注系）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager、OrderRepository、Reconciler：発注・状態同期・再起動時リコンシリエーション
  - BrokerFactory により実運用 / Paper Trading 切替可能（Paper Trading は MockBrokerClient を使用）
  - RiskManager：発注前のリスク制御（最大ポジション比率、利用率、ドローダウン等）

- monitoring（監視系）
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / プロセス死活監視
  - TradeMonitor：滞留注文（stale orders）や約定価格異常監視
  - RiskMonitor：ドローダウン／ポジション上限の監視とアラート記録
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager：LINE Push による通知（cooldown 管理）
  - MonitoringEngine：上記を束ねるポーリングループ
  - streamlit_dashboard.py：監視ダッシュボード（Streamlit）

- portfolio（ポートフォリオ構築）
  - 銘柄選定（スコア降順フィルタ）、等重・スコア重み、セクターキャップ、レジーム乗数、株数決定（lot 単位・リスクベース等）

- research（リサーチ用）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（Information Coefficient）計算、特徴量サマリ

- ai（LLM を利用する機能）
  - news_nlp: raw_news を集約して OpenAI に問い合わせ、銘柄ごとの ai_score を ai_scores テーブルへ書き込む
  - regime_detector: ETF(1321) の MA とマクロニュースを組合せて市場レジーム（bull/neutral/bear）を判定して保存

- tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・約定率・レイテンシ等）

---

## セットアップ手順

1. Python 環境
   - 推奨: Python 3.10+（duckdb / psutil 等の現行パッケージに合わせてください）

2. 依存パッケージ（例）
   - pip install duckdb psutil requests openai streamlit
   - ※ requirements.txt は本リポジトリに含まれていないため、環境に合わせて依存を追加してください。

3. プロジェクトルート（.git または pyproject.toml があるディレクトリ）に配置
   - data/ ディレクトリは自動で作成されますが、事前に作る場合は
     - data/monitoring.db（SQLite、監視ログ）
     - data/paper_trading.db（Paper Trading 用 SQLite）
     - data/kabusys.duckdb（DuckDB 集計用、デフォルト: data/kabusys.duckdb）

4. 環境変数（.env/.env.local）
   - プロジェクトルートの .env（および .env.local）を自動で読み込みます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数とデフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: （必須）
     - KABU_API_PASSWORD: （必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager 用（任意）
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（Paper Trading の DB）
     - SQLITE_PATH: data/monitoring.db（監視 DB）
     - DUCKDB_PATH: data/kabusys.duckdb（DuckDB ファイル）
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、監視スクリプトで使用、デフォルト 60）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）

5. データベース初期化
   - 監視用 DB はスクリプト内で自動的に init します（init_monitoring_db）。特別なマイグレーションは init_monitoring_db が行います。

---

## 使い方（主要スクリプト）

- 監視ループ起動（SystemMonitor 単体）
  - 実行:
    - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL=30 などでポーリング間隔を上書き可能
  - 備考:
    - 監視は常に Settings.sqlite_path（本番 sqlite_path）を使用する設計
    - 停止: data/stop_requested.flag を作成するとループが終了します（stop フラグ）

- Execution エンジン起動（発注エンジン）
  - 実行:
    - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db を使います（本番 DB とは分離）
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します
    - 実行中に data/stop_requested.flag が作成されるとエンジン停止を試みます
  - PID / Kill:
    - 起動時に pid ファイル（デフォルト data/execution.pid）を使って状態管理
    - KillSwitch が data/kill.flag を書き込むと停止シグナルとして機能します

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - --db data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）
  - 出力:
    - 稼働率（uptime）、注文成功率、送信率、P95 レイテンシなどのサマリと PASS/FAIL 判定

- 監視ダッシュボード（Streamlit）
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 機能:
    - Overview / Positions / Orders / System タブで監視情報を閲覧可能（read-only 接続）

- AI 機能（プログラム内 API）
  - ニュースのセンチメントスコア生成:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

  - 注意:
    - OPENAI_API_KEY が設定されていないと例外を投げます（関数は api_key 引数または環境変数を参照）
    - API 呼び出しはリトライとフェイルセーフ（失敗時は中立値で継続）を組み込んでいます

---

## ファイル / ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / Settings 管理、.env 自動ロードロジック
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（Paper Trading 切替含む）

  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite 用永続化層（テーブル作成 / CRUD）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・約定価格異常の検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE Push 通知クライアント
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード

  - execution/
    - order_manager.py — 発注・状態遷移 API
    - order_repository.py, order_record.py, reconciler.py, risk_manager.py, execution_engine.py, broker_factory.py, broker_api.py ...
    - （発注やブローカー通信、リコンシリエーションに関する実装群）

  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 発注株数の計算（ロット丸め・スケール）
    - risk_adjustment.py — セクター上限・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — momentum/volatility/value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
    - __init__.py

  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity のユーティリティ
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
    - __init__.py

- data/ （ランタイムファイル）
  - monitoring.db（デフォルト SQLite）
  - paper_trading.db（Paper Trading 用 SQLite）
  - kabusys.duckdb（DuckDB）
  - execution.pid, stop_requested.flag, kill.flag などの制御ファイル

---

## 運用上の注記 / ヒント

- Paper Trading と本番 DB は分離されています。KABUSYS_ENV=paper_trading を使うと paper_sqlite_path が使用されます。
- .env の読み込み順は OS 環境 > .env.local > .env です。OS 環境変数を上書きしたくない場合は .env/.env.local に注意してください。
- OpenAI など外部 API を使う機能は API キーの取り扱いに注意してください（レート制限・課金に注意）。
- 監視プロセスはデフォルトで MONITOR_POLL_INTERVAL=60 秒です。短くしすぎると負荷・レート問題になる可能性があります。
- streamlit ダッシュボードは DB を読み取り専用で開けるように URI に mode=ro をつけています。監視プロセスが DB を更新しているはずなので通常は read-only で問題ありません。

---

必要であれば README に以下を追記できます：
- コマンド例（systemd ユニット、docker-compose、cron などでの運用例）
- テストの実行方法 / CI 設定
- よくあるトラブルシューティング（kill.flag の対処、PID ファイルが残った場合の手順等）

この README をベースに補足したい項目があれば指示してください（例: systemd のユニット例、Dockerfile、依存パッケージ一覧など）。