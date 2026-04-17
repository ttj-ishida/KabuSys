# KabuSys — README

このリポジトリは日本株の自動売買システム「KabuSys」のコードベースです。  
本READMEはプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

※ 本ドキュメントはコードベース（src/kabusys 以下）を参照して作成しています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・モニタリング基盤です。  
主な要素は以下です。

- ExecutionEngine（発注・注文管理・リスク管理・再同期）
- Monitoring（システム稼働・注文の滞留・リスク監視・アラート）
- Portfolio Construction（銘柄選定、重み付け、ポジションサイズ計算）
- Research（ファクター計算、特徴量解析）
- AI ユーティリティ（ニュースのセンチメント解析、レジーム判定：OpenAI を利用）
- 各種ツール（Paper Trading の検証レポート生成、Streamlit ダッシュボード等）

設計方針として、DuckDB/SQLite を用いたオフライン分析、OpenAI を用いたテキスト解析、psutil によるシステム計測、LINE API を用いた通知などを組み合わせています。

---

## 機能一覧（抜粋）

- 実運用 / Paper Trading の切り替え（KABUSYS_ENV）
- 発注管理（OrderManager）と注文状態同期（Reconciler）
- リスク管理（RiskManager）・リスクイベント記録
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）
  - CPU/メモリ/ディスク使用率、プロセス死活、データ鮮度チェック
  - 注文滞留・約定価格異常の検出
  - ドローダウンやポジション上限の監視と Kill Switch（kill.flag）発動
- アラート送信（LINE Messaging API 経由）
- Streamlit による監視ダッシュボード
- Portfolio construction（候補選定、等重・スコア重み、セクター制約、ポジションサイズ決定）
- Research：ファクター算出、将来リターン、IC、統計サマリー
- AI：
  - news_nlp: raw_news をまとめて OpenAI に投げ、銘柄別スコアを ai_scores に記録
  - regime_detector: MA200 とマクロニュースの LLM 判定を合成して market_regime を算出
- ユーティリティ：プロセス優先度 / CPU affinity 設定、.env 自動読み込みロジック

---

## セットアップ手順

前提：
- Python 3.10 以上を推奨（型記法に | を使用）
- Git リポジトリをクローンしてプロジェクトルートに移動

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

2. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt があればそれを使用してください）

3. 環境変数
   - プロジェクトルートの `.env` または `.env.local` に必要な設定を記述できます。自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 主要な環境変数（代表例）：
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須の項目例）
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
     - PAPER_FILL_MODE: Paper Trading の約定挙動（instant | partial | never | reject）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

4. データディレクトリの準備
   - data ディレクトリを作成（監視 DB・PID・フラグファイルなどを配置）
     - mkdir -p data

5. DB 初期化
   - run_monitoring / run_execution 実行時に必要テーブルは自動作成されます（init_monitoring_db が呼ばれます）。

---

## 使い方（主要な実行方法）

※ これらはプロジェクトルートで実行することを想定しています。

- 監視ループを開始（Monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト: 60）
  - python -m kabusys.run_monitoring
  - 停止は Ctrl+C、または data/stop_requested.flag を作成するとループが検知して終了します。

- ExecutionEngine（発注エンジン）を起動
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
  - python -m kabusys.run_execution
  - 起動時に data/execution.pid が設定され、停止は data/stop_requested.flag の作成や Kill Switch による kill.flag 生成により行われます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH を利用して DB パスを指定できます。

- Streamlit ダッシュボード（監視用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite を開きダッシュボードを表示します。

- AI 関連（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - ニューススコア付け:
    - Python API: kabusys.ai.score_news(conn, target_date, api_key=...)
    - DuckDB 接続を渡して実行
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - 失敗時は安全側のフォールバック（スコア 0 や処理スキップ）する設計です。

---

## 実行時のフラグ / ファイル

- data/stop_requested.flag
  - run_monitoring / run_execution が存在を検知するとループ停止・エンジン停止します。
- data/kill.flag
  - KillSwitch（監視側）が重大なリスク条件を検出した際に書き込まれるファイル。ExecutionEngine に停止を促します。
- data/execution.pid
  - 実行エンジンの PID を書き込むファイル。SystemMonitor はこの PID ファイルを監視してプロセス死活を判定します。

---

## 注意点・運用メモ

- Paper Trading は production DB と分離されています（settings.is_paper により paper_sqlite_path を使用）。
- モジュールは外部 API 呼び出し（ブローカー API、OpenAI、LINE 等）を含むため、本番運用では認証情報の管理に注意してください。
- .env 自動ロードはプロジェクトルートの検出（.git または pyproject.toml）に依存します。CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が便利です。
- process priority / cpu affinity 設定はプラットフォーム依存で権限不足時はスキップされます（psutil を使用）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下のおおまかな構成と主なファイルの説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数／設定の読み込みと Settings クラス
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - utils/
    - __init__.py
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite スキーマ定義と MonitoringDB ラッパー
    - system_monitor.py — CPU/メモリ/ディスク／データ鮮度／プロセス監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE 通知クライアント
    - monitoring_engine.py — 各 Monitor を束ねるループ実装
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注フローの外向き API
    - reconciler.py — 起動時リコンシリエーション（注文・ポジション照合）
    - （その他：broker_factory, execution_engine, order_repository 等は本コードベース内に存在）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・キャップ適用・丸めロジック
    - risk_adjustment.py — セクターキャップ、レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
    - __init__.py
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込むロジック
    - regime_detector.py — MA200 とマクロニュースの LLM 判定を合成して market_regime に書き込む
  - data/ （実行時に使われるローカルディレクトリ）
    - monitoring.db（デフォルト）などの DB ファイル、PID / flag ファイルが置かれる想定

---

## 例：よく使うコマンド（まとめ）

- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動（Paper Trading モード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

もし README に追加したい内容（例：依存関係の明確なバージョン、詳細な環境変数サンプル、実運用手順、デプロイ手順など）があれば教えてください。必要に応じてテンプレートの .env.example も作成できます。