# KabuSys

日本株向け自動売買プラットフォームの一部（ライブラリ／運用用コンポーネント群）。

このリポジトリはトレード実行、監視、ポートフォリオ構築、ファクターリサーチ、AI を用いたニュース分析などの機能を含むモジュール群を提供します。

---

## プロジェクト概要

- 実行エンジン（ExecutionEngine）による注文発行・管理、リコンシリエーション機能
- 監視機能（SystemMonitor / TradeMonitor / RiskMonitor）とアラート送信（LINE）
- モニタリング DB（SQLite）によるログ保持・ダッシュボード表示（Streamlit）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- リサーチ（ファクター計算、特徴量探索、IC 計算等） — DuckDB を利用
- AI モジュール：ニュースの NLP スコアリング（OpenAI） / 市場レジーム判定
- 実運用向けのユーティリティ（プロセス優先度設定、.env ロード等）

主要な起動スクリプト:
- 実行エンジン: python -m kabusys.run_execution
- 監視ループ: python -m kabusys.run_monitoring
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- Streamlit ダッシュボード: streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 機能一覧

- Execution
  - Broker 抽象化・Factory（本番 / Paper Trading 切替）
  - OrderManager（注文状態管理）
  - Reconciler（再起動時の自動同期）
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / 実行プロセス監視、データ鮮度チェック
  - TradeMonitor：滞留注文・約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限検出、ダッシュボード更新
  - KillSwitch：条件を満たすと data/kill.flag を書き実行エンジンを停止
  - AlertManager：LINE への通知（クールダウン管理）
  - MonitoringDB：SQLite に監視ログを永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - Streamlit ベースの監視ダッシュボード
- Portfolio
  - 候補選定（score / rank）
  - 重み計算（等配分 / スコア加重）
  - セクター集中制限、レジーム乗数
  - ポジションサイズ計算（単元丸め・リスクベース算出・アグリゲート制限）
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン / IC / 統計サマリー
- AI
  - news_nlp.score_news(): raw_news を OpenAI に投げて銘柄別スコアを ai_scores テーブルへ書き込み
  - regime_detector.score_regime(): ma200 とマクロニュースを合成して market_regime に書き込み
  - 両者は OpenAI API キー（OPENAI_API_KEY）を必要とする
- Utilities
  - 環境変数読み込み（.env / .env.local、自動ロードを環境変数で無効化可能）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Paper Trading 向けの report 生成スクリプト

---

## セットアップ手順

1. Python (推奨: 3.10+) をインストールし、仮想環境を作成・有効化してください。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Linux/macOS)
     - .venv\Scripts\activate     (Windows)

2. 依存パッケージをインストールしてください（requirements.txt がない場合は各自で必要なパッケージを追加）。
   - 主に必要なパッケージ（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

3. プロジェクトルートに .env（または .env.local）を用意して設定を追加します。
   - 自動読み込み: デフォルトで .env → .env.local の順に読み込みます（OS 環境変数を上書きしない）。読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 必須環境変数（実行に必要なもの）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
   - KABU_API_PASSWORD — kabuステーション API パスワード
   - もし AI 機能を使用する場合: OPENAI_API_KEY
   - 任意（通知や実行時設定）:
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE）用
     - KABUSYS_ENV — {development, paper_trading, live}（デフォルト: development）
     - LOG_LEVEL — ログレベル（例: INFO）
     - PAPER_FILL_MODE — paper_trading の約定挙動（instant / partial / never / reject）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用の DB（デフォルト: data/paper_trading.db）
     - SQLITE_PATH, DUCKDB_PATH — データベースのパス（デフォルトを使用する場合は作成済みフォルダ data/ が必要）

5. データディレクトリ
   - data/ フォルダを作成してください（PID / flag / DB のデフォルトパスがここを参照します）。
     - mkdir -p data

注意: 実際の運用では Broker クライアント設定や API エンドポイントの設定（KABU_API_BASE_URL など）も必要です。

---

## 使い方

- 監視ループを起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒指定（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使います（KABUSYS_ENV に依存しません）
  - 起動時にプロセス優先度を "high" に設定します（可能な範囲で）

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合:
    - Broker は MockBrokerClient（実注文は行わない）
    - DB は data/paper_trading.db（本番 DB と完全分離）
  - エンジンは data/execution.pid を使って稼働チェック、stop は data/stop_requested.flag を作成することで行います

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB が読み込み可能（read-only）であることを期待します

- AI 機能
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY（または api_key 引数）を必須とします
  - OpenAI 呼び出しはリトライ・バックオフを備え、失敗時は安全側（フォールバック）処理を行います

- 環境変数読み込みの挙動
  - プロジェクトルート（.git または pyproject.toml がある場所）を基準に .env/.env.local を自動ロードします（OS 環境変数を保護）。
  - 自動ロードを止める場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 主要な環境変数（抜粋・例）

- KABUSYS_ENV=development|paper_trading|live (default: development)
- JQUANTS_REFRESH_TOKEN=<token>
- KABU_API_PASSWORD=<password>
- OPENAI_API_KEY=<key>  (AI 機能利用時に必須)
- LINE_CHANNEL_ACCESS_TOKEN= (通知に使う; 任意)
- LINE_USER_ID= (通知先ユーザー; 任意)
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- MONITOR_POLL_INTERVAL=60 (run_monitoring のポーリング間隔)
- PAPER_FILL_MODE=instant|partial|never|reject (paper_trading の約定動作)

例 .env（最低限の雛形）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- KABUSYS_ENV=development
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - 環境変数/設定の読み込み・検証（Settings クラス）
- run_monitoring.py
  - SystemMonitor を使ったポーリングループ起動（MONITOR_POLL_INTERVAL で間隔設定）
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 時は専用 DB / MockBroker）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py — SQLite による監視用永続化層（init + MonitoringDB クラス）
  - system_monitor.py — CPU / メモリ / データ鮮度 / プロセス監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — 停止フラグ操作（kill.flag）
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 監視コンポーネントを束ねる実行ループ
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py — 注文の作成・同期管理
  - reconciler.py — 再起動時自動復旧ロジック
  - （その他 broker 関連、order_repository 等：実運用の中核）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 発注株数計算・丸め・アグリゲート制限
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — ファクター計算（Momentum, Volatility, Value）
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — レジーム判定（ma200 + マクロニュース）
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成

---

## 運用上の注意 / 備考

- 本番稼働時は KABUSYS_ENV を適切に設定（live）し、DB や PID / flag の配置や権限管理に注意してください。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離され、検証に使いやすい設定を採用しています。
- OpenAI 等外部 API を使う機能は API キーの管理とコストに注意してください。失敗時はフェイルセーフ動作（スコア 0.0 など）を行いますが、想定外の負荷がかからないよう運用設計を行ってください。
- SQLite / DuckDB のファイルパスは Settings でカスタマイズ可能です。複数プロセスから同一ファイルに書き込む構成は設計上の注意が必要です（monitoring は本番 DB の使用を前提としている箇所があります）。

---

必要であれば、README にサンプル .env.example、システム構成図、運用手順（起動／停止フロー）、よくあるエラーと対処法などを追記できます。追加の要望があれば教えてください。