# KabuSys

日本株向けの自動売買・リサーチ基盤ライブラリ（軽量プロトタイプ）。  
このリポジトリは、発注実行エンジン、監視 (Monitoring)、ポートフォリオ構築、リサーチ／ファクター計算、ニュースNLP / レジーム判定などのコンポーネント群を含みます。

以下はコードベース（src/kabusys）に基づく README です。

---

## プロジェクト概要

KabuSys は日本株アルゴリズム運用のためのモジュール群です。主な責務は：

- 発注実行（ExecutionEngine、OrderManager、Broker 接続）
- モニタリング（System / Trade / Risk、監視ログの永続化、アラート送信）
- ポートフォリオ構築（銘柄選定、重み付け、株数算出、セクター制限）
- リサーチ（ファクター算出、将来リターン、IC 計算、統計サマリ）
- AI 補助（ニュースを LLM でスコアリング、マクロセンチメントでレジーム判定）
- 開発支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード等）

設計上の特徴：

- DuckDB を用いた履歴データ参照（prices_daily / raw_financials 等）
- SQLite を用いた監視・発注ログ（monitoring.db / paper_trading.db 等）
- 環境変数／.env による設定（Settings クラス）
- Paper Trading モード（実ブローカーとは切り離された DB と MockBrokerClient の利用）
- フェイルセーフ重視（LLM/API エラー時のフォールバック、データ欠損時の安全処理）
- モジュールは可能な限り純粋関数・副作用の少ない設計を志向

---

## 機能一覧

- run_monitoring.py
  - SystemMonitor（CPU/Memory/Disk、Execution プロセス生存、データ鮮度）
  - TradeMonitor（滞留注文／約定価格異常検出）
  - RiskMonitor（ドローダウン、ポジション上限の監視）
  - KillSwitch（条件を満たしたら flag ファイルを書いて ExecutionEngine を停止）
  - AlertManager（LINE Push を用いた通知、クールダウン制御）
  - Streamlit ダッシュボードで監視情報を可視化可能

- run_execution.py
  - ExecutionEngine 起動（ブローカークライアントの注入）
  - Paper Trading モード時は mock ブローカーと専用 DB（data/paper_trading.db）を使用
  - リコンシリエーション（再起動後の同期）機能を備えた Reconciler

- portfolio モジュール
  - 銘柄選定（select_candidates）
  - 重み付け（等金額 / スコア加重）
  - セクター集中制限（apply_sector_cap）
  - ポジションサイジング（calc_position_sizes）

- research モジュール
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC・ランク・統計サマリ

- ai モジュール
  - news_nlp.score_news: OpenAI を用いたニュースセンチメントスコア付与（ai_scores への書込み）
  - regime_detector.score_regime: ETF の MA とマクロニュースを組み合わせた市場レジーム判定

- tools
  - paper_verification_report: Paper Trading DB を解析して検証レポートを標準出力に出力

- utils
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
  - config: .env 自動読み込みと Settings（環境変数ラッパ）

---

## セットアップ手順

前提：
- Python 3.10+（typing で論理和型 `|` を使用しているため）
- OS: Linux / macOS / Windows で動作（プロセス優先度設定は OS により差分あり）

推奨手順（開発環境）：

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - pip install duckdb psutil openai requests streamlit
   - （必要に応じてその他テスト用ライブラリを追加）

   代表的な requirements:
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit

3. 環境変数 / .env を用意
   - プロジェクトルートに `.env` / `.env.local` を配置可能（Settings モジュールが自動ロード）
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

   主要な環境変数（例）:
   - KABUSYS_ENV=development | paper_trading | live
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PAPER_FILL_MODE=instant|partial|never|reject
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - LOG_LEVEL=INFO

   例 .env（最小）:
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

4. データディレクトリを作成
   - mkdir -p data

5. DuckDB / SQLite DB の準備
   - DuckDB: 外部スクリプトや ETL で prices_daily, raw_financials, raw_news 等のテーブルを投入することを想定
   - monitoring の SQLite はアプリ起動時に自動でテーブルを作成する（init_monitoring_db）

---

## 使い方

以下は主要な実行方法の例です。いずれもプロジェクトルート（pyproject.toml/.git がある階層）から実行してください。

1. 監視ループを起動（Monitoring）
   - 環境変数でポーリング間隔を上書き可能（秒）
     - MONITOR_POLL_INTERVAL（デフォルト: 60）
   - 実行:
     - python -m kabusys.run_monitoring
   - 備考:
     - run_monitoring は Settings に関わらず「本番」sqlite_path を使って監視 DB を開きます（monitoring 用は環境分離しない設計）。

2. 発注エンジンを起動（Execution）
   - Paper Trading モードで起動する場合:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
   - 通常（本番 / development）:
     - export KABUSYS_ENV=development
     - python -m kabusys.run_execution
   - 備考:
     - paper_trading の場合は MockBrokerClient を使い、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
     - 起動時にプロセス優先度を "high" に設定しようとします（権限により失敗する場合は警告が出ます）。

3. Streamlit 監視ダッシュボード（ローカル閲覧）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only URI で SQLite を開くため、監視中の DB を安全に参照できます。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスを明示する場合:
     - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5. AI 機能の利用（ニューススコア／レジーム判定）
   - score_news / score_regime は DuckDB 接続と target_date を渡して呼び出す仕様です（スクリプト化して実行する想定）。
   - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
   - 例（簡易的）:
     - python -c "from kabusys.ai.news_nlp import score_news; import duckdb, datetime; conn = duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, datetime.date(2026,4,1)))"

6. 設定ファイルロード
   - Settings モジュールはプロジェクトルートにある `.git` または `pyproject.toml` を基準に自動で `.env` / `.env.local` を読み込みます。
   - OS 環境変数が優先され、`.env.local` は `.env` より優先して上書きされます。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## ディレクトリ構成（主要ファイル説明）

src/kabusys/
- __init__.py
  - パッケージメタ情報（__version__ 等）

- config.py
  - Settings クラス：環境変数/.env 読み込みと各種設定プロパティ

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モード対応）

- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py — SQLite テーブル初期化＆IO ラッパー（MonitoringDB）
  - system_monitor.py — CPU/Mem/Disk/プロセス/データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常の検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag による Execution 停止シグナル
  - alert_manager.py — LINE Push による通知（クールダウン付）
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

- execution/
  - order_manager.py, order_repository.py, reconciler.py, etc.
  - 発注ロジック・永続化・リコンシリエーションを扱う（メインロジックは execution 配下）

- portfolio/
  - portfolio_builder.py — 銘柄選定と重み計算
  - position_sizing.py — 発注株数計算、リスク制限、単元丸め
  - risk_adjustment.py — セクターキャップ、レジーム乗数

- research/
  - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB 利用）
  - feature_exploration.py — 将来リターン・IC・統計サマリ等

- ai/
  - news_nlp.py — raw_news を OpenAI で評価して ai_scores に書き込む
  - regime_detector.py — ETF MA とマクロニュースで市場レジームを判定

- tools/
  - paper_verification_report.py — Paper Trading DB を解析して検証レポート生成

その他:
- data/
  - デフォルトの DB 保存先 (data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db)
  - pid / kill.flag 等のファイルも data/ 下を想定

---

## 注意事項 / 運用上のメモ

- 権限
  - process priority / cpu affinity の設定は権限に依存します。AccessDenied が出てもアプリは継続します。
- Paper Trading
  - paper_trading モードでは実ブローカーから分離され、専用 SQLite に記録します（安全のため）。
- モジュールの副作用
  - Settings は起動時に `.env` を自動ロードします。テスト等で自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってください。
- DB マイグレーション
  - init_monitoring_db は冪等であり、既存 DB に列がない場合は ALTER TABLE による軽微なマイグレーションを行います。
- API キー
  - OpenAI の利用はコストがかかるため、実行環境では API キー管理に注意してください（ENV / secrets 管理推奨）。

---

README に記載の内容はコード（src/kabusys 配下）を要約したものです。運用や導入にあたっては各モジュールの docstring を参照し、環境変数や DB の仕様に合わせて設定してください。追加の利用例やデプロイ手順が必要であれば、用途に応じて追記します。