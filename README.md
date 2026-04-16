# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株の自動売買・リサーチ・監視機能を備えた小規模なシステムです。  
以下はコードベース（src/kabusys 以下）を前提とした概要、セットアップ、使い方、ディレクトリ構成の説明です。

注意: 実際にブローカーへ注文を出す機能や外部 API（OpenAI / kabuステーション / J-Quants 等）を利用する部分が含まれます。実運用する場合は十分なテストと安全対策（紙トレード→実運用の段階的移行、APIキー管理、バックアップ等）を行ってください。

## プロジェクト概要
- 日本株向けの自動売買フレームワーク（注文管理、リコンシリエーション、ポートフォリオ構築、ポジションサイジング）。
- データ処理・ファクター計算は DuckDB を使用してオンメモリ／ローカルで実行。
- 監視（System / Trade / Risk）機能と監視データの永続化（SQLite）。
- Paper Trading（テスト用の専用 SQLite DB）をサポート。KABUSYS_ENV による動作モード切替。
- OpenAI（gpt-4o-mini 等）を用いたニュースNLP、レジーム検出モジュールを含む（APIキー必須）。
- Streamlit ベースの監視ダッシュボード、Paper Trading 検証レポート生成ツールなど運用支援スクリプトを提供。

## 主な機能一覧
- execution
  - 注文作成・送信、Order State Machine（OrderManager / OrderRepository）
  - 再起動時の自動リコンシリエーション（Reconciler）
  - RiskManager によるレートリミット・ポートフォリオ制約チェック（設定式）
- portfolio
  - 候補選定、等重・スコア重み、リスク調整（セクターキャップ、レジーム乗数）
  - 銘柄ごとの発注株数算出（単元株丸め、aggregate cap）
- research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- ai
  - ニュース記事から銘柄単位のセンチメントスコア算出（OpenAI）
  - マクロニュース＋ETF MA200 乖離を用いた市場レジーム判定
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor による定期チェック
  - MonitoringDB（SQLite）への永続化（system_status / trade_logs / risk_logs / positions / dashboard）
  - KillSwitch（条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナル）
  - AlertManager（LINE Push を用いた一方向アラート送信）
  - Streamlit ダッシュボード（監視データの可視化）
- tools
  - paper_verification_report：Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）

## 必須（想定）環境
- Python 3.10+
  - 型注釈に union (A | B) を使用しているため 3.10 以上が推奨されます。
- パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
  - （標準ライブラリ: sqlite3 等）
- OS: Linux / macOS / Windows（大部分はクロスプラットフォーム。ただし process priority / cpu affinity の挙動は OS に依存）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install duckdb psutil requests openai streamlit
```
※ requirements.txt がある場合はそれを使ってください。

## 環境変数と設定の読み込み
- 設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動的に読み込まれます（自動読み込みはデフォルト有効）。
- 自動読み込みを無効にする場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- 主要な環境変数（例）
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - OPENAI_API_KEY
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - PAPER_FILL_MODE: instant | partial | never | reject  （paper_trading 用）
  - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL, 等
- Settings クラス（kabusys.config.Settings）が環境変数の検証・デフォルトを提供します。

## セットアップ手順（ローカル開発用）
1. リポジトリをクローンし、作業ディレクトリをプロジェクトルート（pyproject.toml または .git のある場所）に揃える。
2. Python 仮想環境を作成して有効化。
3. 依存ライブラリをインストール（上記参照）。
4. 必要な環境変数を `.env` または `.env.local` に設定（例は下記）。
5. DB ディレクトリを作成（デフォルトでは data/*.db）。
   ```bash
   mkdir -p data
   ```
6. DuckDB / SQLite のスキーマはコード実行時に自動作成・マイグレーションが行われます（例: monitoring_db.init_monitoring_db）。

例 .env 最小例:
```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
JQUANTS_REFRESH_TOKEN=...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

## 使い方（主要スクリプト・モジュール）
基本的にパッケージを import して利用する想定です。リポジトリ直下で `PYTHONPATH=src` を設定するか、パッケージをインストールしてください。

例: 開発環境で直接実行する場合
```bash
# カレントディレクトリをプロジェクトルートにして:
export PYTHONPATH=src

# 監視ループを開始（MONITOR_POLL_INTERVAL を指定可能）
MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

# ExecutionEngine を起動（paper_trading で実行する場合）
KABUSYS_ENV=paper_trading python -m kabusys.run_execution

# paper trading レポート
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# streamlit ダッシュボード（read-only で monitoring DB を開く）
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

重要な挙動:
- run_monitoring:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を参照（KABUSYS_ENV に依存せず）。
  - stop フラグファイル: data/stop_requested.flag を置くことでループを終了させる。
- run_execution:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に保存（本番 DB と分離）。
  - data/execution.pid に PID を書き、data/stop_requested.flag / data/kill.flag により停止・強制停止が可能。
- KillSwitch:
  - RiskMonitor 等の評価で条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine に停止シグナルを送る設計。
- AI モジュール:
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を利用。実行には OPENAI_API_KEY が必要。
  - API 呼び出しはリトライ・バックオフやレスポンス検証を組み込んだ堅牢な実装。
- MonitoringDB:
  - 初回起動時に必要テーブルを作成（冪等）。既存 DB に対する簡易マイグレーション（カラム追加）機能あり。

## 便利なツール
- paper_verification_report
  - Paper Trading の監視ログ（data/paper_trading.db）から運用指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を算出し、Pass/Fail を判定します。
  - CLI オプション: --from --to --db
- streamlit_dashboard
  - 監視 DB を読み取り専用で可視化。MonitoringEngine 実行中の確認用。

## ディレクトリ構成（主要ファイル・モジュール）
（src/kabusys をルートとする）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 読み込みと Settings クラス
  - run_monitoring.py — SystemMonitor の polling loop 起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - utils/
    - __init__.py
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py — MonitoringDB（SQLite テーブル定義・永続化 API）
    - system_monitor.py — CPU/メモリ/DISK/データ鮮度 / 実行プロセス監視
    - trade_monitor.py — 注文滞留・約定異常価格検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 操作
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注 API の外向け API
    - reconciler.py — 再起動時リコンシリエーション
    -（その他 ブローカー抽象や execution engine 実装等がある想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計ユーティリティ
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロ NLP）
  - data/ (実行時に利用することが多い)
    - monitoring.db (SQLite)（デフォルト）
    - paper_trading.db (Paper Trading 用 SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid / kill.flag / stop_requested.flag など制御用ファイル

## 運用上の注意事項
- 実行中にプロセス優先度を "high" に変更しようとします（set_process_priority）。OS 権限により失敗する場合がありますが、その場合は警告ログが出ます。
- Paper Trading モードと Live モードは DB を分離して運用してください。paper_trading 用の DB は Settings.paper_sqlite_path を参照します。
- kill.flag / stop_requested.flag / execution.pid などの制御ファイルは data ディレクトリに配置されます。ファイルの作成・削除によりプロセスの挙動が変わります。
- OpenAI 等の外部 API を呼ぶ部分は API キーの漏洩に注意し、安全に管理してください（.env を git 管理しない等）。
- DB スキーマやマイグレーションは簡易実装のため、本番環境でのスキーマ変更作業は慎重に。バックアップ推奨。

## 開発者向けヒント
- ソースを直接実行する場合はプロジェクトルートから `export PYTHONPATH=src` を行うとモジュール解決が楽です。
- 単体モジュールは関数単位で import してユニットテストを行えるように設計されています（副作用を極力抑える実装方針）。
- AI 呼び出し部分はネットワーク関連の障害に備えたリトライ処理とレスポンス検証を行っています。テスト時は API 呼び出しをモックしてください（`unittest.mock.patch` 等）。

---

必要であれば、README に入れる具体的な .env.example、systemd のサービス定義（監視 / 実行用）、またはデプロイ手順（Dockerfile / docker-compose）案を作成します。どの追加情報が必要か教えてください。