# KabuSys

日本株自動売買システム（軽量プロトタイプ）。  
このリポジトリには、注文実行エンジン・モニタリング・ポートフォリオ構築・リサーチ・AI ユーティリティなどの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム売買を目的としたモジュール群です。主に以下を提供します。

- 実行エンジン（ExecutionEngine）: ブローカーとのやり取り、注文管理、リスク管理、リコンシリエーション
- 監視（Monitoring）: システム状態・注文滞留・リスクを定期チェックし、ログ保存・アラート送信・kill フラグ出力
- ポートフォリオ構築（Portfolio）: 候補選定、重み計算、ポジションサイズ決定、セクター制限等の純関数群
- リサーチ（Research）: ファクター計算、将来リターン、IC 計算、統計サマリー
- AI モジュール（AI）: ニュースのセンチメント解析（OpenAI 利用）、市場レジーム判定
- ツール群: Paper Trading 検証レポート生成、Streamlit ダッシュボード等

設計方針の一部:
- DB（SQLite / DuckDB）を用いた局所的な永続化
- Paper Trading と本番 DB は分離（環境変数で切替）
- 外部 API 呼び出し（OpenAI 等）は明示的にキーを要求し、失敗時はフォールバック（フェイルセーフ）

---

## 機能一覧

主な機能:

- Execution
  - ブローカークライアント抽象化（実ブローカー / MockBroker）
  - 注文作成・送信・状態同期（OrderManager）
  - 起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
- Monitoring
  - システム状態（CPU/Memory/Disk）とプロセス死活の監視（SystemMonitor）
  - 注文滞留・約定異常の検出（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - アラート送信（LINE push via AlertManager）
  - kill.flag を用いた緊急停止シグナル（KillSwitch）
  - Streamlit による監視ダッシュボード
- Portfolio
  - 候補選別（スコア降順）
  - 等配分 / スコア加重 / リスクベースのポジションサイズ計算
  - セクターキャップとレジーム乗数
- Research
  - Momentum / Volatility / Value のファクター計算（DuckDB 利用）
  - 将来リターン計算・IC（Spearman）・統計サマリー
- AI
  - ニュースを LLM（OpenAI）でセンチメントスコア化して ai_scores に書き込み
  - マクロニュース + ETF MA200 による市場レジーム判定
- Tools
  - Paper Trading の検証レポート生成（期間指定可能）
  - Streamlit ダッシュボードで監視情報を可視化

---

## セットアップ手順

推奨 Python バージョン: 3.9+（duckdb 等の互換性に依存）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd repo

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール  
   （requirements.txt がない場合は主要パッケージを個別にインストール）
   - pip install duckdb psutil requests openai streamlit

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（config.py による自動ロード）
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
   - KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
   - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH — 実行管理用ファイルパス

---

## 使い方

基本的なコマンド例を示します。各スクリプトはモジュール実行可能なエントリポイントを持ちます。

- Execution Engine の起動（本番/テスト切替）
  - 本番（KABUSYS_ENV=live）:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - Paper Trading（MockBroker、Paper DB に記録）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 補足: 起動時に PID ファイルが書かれ、プロセス優先度を高く設定します。

- Monitoring の起動（ポーリングループ）
  - MONITOR_POLL_INTERVAL で秒間隔を上書き可能（デフォルト 60s）。
  - 起動コマンド:
    - python -m kabusys.run_monitoring
  - 例:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

- Streamlit ダッシュボード（監視ビュー）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 引数 `--db` で監視 DB ファイルを変更可能

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - `--db` で DB パス指定可能（デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI 機能（ライブラリ呼び出し）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  # duckdb 接続を渡す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

- キルスイッチ
  - RiskMonitor 等により条件が満たされると `data/kill.flag` が書き込まれます。ExecutionEngine は起動時や定期チェックでこのフラグを検出し停止できます。
  - フラグを手動で削除するには:
    - rm data/kill.flag

- DB 初期化
  - run_execution / run_monitoring 実行時に監視用テーブル群は `init_monitoring_db()` により冪等に作成されます。

---

## 主要な設定（環境変数まとめ）

- KABUSYS_ENV (development | paper_trading | live) — 実行環境
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能）
- PAPER_FILL_MODE (instant | partial | never | reject) — Paper Trading の約定挙動
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH — PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

設定は .env / .env.local に記述しておくことで自動読み込みされます（ただし OS 環境変数が優先され、.env.local は上書きが可能）。

---

## ディレクトリ構成

src/kabusys の主要ファイルと概略:

- src/kabusys/__init__.py
  - パッケージ定義、バージョン

- src/kabusys/config.py
  - 環境変数/.env ローダー、Settings クラス（アプリ設定をプロパティで提供）

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV による Paper/Live 切替）

- src/kabusys/run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- src/kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など
  - 注文フロー・ブローカー抽象化・リコンシリエーション等

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ & 永続化 API
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, alert_manager.py
  - monitoring_engine.py — 各 Monitor を束ねる
  - streamlit_dashboard.py — Streamlit ベースの UI

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック

- src/kabusys/research/
  - factor_research.py, feature_exploration.py — ファクター計算、IC、統計

- src/kabusys/ai/
  - news_nlp.py — ニュースの LLM スコアリング
  - regime_detector.py — 市場レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

- data/
  - data/kabusys.duckdb (DuckDB)
  - data/monitoring.db (監視 SQLite)
  - data/paper_trading.db (Paper Trading SQLite)
  - data/execution.pid, data/kill.flag など（実行時に生成）

---

## 開発・運用ノート / 注意点

- Paper Trading と本番データは明確に分離されています。KABUSYS_ENV=paper_trading 時は paper_sqlite_path が使用されます。
- OpenAI を使う機能は API キーが必須。キー未設定時は該当処理は ValueError を出します（呼び出し側で捕捉可能）。
- config.py はプロジェクトルート（.git か pyproject.toml）から .env 自動ロードを行います。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を推奨。
- DuckDB / SQLite のスキーマはモジュール内で冪等に初期化・マイグレーション処理があります。
- 実行中のプロセス優先度設定や CPU affinity 設定は psutil に依存し、権限不足時は警告ログを出してスキップします。
- LINE アラートは channel access token と user id が未設定の場合ログのみです。過剰な通知抑止のためクールダウンをメモリ内で管理します。
- streamlit ダッシュボードは読み取り専用モードで監視 DB を開くことを推奨します。

---

README に書かれているコマンドや環境変数は、実行環境・運用方針に合わせて適宜カスタマイズしてください。必要に応じて README を拡張しますので、追加で知りたい箇所があれば教えてください。