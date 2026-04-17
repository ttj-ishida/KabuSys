# KabuSys

日本株向け自動売買・解析プラットフォームの小規模実装（モジュール群のみ）。  
この README はリポジトリ内の主要コンポーネント、起動方法、環境変数、ディレクトリ構成などの使い方をまとめたものです。

注意: 本 README はソースコード（src/kabusys 以下）を元に作成しています。実運用では追加の設定・安全対策が必要です。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群から構成されます。

- Execution (発注エンジン)
  - ブローカーとのやり取り、注文の状態管理、再起動時のリコンシリエーション
  - Paper Trading モード（モックブローカー）をサポート（本番 DB と完全分離）
- Monitoring（監視）
  - システムリソース・プロセスの監視、注文滞留／約定異常の検出、リスク（ドローダウン・ポジション数）監視
  - SQLite ベースの監視ログ永続化（monitoring.db）
  - LINE へのアラート通知（任意）
  - Streamlit ダッシュボード（可視化）
- Portfolio（銘柄選定・配分・ポジションサイズ決定）
  - 候補選定、等配分／スコア配分、リスク調整、単元丸めなど
- Research（ファクター計算・特徴量探索）
  - モメンタム・ボラティリティ・バリューファクター、将来リターン・IC 等
- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースセンチメントの銘柄スコア付与、マクロニュースを使った市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成スクリプトなど

---

## 主な機能一覧

- run_execution: ExecutionEngine を起動（KABUSYS_ENV による paper/live 切替）
- run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔調整可）
- monitoring_db: 監視用 SQLite スキーマ初期化 / CRUD ラッパー
- MonitoringEngine: 各種モニタ（System/Trade/Risk）を束ねてアラート・KillSwitch を評価
- streamlit_dashboard: Streamlit を使った監視ダッシュボード
- ai.news_nlp: raw_news を LLM（OpenAI）で解析し ai_scores テーブルへ書込み
- ai.regime_detector: MA200 と LLM による市場レジーム判定、market_regime テーブルへ書込み
- portfolio.*: 候補選定・重み算出・ポジションサイズ計算・セクター制約等
- research.*: DuckDB 上の prices_daily / raw_financials を使ったファクター計算・解析
- tools.paper_verification_report: Paper Trading DB の検証レポート出力（期間指定可）

---

## 前提 / 必要環境

- Python 3.10 以上（ソース内で typing の | 演算子等を使用）
- SQLite（標準ライブラリ）
- DuckDB Python パッケージ
- psutil（プロセス情報取得）
- requests（LINE API 用）
- openai（OpenAI API クライアント）
- streamlit（ダッシュボード実行時）

推奨インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```
（requirements.txt がない場合は上記のように主要パッケージを個別にインストールしてください。）

---

## 環境変数（主なもの）

Settings クラスで参照される環境変数（省略時のデフォルトを併記）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合は必須)
- LINE_CHANNEL_ACCESS_TOKEN (LINE 通知を使う場合)
- LINE_USER_ID (LINE 通知を使う場合)
- KABUSYS_ENV: 開発環境フラグ。`development` / `paper_trading` / `live`（デフォルト: development）
  - `paper_trading` の場合は MockBroker を使い、Paper Trading 専用 DB に書き込む
- PAPER_FILL_MODE: paper_trading 時のマッチング動作（instant / partial / never / reject。デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB データベースパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグ（デフォルト: data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

自動環境ファイル読み込み:
- プロジェクトルートにある `.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

簡易 .env 例（.env.example 参照のこと）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. 必要な環境変数を設定（.env/.env.local を使うか export）
5. data ディレクトリを作成（必要なら）
```bash
mkdir -p data
```
6. DuckDB / SQLite DB は実行時に自動生成・マイグレーションが行われます（init_monitoring_db を使用）

---

## 使い方

基本的な起動コマンド例:

- ExecutionEngine を起動
  - 本番（live）または開発（development）では実際のブローカーを使います。paper_trading では MockBroker を使用し DB を分離します。
```bash
# 環境変数を設定した上で
python -m kabusys.run_execution
```

- Monitoring を起動（SystemMonitor のポーリングループ）
```bash
# ポーリング間隔を秒で指定（省略時 60 秒）
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

- Paper Trading 検証レポートを生成
```bash
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# --db オプションで DB パス指定可
```

- Streamlit ダッシュボード（監視データ可視化）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

プロセス制御 / 停止:
- ExecutionEngine 停止は kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）を作成することで指示できます。KillSwitch ロジックはリスク閾値を満たした場合に自動で書き込みます。
- run_execution, run_monitoring は PID ファイル / stop フラグを参照して安全に終了を検知します。

AI 機能:
- OpenAI API を使う機能（ニューススコアリング、レジーム判定）は OPENAI_API_KEY が必要です。
- 関数単位で呼び出し可能:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

その他ツール:
- Portfolio / Research / Position sizing 関数群は Python API として利用できます（DuckDB コネクション等を引数にとる純粋関数が中心）。

ログレベル:
- Settings.log_level または logging.basicConfig で調整してください。run_* スクリプトは起動時に INFO レベルで設定しています。

---

## ディレクトリ構成（抜粋）

リポジトリの主要なソース構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
    - __init__.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他の実装ファイル: broker_factory, execution_engine, order_repository, order_record etc.)
  - data/                     — デフォルト DB / PID / flag ファイルが配置される想定ディレクトリ（実行時に作成）
  - utils/
    - process_priority.py
    - __init__.py

（上記は主要ファイルの要約です。実際のツリーはリポジトリを参照してください。）

---

## 重要な挙動・注意点

- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db）を使用します。Paper Trading の監視データは通常の監視 DB に書き込まれます（実際の発注 DB は paper_trading_db に分離）。
- run_execution は KABUSYS_ENV=paper_trading の場合、MockBroker を使用し paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使います。
- Settings はプロジェクトルートの `.env` / `.env.local` を自動読み込みします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- OpenAI 呼び出しは外部 API に依存します。API の失敗に対してはフェイルセーフ（スコア0やスキップ）を基本方針としていますが、API キーがないと機能は動作しません。
- プロセス優先度や CPU affinity の設定は psutil を使って行い、権限不足等のエラーは警告ログに留めスキップされます。

---

## 開発者向けメモ

- DuckDB を使って市場価格や財務データ（prices_daily, raw_financials 等）を格納・参照する設計になっています。Research / AI モジュールは DuckDB の接続を受け取り SQL と Python を組み合わせて処理します。
- 多くのモジュールは「副作用を持たない純粋関数」または DB コネクション / クライアントを引数に取る形で設計されており、ユニットテストを作成しやすくなっています。
- テスト実行時には .env の自動読み込みをオフにするか、テスト用環境変数を設定して挙動を制御してください。

---

この README はコードベースの主要点をまとめたものです。さらに詳細な API 仕様や設計ドキュメント（例: PortfolioConstruction.md, StrategyModel.md）がリポジトリに存在する場合はそちらを参照してください。ご質問や追加で記載したい項目があれば教えてください。