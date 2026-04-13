# KabuSys

日本株自動売買システムの一部（ライブラリ群・モニタリング・ExecutionEngine・研究/AI ツール群）。  
この README はリポジトリに含まれる主要コンポーネントの概要、機能、セットアップ手順、起動方法、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアライブラリ群です。主な責務は次の通りです。

- 実行エンジン（ExecutionEngine）による発注／リスク管理／再同期（Reconciler）
- 監視（Monitoring）: システム状態・注文状態・リスクを定期的にチェックしログ化・アラート送信・キルスイッチを実行
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・リスク調整）
- 研究（Research）: DuckDB 上の株価・財務データを用いたファクター計算・探索
- AI モジュール: ニュースの NLP スコアリング（OpenAI）や市場レジーム判定
- 補助ツール: Paper Trading 検証レポート、Streamlit ダッシュボード 等

設計方針の要点:
- DB（SQLite / DuckDB）をデータ永続化に利用
- Paper Trading は本番 DB と分離（隔離された SQLite）
- ルックアヘッドバイアスを避ける実装（date.today() 等を直接参照しない設計）
- フェイルセーフ: 外部 API（OpenAI 等）失敗時はフォールバックして継続

---

## 機能一覧

- Execution
  - ブローカークライアント抽象化（BrokerClientFactory）
  - OrderManager による発注ワークフロー（作成 → 送信 → 同期）
  - Reconciler による起動時の自動復旧（OrderSent の突合、ポジション差分検出）
  - RiskManager による利用制限・サーキットブレーカー等（設定に基づく）

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス PID / データ鮮度チェック
  - TradeMonitor: 滞留注文検出・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限チェック、ダッシュボード更新・リスクログ出力
  - KillSwitch: 条件達成時にフラグファイルを書き込み ExecutionEngine を安全停止させる
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード

- Portfolio
  - 候補選定（スコア順）、等重／スコア加重、リスクベースのポジションサイズ計算
  - セクターキャップ適用、レジームに基づく資金乗数

- Research / AI
  - ファクター計算（Momentum / Volatility / Value）
  - 特徴量探索（将来リターン、IC 計算、統計サマリー）
  - ニュース NLP（OpenAI を用いた銘柄単位センチメントスコア）
  - 市場レジーム判定（MA200 + マクロセンチメントの合成）

- Tools
  - Paper Trading 用検証レポート生成（期間指定可）
  - Paper Trading 用 DB（data/paper_trading.db）との分離

---

## 前提 / 依存

推奨環境:
- Python 3.10+（| 型注釈を利用）
- SQLite（標準ライブラリ）
- DuckDB（pip: duckdb）
- psutil（プロセス優先度 / CPU affinity）
- requests（LINE API）
- openai（OpenAI クライアント）
- streamlit（ダッシュボード、任意）

主要パッケージ（例）
- duckdb
- psutil
- requests
- openai
- streamlit

（実際の requirements.txt がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローンし作業ディレクトリへ移動
   - git clone ... && cd repo

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil requests openai streamlit

   （requirements.txt があれば `pip install -r requirements.txt`）

4. データディレクトリを作成
   - mkdir -p data

5. 環境変数（.env）を用意
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（デフォルトで読み込み有効）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - .env の雛形は .env.example を参照してください（リポジトリにある場合）。

6. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
   - KABU_API_PASSWORD — 必須（kabuステーション API 用）
   - OPENAI_API_KEY — AI 機能を使う場合必須
   - KABUSYS_ENV — environment: development | paper_trading | live（デフォルト: development）

7. （任意）Paper Trading 用 DB を使う場合
   - デフォルト: data/paper_trading.db
   - 環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（default: development）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（default: data/execution.pid）
- KILL_FLAG_PATH: Kill switch flag（default: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- PAPER_FILL_MODE: paper_trading の MockBroker の挙動（instant|partial|never|reject、default: instant）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 各 API の認証情報（必須）

（その他: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, LOG_LEVEL 等）

---

## 使い方（起動コマンド例）

基本的にパッケージのモジュールを -m で実行します。

- 監視ループを起動（監視 DB は Settings.sqlite_path を使用）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（例: MONITOR_POLL_INTERVAL=30）

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、Paper Trading 用 DB（data/paper_trading.db）に記録します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- Streamlit ダッシュボード（監視データを可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI / Research（Python から関数を呼ぶ）
  - ニュース NLP を実行（例: Python REPL）
    - from datetime import date
      from kabusys.ai.news_nlp import score_news
      import duckdb, os
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, target_date=date(2026,4,1), api_key=os.environ.get("OPENAI_API_KEY"))
  - レジーム判定
    - from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date=date(2026,4,1), api_key=...)

- 開発用: MonitoringEngine を単発で実行（テスト）
  - MonitoringEngine.run_once() を使ってユニットテスト的に 1 回だけ各チェックを実行可能

注意点:
- Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番パス）を使用します。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合 DB を分離します。
- 実行時、最初にプロセス優先度を "high" に設定する処理が呼ばれます（psutil の権限に依存して失敗する場合は警告でスキップ）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - .env 自動ロードロジック、Settings クラス（環境変数ラッパ）
- run_monitoring.py
- run_execution.py

サブパッケージ:
- ai/
  - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite テーブル作成 / DB ラッパ
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py — 滞留注文 / 約定異常検出
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — フラグファイル書き込みによる停止シグナル
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 各 Monitor をまとめる（ポーリング）
  - streamlit_dashboard.py — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定・スケーリング・単元丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリー等
- execution/
  - reconciler.py — 起動時リコンシリエーション
  - order_manager.py — 発注ワークフロー（作成/送信/同期）
  - （その他ブローカー/リポジトリ関連モジュールはこの配下）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

その他:
- data/ — デフォルトの DB ファイル配置（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）
- .env / .env.local（プロジェクトルートに配置すると自動読み込み）

---

## 注意事項 / 運用メモ

- .env の自動ロード
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して .env/.env.local を読み込みます。
  - OS 環境変数のほうが優先され、.env.local は .env を上書きします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できます。

- DB マイグレーション
  - monitoring_db.init_monitoring_db() は起動時に呼ばれ、必要なテーブルやカラムを作成・マイグレーションします（冪等）。

- Paper Trading
  - KABUSYS_ENV=paper_trading 時は broker が Mock 実装となり、paper_sqlite_path に記録します。本番データと完全に分離されます。

- OpenAI 利用
  - API 失敗時はフォールバック（ゼロ或いはスキップ）して継続する実装になっていますが、AI 機能を正しく動かすには OPENAI_API_KEY を設定してください。
  - rate limit / 5xx 等へのリトライ（指数バックオフ）実装があります。

- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。psutil の権限によって失敗することがあります（その場合は警告）。

---

## よく使うコマンド例

- 監視起動（デフォルト間隔 60 秒）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Execution 起動（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper 検証レポート（2026-04-01 〜 2026-04-11）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

もし README に追記してほしいポイント（例: サンプル .env.example、requirements.txt の自動生成、Docker / systemd ユニット例、詳しい API 使用例など）があれば教えてください。必要に応じてセクションを拡張します。