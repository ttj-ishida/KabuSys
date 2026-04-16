# KabuSys

日本株自動売買システムのコードベース（抜粋）。このREADMEはリポジトリ内の主要モジュールをもとに、導入・起動・使い方を日本語でまとめたものです。

注意: 実行には外部 API キーやデータベースが必要な機能があります。安全のため本番環境での実行前に設定を確認してください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買 / 研究 / モニタリング機能を備えたシステムです。主な役割は以下のとおりです。

- シグナル → 注文発行 → ブローカーとのやり取り（ExecutionEngine）
- 発注・約定ログ・システム状態の永続化（SQLite / DuckDB）
- モニタリング（CPU/メモリ/ディスク・注文滞留・ドローダウン等）とアラート送信（LINE）
- Paper Trading（擬似ブローカー）モードの分離運用
- ファクター計算、特徴量探索などの研究用モジュール（DuckDB利用）
- ニュースを LLM で評価する AI モジュール（OpenAI）

設計上、以下の方針が見られます：
- DuckDB をデータ分析用に使用、SQLite を監視/発注ログに利用
- 本番と paper_trading を明確に分離（別 SQLite）
- LLM 呼び出しはリトライとバリデーションを備えた安全設計
- プロセス優先度 / CPU affinity の簡易ユーティリティを提供

---

## 機能一覧（主要）

- Execution
  - OrderManager / Reconciler による発注・状態同期・起動時リコンシリエーション
  - BrokerClientFactory 経由で実際のブローカー or MockBroker（paper）を利用
  - RiskManager による注文前の制限チェック

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス生存、データ鮮度
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン / ポジション上限監視
  - MonitoringEngine: 各モニタを束ねてポーリング
  - AlertManager: LINE プッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（read-only DB 接続）

- Research / Portfolio
  - factor_research: Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン・IC・統計サマリー
  - portfolio: 候補選択、重み付け、ポジションサイズ計算、セクター制約、レジーム調整

- AI
  - news_nlp: ニュースを LLM でスコアリングして ai_scores へ書き込み
  - regime_detector: ETF + マクロニュースを併せて市場レジーム判定・保存

- ツール
  - paper_verification_report: Paper Trading DB を解析してレポートを標準出力に出力

---

## セットアップ手順

以下は開発 / 実行環境の最小セットアップ例です。

1. Python（推奨: 3.10+）を用意
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（代表的なもの）
   - pip install duckdb psutil requests openai streamlit

   実際のプロジェクトでは requirements.txt を用意してください。上記は主要依存の例です。

4. プロジェクトルートに `data/` フォルダを作成（起動時に PID/フラグ/DB を配置）
   - mkdir -p data

5. 環境変数（.env など）を用意
   - `.env` または `.env.local` に基本的な設定を記載できます（config.py が自動ロードします）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...            # AI 関連機能に必須
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LOG_LEVEL=INFO
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60

   注意: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを抑止できます。

6. DB 初期化
   - Monitoring 用 SQLite は起動スクリプトが自動でテーブルを作成します（init_monitoring_db）。

---

## 使い方

ここでは主要な実行方法（ローカルでの例）を説明します。

### 1) 監視プロセスを起動（Monitoring）
- 目的: SystemMonitor をポーリングして system_status / risk_logs / trade_logs 等を記録する
- 実行:
  - python -m kabusys.run_monitoring
- オプション / 環境:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60 秒。
  - run_monitoring は常に本番（settings.sqlite_path）を参照して monitoring DB に書き込みます（KABUSYS_ENV に依存しない点に注意）。

- 停止:
  - プロジェクトルートの `data/stop_requested.flag` を作成するとループを検知して終了します。
  - または Ctrl+C（KeyboardInterrupt）。

### 2) Execution Engine を起動（注文発行）
- 目的: ExecutionEngine を起動して取引処理を行う
- 実行:
  - python -m kabusys.run_execution
- 振る舞い:
  - KABUSYS_ENV が `paper_trading` のときは MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（既定: data/paper_trading.db）へ記録して本番 DB と完全分離します。
  - 起動時に `data/stop_requested.flag` が既にある場合は起動せず終了します（安全措置）。
  - pid ファイルは `data/execution.pid`（デフォルト）へ書き込みます。

- 停止:
  - プロジェクトルートの `data/stop_requested.flag` を作成するとエンジンに停止シグナルが送られます。
  - Kill switch（自動停止条件）が発動した場合は `data/kill.flag` が書き込まれ、管理者介入を促します。

### 3) Streamlit ダッシュボード（監視確認）
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 読み取り専用で SQLite を開きダッシュボードを表示します。
  - 監視プロセスが作成した DB を参照して KPI を表示します。

### 4) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
    - 環境変数 PAPER_TRADING_SQLITE_PATH を優先して参照します。
- 出力:
  - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等のサマリと PASS/FAIL 判定を標準出力に出します。

### 5) AI モジュール（ニュース NLP / レジーム判定）
- 要件: OPENAI_API_KEY を設定するか、関数に api_key 引数を渡す
- news_nlp.score_news(conn, target_date, api_key=None)
  - raw_news / news_symbols を集約して OpenAI へ送信し ai_scores を更新します。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF (1321) の MA200 乖離 + マクロニュース LLM によるセンチメントを合成して market_regime に保存します。
- 実行やテスト時は API 呼び出し関数がモック可能（ユニットテストを想定した実装）。

---

## 重要なファイル / フラグ

- data/stop_requested.flag
  - run_monitoring / run_execution がループの中でチェックする停止フラグ。存在するとプロセスが自分で終了します。
- data/kill.flag
  - KillSwitch が発動したときに書き込まれるファイル（ExecutionEngine を停止するための管理者向けフラグ）。
- data/execution.pid
  - ExecutionEngine の PID を記録するファイル。SystemMonitor はこのファイルを読み、プロセスの存否を監視します。
- DB
  - monitoring.db（デフォルト: data/monitoring.db）: 監視ログ用 SQLite（system_status / trade_logs / risk_logs / positions / dashboard を含む）
  - paper_trading.db（デフォルト: data/paper_trading.db）: Paper Trading 時専用の SQLite
  - kabusys.duckdb（デフォルト: data/kabusys.duckdb）: prices_daily, raw_financials, raw_news 等を格納する分析用 DB

---

## 設定（Settings）で重要な環境変数一覧

設定は `kabusys.config.Settings` で定義されています。主要項目：

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能に必須)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (アラート送信用)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
  - is_live / is_paper / is_dev 判別に使用
- PAPER_FILL_MODE: instant | partial | never | reject (paper_trading の約定挙動)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- MONITOR_POLL_INTERVAL（run_monitoring で使用） — 環境変数で設定可能

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要なファイル／モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数読み込み / Settings
  - run_monitoring.py              # SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               # ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  # Paper Trading レポートツール
  - ai/
    - news_nlp.py                   # ニュース NLP（OpenAI 連携）
    - regime_detector.py            # 市場レジーム判定（ETF + マクロ）
  - monitoring/
    - monitoring_db.py              # monitoring DB 層（SQLite）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - execution_engine.py (省略箇所あり)
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - order_repository.py
    - ...
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py
  - data/ (実行時に作成される想定)
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - stop_requested.flag
    - kill.flag

---

## 運用上の注意 / ヒント

- Paper Trading と Live DB は明確に分離すること（PAPER_TRADING_SQLITE_PATH を設定）。
- OpenAI 利用機能は API キーが必要。利用料とレート制限に注意すること。
- run_monitoring.py は KABUSYS_ENV に関係なく常に本番 sqlite_path を使用します（設計上の仕様）。
- process priority を High に設定しようとしますが、権限不足で失敗することがあるためログに注意してください。
- kill.flag / stop_requested.flag の取り扱いは慎重に。自動化スクリプトで誤って置かないように。

---

## テスト / 開発

- モジュールは副作用が少ない設計を志向しています（例えば DB 初期化は冪等）。
- AI API 呼び出しは内部でラップされているため、ユニットテスト時は呼び出し関数をモックしてテスト可能です（例: unittest.mock.patch）。
- Streamlit ダッシュボードは DB の読み取り専用 URI を用いることで安全に参照可能。

---

以上がこのコードベースの README です。必要であれば、実行例のコマンドや .env のサンプル、依存関係の exact requirements.txt を作成するテンプレートも作成します。どの情報を追加しますか？