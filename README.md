# KabuSys

日本株向け自動売買システムのコアライブラリ（README）。このドキュメントはリポジトリ内の主要スクリプト／モジュールから要点を抜粋してまとめたものです。

- 対象コードパス: src/kabusys/*
- バージョン: __version__ = 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買・検証・監視を目的としたモジュール群です。主な機能は以下の通りです。

- 発注/注文管理（ExecutionEngine、OrderManager、OrderRepository）
- リコンシリエーション（Reconciler）による自動復旧
- リスク管理（RiskManager、RiskMonitor）
- 監視・アラート（MonitoringEngine、SystemMonitor、TradeMonitor、AlertManager）
- Paper Trading 向けの分離された DB と MockBroker
- ポートフォリオ構築（銘柄選定・重み・株数決定）
- 研究用ファクター計算（Momentum / Volatility / Value 等）と特徴量解析
- OpenAI を用いたニュース NLP / レジーム判定（AI モジュール）
- Paper Trading 検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

設計上の特徴：
- DuckDB をデータ分析（履歴価格・財務等）に使用
- 監視ログは SQLite（data/monitoring.db 等）へ永続化
- 環境（本番 / paper_trading / development）に応じて挙動を切替可能
- 実行中プロセスの優先度設定や PID / フラグファイルで外部制御を想定

---

## 機能一覧（抜粋）

- 実行系
  - run_execution.py: ExecutionEngine 起動スクリプト（本番 / Paper Trading 切替）
  - Reconciler：起動時に未解決注文の同期とポジション差分チェック
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL）
  - MonitoringEngine：System / Trade / Risk の統合ポーリングと KillSwitch 判定
  - streamlit_dashboard.py：監視ダッシュボード（streamlit）
  - monitoring_db.py：監視用 SQLite スキーマ初期化 / 永続化 API
- ポートフォリオ構築
  - portfolio_builder.py: 候補選定・重み計算（等重み・スコア重み）
  - position_sizing.py: 発注株数算出（risk_based, equal, score）
  - risk_adjustment.py: セクターキャップ，レジーム乗数
- 研究（research）
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC・統計サマリー
- AI（OpenAI）
  - news_nlp.py: ニュースのセンチメントを LLM で評価して ai_scores に保存
  - regime_detector.py: MA200 とマクロセンチメントを合成して市場レジーム判定
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成
- ユーティリティ
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定
  - config.py: 環境変数 / .env ロードと Settings API

---

## セットアップ手順

前提
- Python 3.10 以上（`typing` の `X | Y` 構文を使用）
- SQLite は標準ライブラリに含まれます

推奨手順（例）
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （実際のプロジェクトでは requirements.txt を用意している場合はそれを使用）

3. 環境変数（.env）を準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必須（実行に必須なもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - あると便利／用途別
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用）
     - OPENAI_API_KEY（AI モジュール用）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB、デフォルト: data/paper_trading.db）
     - PID_FILE_PATH, KILL_FLAG_PATH 等
     - KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
     - PAPER_FILL_MODE（paper_trading のフィルモード: instant|partial|never|reject、デフォルト: instant）

4. data ディレクトリを作る（必要に応じて）
   - mkdir -p data

注意:
- Settings モジュールはプロジェクトルートから `.env` / `.env.local` を自動で探して読み込む実装になっています（.git または pyproject.toml を起点にプロジェクトルートを決定）。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを抑止してください。

---

## 使い方（起動 / 実行例）

基本的にパッケージとしてインポートして使えますが、実行用スクリプトも用意されています。

1) ExecutionEngine を起動（本番 / Paper Trading）
- 本番（環境変数 KABUSYS_ENV=live）
  - KABUSYS_ENV=live python -m kabusys.run_execution
- Paper Trading（MockBroker を使い、別 DB に記録）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - Paper DB は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に書き込まれます。

起動時の挙動:
- プロセス優先度を high に試行設定（psutil を使用、権限が必要な場合は警告でスキップ）
- PID ファイル（data/execution.pid 等）を扱う
- data/stop_requested.flag が存在すると起動を中止
- 停止は stop フラグや kill.flag により外部から指示可能

2) 監視ループを起動
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定（秒、デフォルト 60）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 監視は常に本番の sqlite_path を使用（KABUSYS_ENV にかかわらず本番 DB を参照する設計）
- 監視ループは data/stop_requested.flag を検知すると終了します

3) Streamlit ダッシュボード（監視用）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only モードで SQLite を開きます（存在しない場合や起動前はエラーを表示）

4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
- 指標: 稼働率、注文成功率、送信率、P95 レイテンシ など

5) AI / レジーム判定 / ニューススコア
- OpenAI API キーが必要（環境変数 OPENAI_API_KEY または引数で渡す）
- モジュール関数（ライブラリ利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 実行時は DuckDB の接続（prices_daily / raw_news / news_symbols / ai_scores / market_regime 等）を渡します

---

## 重要な環境変数（Settings より抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信先（AlertManager）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の挙動）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env の自動ロードを無効化

設定の読み込み:
- .env（および .env.local）をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みします。
- OS 環境変数は .env の値に優先します。

---

## 外部制御 / フラグ

- data/stop_requested.flag: 各長時間ループ（実行系/監視系）はこのファイルの存在を監視し、存在時に安全に終了します。
- data/kill.flag: KillSwitch (monitoring/kill_switch.py) が書き込む停止指示ファイル。ExecutionEngine 側で検出されれば停止やクリーンアップに使用。
- data/execution.pid: 実行エンジンが自身の PID を書くために使用（SystemMonitor がプロセスの存否を監視）。

---

## ディレクトリ構成（src/kabusys/ 配下の主要ファイル）

- __init__.py
- config.py — 環境変数/.env 読み込みと Settings クラス
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- ai/
  - news_nlp.py — ニュースを LLM でスコアリング
  - regime_detector.py — レジーム判定と DB 書き込み

- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・永続化 API
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor の統合ポーリング
  - alert_manager.py — LINE へのプッシュ通知
  - kill_switch.py — kill.flag 管理
  - streamlit_dashboard.py — Streamlit ダッシュボード

- execution/
  - order_manager.py — 発注ロジックの外向き API
  - reconciler.py — 起動時リコンシリエーション
  - （その他ブローカ関連・エンジン等 / 一部ファイルは省略）

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数算出・スケール調整
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — ファクター計算（momentum / value / volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリー

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成ツール

- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

データ・実行ファイル（リポジトリルート推奨）
- data/monitoring.db         — 監視ログ（SQLite）
- data/paper_trading.db      — Paper Trading 用の SQLite（環境により分離）
- data/kabusys.duckdb        — DuckDB（価格・財務データなど）
- data/execution.pid         — 実行エンジン PID
- data/kill.flag             — KillSwitch のフラグ
- data/stop_requested.flag   — スクリプト停止用フラグ

---

## 運用上の注意 / ベストプラクティス

- 本番稼働では KABUSYS_ENV=live を使用し、Paper Trading とは DB を分離してください。
- psutil によるプロセス優先度設定は OS と権限によって失敗することがあります（警告ログのみ）。
- OpenAI 使用時は API レート制限やレスポンスの不安定さを考慮してあり、内部でリトライ・フォールバックが実装されていますが、API キー管理には注意してください。
- monitoring は監視 DB を用いるため、run_monitoring を本番で実行して監視ログを貯める運用を推奨します。
- kill.flag / stop_requested.flag により外部から安全に停止できる設計ですが、フラグファイルの操作は慎重に行ってください（誤ったフラグ書き込みで停止する恐れがあります）。
- DuckDB / SQLite に格納されるデータは定期的なバックアップを検討してください。

---

## 参考コマンド（まとめ）

- 仮想環境と依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil requests openai streamlit

- 実行（Paper）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 実行（Live）
  - KABUSYS_ENV=live python -m kabusys.run_execution

- 監視起動
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの主要点をまとめたものです。細かい挙動やパラメータは各モジュールの docstring / ソースコードを参照してください。追加で「セットアップの自動化」「テスト方法」「デプロイ手順」などを含めた詳細 README が必要であれば、その範囲を指定していただければ作成します。