# KabuSys — README

日本株自動売買システムのサブセット実装ドキュメント（コードベースから生成）。  
この README はリポジトリ内の主要スクリプト・モジュールの概要、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するモジュール群です。本リポジトリには以下の主要機能が含まれます（実取引用 API 呼び出しや外部データベースとの連携は設定により切り替え可能）:

- ExecutionEngine（発注エンジン）: ブローカーへの発注、注文状態管理、リコンシリエーション機能
- Monitoring（監視）: システム・注文・リスク監視、アラート送信（LINE）、kill flag による安全停止
- Research / Factor 計算: DuckDB 上の価格・財務データを用いたファクター計算・解析
- AI モジュール: ニュースから LLM を用いたセンチメントスコア算出（OpenAI）
- Portfolio 構築: 候補選定、重み計算、ポジションサイズ算出、セクター制約など
- Tools: Paper Trading 検証レポート生成、Streamlit ダッシュボード

設計方針の一例:
- DuckDB を分析用、SQLite を監視ログ／注文ログ用に使用（paper_trading 時は監視 DB を分離）
- 環境変数 / .env による設定管理
- フェイルセーフ（API失敗時のフォールバック、ログ出力による監視等）
- ルックアヘッドバイアス防止（日時参照の扱いに注意）

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB に記録
  - プロセス優先度（high）設定、DB 初期化、リコンシリエーション等を実施

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整（デフォルト 60 秒）
  - 常に本番 sqlite_path を使用して監視ログを記録

- monitoring/*
  - MonitoringDB: SQLite における監視ログ（system_status、trade_logs、positions、risk_logs、dashboard）の作成/操作
  - SystemMonitor: CPU/メモリ/Disk/プロセス・データ鮮度の監視
  - TradeMonitor: 滞留注文、約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard の更新とリスクログ記録
  - KillSwitch: kill.flag の書き込み（ExecutionEngine 停止シグナル）
  - AlertManager: LINE Push による通知（クールダウン管理）
  - MonitoringEngine: 上記モニタを束ねたポーリングループ / 単発実行

- research/*
  - factor_research: モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー

- ai/*
  - news_nlp.score_news: raw_news を OpenAI に送り銘柄ごとのセンチメント（ai_scores）を作成して DuckDB に保存
  - regime_detector.score_regime: ETF(1321) の MA とマクロセンチメントを合成し market_regime を決定して保存

- portfolio/*
  - 候補選定、重み算出、セクターキャップ適用、ポジションサイジング（単元丸め／資金配分制約反映）などの純粋関数

- tools/paper_verification_report.py
  - Paper Trading DB を対象に検証レポートを生成（稼働率、注文成功率、レイテンシ等の判定）

- monitoring/streamlit_dashboard.py
  - Streamlit を使った監視ダッシュボード（read-only で monitoring DB を表示）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 最低限必要なライブラリ（例）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - インストール例:
     - pip install duckdb psutil openai requests streamlit

   ※ 実際の運用では dependency 管理のため requirements.txt / poetry 等を用意してください。

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くことで自動読み込みされます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   代表的な環境変数（主なもの）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須な場合あり）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
   - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の挙動）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
   - LOG_LEVEL（INFO 等）、MONITOR_POLL_INTERVAL（秒）、LINE_CHANNEL_ACCESS_TOKEN、LINE_USER_ID

5. データベース初期化
   - 起動スクリプトが初回実行時に monitoring DB のテーブルを作成します（init_monitoring_db）。
   - DuckDB のテーブル（prices_daily, raw_financials 等）は外部 ETL / インポート処理により準備してください。

---

## 使い方（実行例）

- ExecutionEngine を起動する（通常/本番は環境変数 KABUSYS_ENV を適切に設定）
  - python -m kabusys.run_execution
  - paper_trading モードで起動（専用 DB に記録）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  実行時の動作:
  - プロセス優先度を「high」に設定（可能な場合）
  - SQLite / DuckDB に接続
  - Broker クライアントを生成（paper_trading なら Mock）
  - リコンシリエーションを実行してセッション開始

- Monitoring（SystemMonitor）を起動する
  - python -m kabusys.run_monitoring
  - ポーリング間隔の変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  実行時の動作:
  - プロセス優先度を「high」に設定
  - 監視ログ（system_status 等）を sqlite に永続化
  - PID ファイル確認、kill.flag 書き込み検出／削除など

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュールのプログラム利用例（Python スクリプトから）
  - ニューススコア付け:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")

- 注意点
  - paper_trading モードは「本番 DB と完全分離」されるように設計されています。運用時は環境変数により DB パスを確認してください。
  - OpenAI/ブローカー等の外部 API を使用する機能は API キーやネットワークが必要です。障害時はフェイルセーフ（フォールバック）挙動を取りますが、必ずテスト環境で動作確認してください。

---

## 重要な環境変数（まとめ）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- OPENAI_API_KEY
- SQLITE_PATH (監視 DB) — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- MONITOR_POLL_INTERVAL — 監視ポーリング秒数（run_monitoring）
- PAPER_FILL_MODE — paper_trading の約定挙動
- PID_FILE_PATH, KILL_FLAG_PATH
- LOG_LEVEL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

---

## ディレクトリ構成（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / .env 自動ロード、Settings クラス
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

src/kabusys/ai/
- news_nlp.py — ニュースの LLM センチメント集計・ai_scores 書き込み
- regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）

src/kabusys/monitoring/
- monitoring_db.py — SQLite スキーマ初期化・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py — システム状態・データ鮮度チェック
- trade_monitor.py — 注文滞留・約定異常チェック
- risk_monitor.py — ドローダウン / ポジション上限チェック
- kill_switch.py — kill.flag の管理
- alert_manager.py — LINE 通知（クールダウン対応）
- monitoring_engine.py — 各 Monitor の統合（run / run_once）
- streamlit_dashboard.py — Streamlit ダッシュボード起動スクリプト

src/kabusys/execution/
- reconciler.py — 起動時リコンシリエーション（注文 / ポジション同期）
- order_manager.py — 発注 FSM の上位 API（作成・送信・同期など）
- （他に broker_factory, execution_engine, order_repository 等が存在する想定）

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・等重/スコア重み
- risk_adjustment.py — セクター上限・レジーム乗数
- position_sizing.py — 株数決定、単元丸め、aggregate cap スケーリング
- __init__.py — API エクスポート

src/kabusys/research/
- factor_research.py — momentum/volatility/value ファクター計算（DuckDB）
- feature_exploration.py — 将来リターン・IC・統計サマリ

src/kabusys/utils/
- process_priority.py — プロセス優先度 / CPU affinity 設定ラッパー

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

---

## 監視 DB（SQLite）スキーマ（概要）

init_monitoring_db により作成されるテーブル:
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code PK, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 固定行で集計保存: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

監視 / アラートの多くはこの DB に記録され、Streamlit ダッシュボードや検証レポートが参照します。

---

## 運用上の注意 / ベストプラクティス

- 本番環境では KABUSYS_ENV=live を設定し、設定ファイル・シークレット管理に注意してください。
- paper_trading は本番 DB と分離しているとはいえ、データ整合性の確認は十分に行ってください。
- OpenAI 等の外部 API 呼び出しはレート制限やコストが発生します。API キーの管理・呼び出し頻度に注意してください。
- process priority / cpu affinity の設定は環境によって権限が必要になることがあります（psutil の AccessDenied 例外に注意）。
- kill.flag により ExecutionEngine を安全停止できるため、監視ツールは kill.flag の有無を適切に扱ってください。

---

必要であれば README にサンプル .env.example、requirements.txt、運用手順（systemd ユニット、Dockerfile、コンテナ運用）やユニットテストの実行方法を追加します。どの情報を追加したいか教えてください。