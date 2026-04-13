# KabuSys

日本株自動売買システムのコアモジュール群。ポートフォリオ構築、発注実行、監視、リサーチ、ニュースNLP / レジーム判定などを含むライブラリおよび起動スクリプト群です。

---

## 概要

KabuSys は以下のような機能を持つ自動売買基盤の一部を実装しています。

- データ解析（DuckDB を用いたファクター計算）
- ポートフォリオ構築（候補選定・重み付け・在庫調整）
- 発注フロー管理（OrderManager / ExecutionEngine、ブローカーファクトリ）
- 監視・アラート（プロセス監視、滞留注文チェック、ドローダウン検知、LINE 通知）
- AI 支援（OpenAI を用いたニュースセンチメント評価・市場レジーム判定）
- 開発/検証用ユーティリティ（Paper Trading 用検証レポート、Streamlit ダッシュボード）

設計上のポイント：
- 設定は環境変数または .env / .env.local から読み込まれます（自動ロード機能あり）。
- Paper Trading モード（KABUSYS_ENV=paper_trading）は本番 DB と分離された SQLite を使用します。
- OpenAI を使う機能は API キー入力が必須（環境変数 OPENAI_API_KEY など）。

---

## 主な機能一覧

- portfolio
  - 候補選定（select_candidates）
  - 重み計算（等配分 / スコア加重）
  - ポジションサイズ計算（リスクベース等）
  - セクター制限・レジーム乗数適用
- research
  - モメンタム・ボラティリティ・バリューのファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- execution
  - OrderManager（発注状態遷移管理）
  - Reconciler（再起動時の同期）
  - ExecutionEngine の起動スクリプト（run_execution.py）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor
  - MonitoringDB（SQLite に監視ログを永続化）
  - KillSwitch（フラグファイルで ExecutionEngine 停止）
  - AlertManager（LINE Push を利用した通知）
  - Streamlit ダッシュボード（監視 UI）
  - 起動スクリプト（run_monitoring.py）
- ai
  - news_nlp: ニュースを集約して OpenAI に問い合わせ、銘柄ごとのスコアを ai_scores テーブルへ書き込む
  - regime_detector: ETF MA とマクロニュースを合わせて市場レジーム判定を行う
- tools
  - paper_verification_report: Paper Trading DB（data/paper_trading.db）を集計して検証レポートを出力

---

## 必要要件（例）

- Python 3.10+
- パッケージ（主なもの）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (監視ダッシュボードを使う場合)
- SQLite（Python 標準ライブラリの sqlite3 を使用）

プロジェクトには requirements.txt が付属していない想定のため、上記を pip でインストールしてください。

例:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) / .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
4. データディレクトリ作成（必要に応じて）
   - mkdir -p data
5. .env を作成（参考: .env.example を元に）
   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...         # AI 機能を使う場合に必須
   - KABUSYS_ENV=development|paper_trading|live
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - LOG_LEVEL=INFO
   - LINE_CHANNEL_ACCESS_TOKEN=...  # LINE 通知を使う場合
   - LINE_USER_ID=...

自動読み込み:
- プロジェクトルートに .env / .env.local があれば起動時に自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。

---

## 使い方

主要な起動スクリプト・コマンド例を示します。src ディレクトリにいる前提では、python -m kabusys.<module> で実行できます。

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
    - 監視は常に本番用の sqlite_path を使用（KABUSYS_ENV に依らず）
    - プロセス優先度を "high" に設定しようとします（psutil に依存）

- 実行エンジンを起動（Execution）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、BrokerClientFactory は MockBrokerClient を生成し、paper_sqlite_path を使用して発注データを完全分離します
    - 起動時に ExecutionEngine がブローカーと接続してセッションを実行します

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 補足:
    - --db オプションで読み込む monitoring DB を指定できます（デフォルト data/monitoring.db）
    - 読み取り専用（URI に ?mode=ro が付与されます）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

- AI 関連（ニュース NLP / レジーム判定）
  - kabusys.ai.score_news は内部で OpenAI API を呼ぶ関数です。呼び出しプログラム側で
    OPENAI_API_KEY 環境変数を設定するか、関数引数で api_key を渡してください。
  - kabusys.ai.regime_detector.score_regime も同様に API キーが必要です。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 起動モード（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- SQLITE_PATH: 監視ログ用 SQLite のパス（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグファイル（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用

詳細はコード内の Settings クラス（kabusys.config）を参照してください。

---

## 注意事項 / 実運用メモ

- Paper Trading モードでは発注・証跡が本番 DB から分離されます（必ず PAPER_TRADING_SQLITE_PATH を確認）。
- OpenAI API 呼び出しはレート制限やネットワーク障害を想定してリトライロジックが実装されていますが、API キーと呼び出しコストに注意してください。
- monitoring の kill.flag により ExecutionEngine 停止を行う設計です。KillSwitch は閾値を満たすと data/kill.flag を作成します。起動時に KILL_FLAG_CLEAR_ON_START を使って起動時にクリアする設定を行うことができます。
- Process priority / CPU affinity 設定は psutil を使ってプラットフォーム差分を吸収します。権限不足で設定が失敗する可能性があります（ログに警告）。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル / フォルダ構成を簡単に示します（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env ロードと Settings クラス
  - run_monitoring.py             — Monitoring のポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
    - position_sizing.py           — 株数決定・上限・丸め
    - __init__.py
  - research/
    - factor_research.py           — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py       — 将来リターン・IC・統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py                  — ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py           — 市場レジーム判定（MA + マクロニュース）
    - __init__.py
  - monitoring/
    - monitoring_db.py             — SQLite スキーマ / DB 操作ラッパー
    - system_monitor.py            — CPU/メモリ/ディスク / データ鮮度チェック
    - trade_monitor.py             — 注文滞留・約定異常検知
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - kill_switch.py               — フラグファイルによる停止信号
    - alert_manager.py             — LINE 通知
    - monitoring_engine.py         — 複数 Monitor を束ねるエンジン
    - streamlit_dashboard.py       — Streamlit ベースの監視画面
    - __init__.py
  - utils/
    - process_priority.py          — psutil を使った優先度 / CPU affinity 設定
    - __init__.py
  - execution/
    - order_manager.py             — 発注フローの外向き API（OrderManager）
    - reconciler.py                — 起動時リコンシリエーション
    - ...（ブローカ関連・注文リポジトリ等が存在）
  - monitoring/monitoring_db.py   — 監視用テーブル定義と MonitoringDB クラス

（注）実際のリポジトリには data/ や他の補助モジュール（kabusys.data など）が存在する想定です。

---

## 開発・デバッグのヒント

- 設定の自動ロードはプロジェクトルートを .git または pyproject.toml で検出して行われます。テスト時など明示的に無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のクエリは大きなデータセットを扱うため、クエリログやインデックス等の最適化が必要な場合があります。
- AI 呼び出し部分は外部依存が強いため、ユニットテストでは OpenAI クライアント呼び出しをモックすることを推奨します（コード内にモック用に差し替え可能な関数が用意されています）。

---

README はここまでです。必要であれば次のことを追加できます：
- .env.example のテンプレート（具体的なサンプル）
- requirements.txt の推奨内容
- より詳細な運用手順（デプロイ / サービス化 / systemd ユニット例）