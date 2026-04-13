# KabuSys

日本株自動売買システムのリポジトリ（モジュール群の抜粋）。  
この README はコードベースから読み取れる設計方針・起動方法・設定方法をまとめたドキュメントです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたシステムで、以下の機能群を持ちます。

- 戦略 / ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 実行層（ブローカー抽象化、注文作成・送信・再同期）
- 監視（プロセス死活監視、注文滞留・約定異常の検出、ドローダウン監視、アラート送信）
- 研究・リサーチ（ファクター計算、将来リターン・IC 計算）
- AI連携（ニュースのセンチメント評価、マクロセンチメントによるレジーム判定）
- 運用ツール（Paper Trading 検証レポート、Streamlit ベースの監視ダッシュボード）

設計方針の特徴：
- DuckDB / SQLite をデータストアに利用し、研究用クエリと運用ログを分離
- Paper Trading と本番 (live) を DB レベルで分離（paper_trading 環境用の SQLite）
- OpenAI API を利用した NLP 機能を実装（フェイルセーフ・リトライ・バリデーションを備える）
- プロセス優先度 / CPU affinity 設定など運用向けユーティリティあり

---

## 主な機能一覧

- portfolio
  - 銘柄選定（score/順位ベース）
  - 等配分 / スコア加重配分
  - セクターキャップ適用、レジームに基づく乗数
  - 発注株数（単元）算出、資金制約に基づくスケーリング
- execution
  - BrokerClientFactory による実ブローカー / モック両対応
  - OrderManager：注文状態遷移の管理、重複防止
  - Reconciler：起動時の注文/ポジション再同期
- monitoring
  - SystemMonitor：CPU/メモリ/ディスク・プロセス死活・データ鮮度監視
  - TradeMonitor：滞留注文 / 約定価格異常検知
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：条件に応じて flag ファイルを書き ExecutionEngine を停止
  - AlertManager：LINE によるプッシュ通知（クールダウンあり）
  - Streamlit ダッシュボード（read-only 接続）
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- ai
  - news_nlp.score_news：ニュース記事を LLM で評価し ai_scores テーブルへ書き込み
  - regime_detector.score_regime：ETF 乖離 + マクロニュースで日次レジーム判定
- tools
  - paper_verification_report：Paper Trading の検証レポート生成（期間指定可）

---

## セットアップ手順（ローカル）

※以下はコードから読み取れる要件に基づく手順例です。実際の requirements.txt がある場合はそちらを参照してください。

1. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （研究で必要なら追加で pandas 等。実際の依存はプロジェクトの requirements.txt を参照）

3. プロジェクトルートに .env ファイル（任意）を配置
   - config.py はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` / `.env.local` を自動読み込みします。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

4. 主要環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN — J-Quants API の refresh token（必須）
   - KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
   - OPENAI_API_KEY — OpenAI を使う場合に必要
   - KABUSYS_ENV — 環境。`development` / `paper_trading` / `live`（デフォルト: development）
   - PAPER_FILL_MODE — Paper Trading の約定モード（instant / partial / never / reject）
   - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH — DuckDB データパス（デフォルト: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
   - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒。デフォルト 60）

5. データディレクトリ作成
   - mkdir -p data

---

## 使い方（起動コマンド例）

- ExecutionEngine（実行層）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録され本番 DB と分離されます。
    - プロセス起動時にプロセス優先度を "high" に設定しようとします（権限がない場合は警告）。

- SystemMonitor（単体の監視ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可。デフォルト 60 秒。
  - 監視は Settings.env に関係なく本番 sqlite_path を使用して監視ログを記録します。

- Streamlit ダッシュボード（ローカルで監視を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - または上記スクリプトをモジュールとして実行可能（必要に応じて DB パスを指定）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD（開始日）
    - --to YYYY-MM-DD（終了日）
    - --db PATH（SQLite DB パス。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI 機能（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニュースセンチメントを ai_scores テーブルへ書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルへレジームを書き込む
  - 両関数とも api_key 引数が None の場合は環境変数 OPENAI_API_KEY を参照

---

## 設定（Settings の挙動）

- 設定は環境変数を参照します。自動で `.env` → `.env.local` を読み込みます（OS 環境変数が優先）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可。
- 主要プロパティ（Settings クラス）:
  - duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path
  - env（development / paper_trading / live）
  - is_paper / is_live / is_dev
  - paper_fill_mode（"instant"|"partial"|"never"|"reject"、不正値は例外）
  - thresholds: cpu/memory/disk（パーセンテージ）

---

## 運用上の注意

- OpenAI API を利用する機能は API キー・コストが発生します。テスト時はモック化して利用してください（コード中で _call_openai_api をパッチ可能）。
- run_monitoring.py は監視ログの DB に常に本番 sqlite_path を使います（KABUSYS_ENV に依存せず）。
- run_execution.py は paper_trading 環境のとき DB を分離します（settings.is_paper を利用）。
- KillSwitch は flag ファイル（デフォルト data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送ります。必要に応じて起動時にフラグをクリアするオプションがあります（Settings.kill_flag_clear_on_start）。
- process priority / CPU affinity の設定は psutil を利用。権限がない場合は警告ログを出してスキップされます。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / .env の読み込みと Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト（本番 / paper_trading 対応）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成（CLI）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 等配分・スコア配分
    - position_sizing.py — 発注株数算出（risk_based 等）
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースを LLM でスコア化して ai_scores へ書き込み
    - regime_detector.py — ETF MA 乖離 + マクロニュースでレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化と DB ラッパー（MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py — 注文滞留 / 約定異常
    - risk_monitor.py — ドローダウン / ポジション上限チェック
    - kill_switch.py — kill.flag の管理
    - alert_manager.py — LINE push API による通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — 注文作成・送信ロジック、状態遷移管理
    - reconciler.py — 再起動時の注文・ポジション再同期
    - （その他 broker_factory / broker_api / order_repository 等が存在する想定）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 例: よく使うコマンドまとめ

- Execution 起動（本番/ペーパー共通）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動（バックグラウンドでの監視）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Streamlit ダッシュボード（監視 DB を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
- AI ニューススコア（プログラム呼び出し例）
  - from kabusys.ai import score_news
    score_news(conn, target_date, api_key="YOUR_KEY")

---

## 参考（環境変数抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai 機能使用時）
- PAPER_FILL_MODE: instant | partial | never | reject
- PAPER_TRADING_SQLITE_PATH: paper trading DB path（default: data/paper_trading.db）
- SQLITE_PATH: monitoring DB path（default: data/monitoring.db）
- DUCKDB_PATH: DuckDB path（default: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）

---

必要であれば、README に実際の requirements.txt、起動スクリプトの systemd ユニット例、または Dockerfile のサンプルを追加できます。どの情報を優先して追記しますか？