# KabuSys

軽量な日本株自動売買システムのコアライブラリ群および運用用ツール群です。  
本リポジトリは取引実行、監視、研究用ファクター計算、AI を使ったニューススコアリング、ポートフォリオ構築などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の関心ごとに分かれたコンポーネント群を提供します。

- Execution（発注エンジン）
  - ブローカークライアント抽象化、OrderManager、ExecutionEngine、起動時のリコンシリエーション等。
  - `run_execution.py` から実行。
- Monitoring（監視）
  - システム状態・注文状態・リスクルールの定期チェック、アラート送信、kill flag 発動等。
  - 監視ログは SQLite（デフォルト: `data/monitoring.db`）に永続化。
  - `run_monitoring.py` から実行。Streamlit ダッシュボードを同梱。
- Research（研究）
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）や特徴量解析ユーティリティ。
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み付け、セクター上限、ポジションサイズ算出など純関数群。
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメント化、マクロセンチメント評価。
- Tools
  - Paper Trading の検証レポート生成スクリプト等。

設計上のポイント:
- 環境依存設定は `kabusys.config.Settings` を通じて一元管理。
- DuckDB を研究用 DB に、SQLite を監視・発注ログに使用。
- Paper trading（`KABUSYS_ENV=paper_trading`）は実稼働 DB と完全分離されるよう設計。

---

## 主な機能一覧

- Execution
  - ブローカー抽象化（実環境・モックの切替）
  - 注文状態管理（OrderManager）
  - 起動時のリコンシリエーション（Reconciler）
  - リスク管理・注文レポジトリ連携
- Monitoring
  - CPU / メモリ / ディスク使用率の定期ログ化
  - Execution プロセス監視（PID ファイル）
  - 注文滞留チェック・約定価格異常検出
  - ドローダウン・ポジション上限のアラートと kill.flag 発行
  - LINE 通知送信（AlertManager）
  - Streamlit ダッシュボード（監視 UI）
- Research
  - モメンタム / ボラティリティ / バリューのファクター計算（DuckDB ベース）
  - 将来リターン・IC 計算・統計サマリ
- Portfolio
  - 候補選定（スコア順、上位 N）
  - 重み計算（等分配 / スコア比率）
  - セクターキャップ適用、レジーム乗数
  - 株数算出（リスクベース / ウェイトベース）、単元丸め、aggregate cap 調整
- AI
  - ニュース記事の銘柄毎センチメント（OpenAI API 経由）
  - マクロ記事を用いた市場レジーム判定（ma200 とマクロセンチメントの合成）
- Tools
  - Paper Trading 検証レポート生成（CSV/標準出力）
  - Streamlit ベースの監視ダッシュボード

---

## セットアップ手順（開発 / 実行環境）

※ OS や Python バージョンは開発環境に合わせてください。ここでは一般的な手順を示します。

1. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 必要パッケージ（抜粋）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用してください）

3. プロジェクトルートに .env を置く（任意）
   - 本リポジトリは自動的にプロジェクトルート（.git または pyproject.toml がある階層）から `.env`/.env.local を読み込みます（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=
     - KABU_API_PASSWORD=
     - OPENAI_API_KEY=
     - KABUSYS_ENV=development | paper_trading | live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - KILL_FLAG_CLEAR_ON_START=0|1
     - LOG_LEVEL=INFO|DEBUG|...
     - LINE_CHANNEL_ACCESS_TOKEN=（任意）
     - LINE_USER_ID=（任意）

4. データディレクトリの作成
   - mkdir -p data

5. Paper Trading を使う場合
   - 環境変数 KABUSYS_ENV=paper_trading を設定してください。
   - Paper trading は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）にデータを記録し、本番の monitoring DB とは分離されます。

---

## 使い方（起動コマンド・主要スクリプト）

- ExecutionEngine（実行エンジン）を起動
  - python -m kabusys.run_execution
  - 動作モードは `KABUSYS_ENV` で制御:
    - paper_trading → MockBroker を使用して paper DB に書き込む
    - live / development → 実ブローカー/設定に依存

- Monitoring（監視）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可。デフォルト 60 秒。
  - 監視は常に本番用の `sqlite_path` を使用して監視ログを残します（監視 DB は環境に依らず production path を参照）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only モードで開いて表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）

- AI 関連（ニュース NLP / レジーム判定）
  - プログラムから `kabusys.ai.score_news(conn, target_date, api_key=None)` を呼ぶ。
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)` でレジーム算出。
  - API キーは引数または環境変数 `OPENAI_API_KEY` を使用。

注意点:
- 実行前に必要な環境変数が未設定だと起動時に例外を投げるプロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）があります。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると、ExecutionEngine 起動時に既存の kill.flag を自動で削除できます（クリーンアップ）。

---

## 主な設定（重要な環境変数）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視ログ用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH: プロセス管理用ファイルパス
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE アラート送信用

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・モジュール構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                            — 環境変数/設定管理
    - run_execution.py                     — ExecutionEngine 起動スクリプト
    - run_monitoring.py                    — SystemMonitor ポーリング起動スクリプト
    - utils/
      - __init__.py
      - process_priority.py                — プロセス優先度 / CPU affinity ユーティリティ
    - monitoring/
      - __init__.py
      - monitoring_db.py                   — monitoring SQLite テーブル定義 + 永続化API
      - system_monitor.py                  — システム状態・データ鮮度監視
      - trade_monitor.py                   — 注文滞留・約定異常監視
      - risk_monitor.py                    — ドローダウン・ポジション上限監視
      - kill_switch.py                     — kill.flag の管理
      - alert_manager.py                   — LINE 通知ラッパー
      - monitoring_engine.py               — 各 Monitor を束ねるエンジン
      - streamlit_dashboard.py             — Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - reconciler.py
      - order_repository.py
      - order_record.py
      - broker_factory.py
      - execution_engine.py
      - ... (他関連モジュール)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py                         — ニュースセンチメント生成（OpenAI 呼び出し）
      - regime_detector.py                  — 市場レジーム判定（MA200 + マクロセンチメント）
    - tools/
      - __init__.py
      - paper_verification_report.py        — Paper Trading 検証レポート生成スクリプト

---

## 運用上の注意 / 実装メモ

- データ鮮度チェックは DuckDB の prices_daily テーブルに依存します。DuckDB のデータ更新を忘れないでください。
- 監視は監視用 SQLite（monitoring.db）にログを書きます。複数プロセスが同一ファイルを操作する場合はファイルロックに注意してください（SQLite の制約）。
- Process 優先度設定（psutil）や CPU affinity 設定は権限によって失敗することがあります。失敗時は警告ログを出してスキップします。
- OpenAI API を使う機能は API の利用制限や応答形式に依存します。大量のリクエストを行う場合はレート制限やリトライロジックを確認してください（実装済みのバックオフあり）。
- Paper trading は実 DB と完全分離するよう設計されています。検証時に本番資産に影響を与えないよう注意して下さい。

---

## よく使うコマンドまとめ

- Execution 起動（Paper / Live は KABUSYS_ENV に依存）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

---

もし README に追加したいサンプル .env.example、依存関係の固定（requirements.txt）やデプロイ手順（systemd ユニット、Dockerfile など）があれば、続けてそれらのテンプレートも作成します。必要なら教えてください。