# KabuSys

日本株向けの自動売買／リサーチ／監視ユーティリティ群です。  
このリポジトリは取引実行・モニタリング・ポートフォリオ構築・ファクター研究・AIによるニュースセンチメント評価などの機能を持つモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は次のような責務を持つモジュール群で構成された小規模な自動売買基盤です。

- ExecutionEngine（発注・注文管理・リスク制御）
- Monitoring（システム稼働監視、注文監視、リスク監視、アラート）
- Portfolio construction（候補選定、重み計算、ポジションサイジング、セクター制約）
- Research（ファクター計算、将来リターン・IC 計算、特徴量解析）
- AI（ニュースセンチメントの LLM スコアリング、マーケットレジーム判定）
- Tools（Paper Trading の検証レポート生成、Streamlit ダッシュボードなど）

設計上の方針は「本番DBと paper_trading の分離」「ルックアヘッドバイアスの回避」「フェイルセーフ（API失敗時は安全側にフォールバック）」などです。

---

## 主な機能一覧

- 実行（Execution）
  - ブローカークライアントと連携して注文を作成・送信・同期
  - 再起動時のリコンシリエーション（Reconciler）
  - リスクマネージャ（利用率 / ドローダウン等）
  - Paper Trading モード（モックブローカー、専用 SQLite DB）
- 監視（Monitoring）
  - システム状態（CPU/メモリ/ディスク、プロセス生存）ログ
  - 注文滞留・約定異常検出
  - ドローダウン・ポジション上限監視（Kill Switch により Execution 停止信号）
  - LINE へのプッシュ通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- ポートフォリオ構築（Portfolio）
  - 候補選定、等金額／スコア加重の重み付け
  - セクター集中制限、レジーム乗数
  - ポジションサイジング（lot 単位丸め、利用可能資金に応じたスケール）
- リサーチ（Research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）計算、要約統計
- AI（OpenAI を利用）
  - ニュース記事を LLM でセンチメント評価 → ai_scores へ書込
  - マクロニュース + ETF MA200 による日次レジーム判定
  - API 呼び出しはリトライ・バックオフ、有効性検証を実装
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - .env 読み込み・設定管理（Settings クラス）
  - Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...（省略）

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要依存（手動インストールの例）:
     - pip install duckdb psutil openai requests streamlit

   ※ 実行環境により追加のパッケージが必要になる場合があります。

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を作成することで環境変数を自動読み込みします（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要な環境変数は次のとおり（詳細は下の「環境変数」を参照）:
     - KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, 等

5. データディレクトリ作成
   - デフォルトでは data/ 以下に DB 等を作成します。必要に応じてディレクトリを作成してください:
     - mkdir -p data

---

## 環境変数（主なもの）

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用 LINE 設定（省略可）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant|partial|never|reject。デフォルト: instant）
- PID_FILE_PATH: Execution 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch フラグファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）

---

## 使い方（主要コマンド）

前提: パッケージソースをカレントの Python モジュール検索パスに入れておく必要があります。簡単な方法:

- 一時的に PYTHONPATH を設定して実行:
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - PYTHONPATH=src python -m kabusys.run_execution

- またはパッケージを開発インストール:
  - pip install -e .

### 監視（Monitoring）起動

- デフォルトのポーリング間隔 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可）:
  - PYTHONPATH=src python -m kabusys.run_monitoring

- 例（ポーリング間隔を 30 秒にする）:
  - MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring

- 動作:
  - プロセス優先度を high に設定（可能な場合）
  - monitoring DB（settings.sqlite_path）を初期化（init_monitoring_db）
  - SystemMonitor の巡回処理を行い system_status / risk_logs などに記録

### 実行（Execution）起動

- Paper Trading モード（本番 DB と分離）:
  - KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution

- 本番モード（live）:
  - KABUSYS_ENV=live PYTHONPATH=src python -m kabusys.run_execution

- 動作:
  - BrokerClientFactory により KABUSYS_ENV に応じたブローカークライアントを生成（paper_trading では MockBrokerClient）
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行
  - DuckDB は settings.duckdb_path を使用

### Streamlit ダッシュボード（監視 UI）

- 実行例（デフォルト DB = data/monitoring.db）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ダッシュボードは読み取り専用で monitoring DB を参照します（存在しない場合はエラー表示）。

### Paper Trading 検証レポート（ツール）

- レポート生成:
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db /path/to/data/paper_trading.db
  - 検証指標: 稼働率 (uptime), 注文成功率 (fill rate), 送信率, P95 レイテンシ など

### AI 機能（ニューススコアリング / レジーム判定）

- OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数で指定）。
- Python から呼び出す例:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="sk-...")
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="sk-...")

- 注意: API 呼び出しはレート制限・ネットワーク障害に備えリトライ・フォールバック実装がありますが、APIキー未設定時は ValueError が発生します。

---

## 監視の自動停止（Kill Switch）

- KillSwitch は risk_monitor の判定（ドローダウン超過 / ポジション上限超過など）で flag ファイル（settings.kill_flag_path）を作成します。
- ExecutionEngine 側は起動時にこの flag をチェックし、フラグが存在する場合は停止する、または起動時にフラグをクリアする設定があります（Settings.kill_flag_clear_on_start）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / Settings 管理、.env 自動ロード機能
- run_monitoring.py — SystemMonitor のポーリング起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- execution/
  - order_manager.py, reconciler.py, ...（発注・同期・リスク関連）
- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - monitoring_engine.py, kill_switch.py, alert_manager.py
  - streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py, regime_detector.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py（プロセス優先度 / CPU affinity）

（実際のファイルや追加モジュールはソースツリーを参照してください）

---

## 実行上の注意 / 運用メモ

- Paper Trading モードは本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- Settings は起動時に .env/.env.local を自動読み込みしますが、OS 環境変数が優先されます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL は正の整数で指定してください（1 未満や無効値はデフォルト 60 秒にフォールバックします）。
- OpenAI API を利用する機能は API 使用料が発生するため注意してください。
- psutil によるプロセス優先度設定や CPU affinity は権限や OS に依存し、失敗した場合は警告ログが出て処理は継続します。
- DuckDB / SQLite のスキーママイグレーションは簡易的に行われます（init_monitoring_db が必要カラムを追加する処理を含む）。

---

## 開発／テスト

- 各モジュールはできるだけ副作用を最小化する（純関数・DBアクセス分離）設計です。
- research / portfolio モジュールは DuckDB 接続を受け取り、テーブル（prices_daily 等）だけを参照します。ローカルで DuckDB を用意してユニットテストを実行してください。
- OpenAI 呼び出し部分は内部で関数を分離しているため、単体テストでは該当関数をモックして検証できます（例: unittest.mock.patch）。

---

以上が README の概要です。必要であれば以下の追加情報を作成します：
- さらに詳しい環境変数一覧とデフォルト値のテーブル
- systemd / supervisor 用のユニットファイルサンプル（起動・ログ管理）
- 開発用の Makefile / docker-compose 設定例

どれを追加しますか？