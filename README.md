# KabuSys

KabuSys は日本株向けの自動売買システム（ライブラリ兼実行コンポーネント）です。本リポジトリは注文実行、監視、ポートフォリオ構築、研究用ファクター計算、AI を利用したニュース解析などのコンポーネントを含みます。

以下はこのコードベースの README（日本語）です。

---

## プロジェクト概要

- 日本株自動売買のためのモジュール群（Execution / Monitoring / Portfolio / Research / AI）。
- 注文の作成・管理、ブローカーとの同期（Reconciler）、リスク監視、監視ログ永続化（SQLite）、時系列解析（DuckDB）などを提供。
- Paper Trading モードを備え、本番 DB と分離して検証が可能。
- ニュースの NLP（OpenAI）を使った銘柄センチメントや市場レジーム判定機能を含む。

---

## 主な機能（機能一覧）

- Execution
  - 注文作成・管理（OrderManager）
  - ExecutionEngine（起動、セッション管理、PID 管理、停止フラグ対応）
  - ブローカー抽象化（実ブローカー / モックの切り替え）

- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス状態／データ鮮度監視）
  - TradeMonitor（滞留注文 / 約定異常価格検出）
  - RiskMonitor（ドローダウン・ポジション上限監視、ダッシュボード更新）
  - MonitoringEngine（複数モニタのポーリング統合）
  - AlertManager（LINE Push を使った通知）
  - KillSwitch（条件に応じて stop フラグを書き、ExecutionEngine を停止）

- Portfolio
  - 候補選定、重み付け（等配分／スコア配分）
  - ポジションサイズ計算（リスクベース、上限・ロット丸め）
  - セクターキャップ・レジーム調整

- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索、将来リターン計算、IC（Information Coefficient）等

- AI
  - ニュース NLP による銘柄センチメントスコアリング（OpenAI）
  - 市場レジーム判定（ETF MA とマクロセンチメントの合成）

- Tools
  - paper_verification_report: Paper Trading ログを集計してレポートを出力
  - Streamlit ダッシュボード（監視データ可視化）

---

## 前提 / 必要なもの

- Python 3.10 以上を推奨（typing の使用に適合）
- 主要依存（例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit（ダッシュボード利用時）
- SQLite（組み込み DB）、ファイルアクセス権（data/ 配下への読み書き）

（実際の依存はプロジェクトの requirements.txt や pyproject.toml を参照してください。無ければ上記パッケージをインストールしてください）

---

## セットアップ手順

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

3. 環境変数の設定
   - ルートに `.env` / `.env.local` を置くと自動で読み込まれます（CWD ではなくソースファイル位置からプロジェクトルートを検出）。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）を使う場合は必須

5. データディレクトリ
   - デフォルトで data/ 以下に DB やフラグファイルを作成します。プロジェクトルートに `data/` を作るか、環境変数でパスを上書きしてください。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合、Execution は MockBrokerClient を使い `data/paper_trading.db` を使用して本番 DB と分離
- SQLITE_PATH: 監視用 SQLite パス。デフォルト: data/monitoring.db
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject、デフォルト instant）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH: execution PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグ（デフォルト data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1" で有効）

---

## 実行方法（使い方）

- 監視ループ起動（Monitoring）
  - コマンド:
    - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（秒、デフォルト 60）。
    - 監視は sqlite_path（Settings.sqlite_path）を使ってログを永続化します（Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計）。
    - 停止: プロジェクトルートの `data/stop_requested.flag` ファイルを作成するとループが終了します。

- Execution 起動（発注エンジン）
  - コマンド:
    - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番 DB と分離されます。
    - 実行中は `data/execution.pid` を作成。`data/stop_requested.flag` を作ると安全に停止します。
    - 起動時に kill.flag が既にあると起動せず終了します。

- Streamlit 監視ダッシュボード
  - コマンド:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 概要:
    - SQLite を読み取り専用で開いて監視ダッシュボードを表示します。MonitoringEngine を起動していないとデータが存在しない旨が表示されます。

- Paper Trading 検証レポート（ツール）
  - コマンド:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定: --db /path/to/paper_trading.db （未指定時は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）
  - 出力: 標準出力に検証レポートを表示します（稼働率、注文成功率、送信率、レイテンシ等）。

- AI 機能（プログラム的に呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date（datetime.date）を渡してニューススコアを ai_scores テーブルに書き込みます。
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを判定して market_regime テーブルに書き込みます。
  - 注意: OpenAI 呼び出しは API 失敗時にフェイルセーフ（スコア 0.0 等）やリトライ（指数バックオフ）を行いますが、API キーは必須です。

---

## 制御ファイル（data/ 配下）

- data/execution.pid — ExecutionEngine が作成する PID ファイル
- data/stop_requested.flag — 存在すると run_monitoring / run_execution が停止する（外部から停止させる用途）
- data/kill.flag — KillSwitch が条件を満たしたときに書き込む停止理由（Execution の外部停止トリガ）
- DB ファイル（デフォルト）
  - data/monitoring.db — 監視ログ（SQLite）
  - data/paper_trading.db — paper_trading 用 SQLite（分離運用）
  - data/kabusys.duckdb — DuckDB（時系列データ等）

---

## 開発メモ / 注意点

- Settings（kabusys.config）:
  - .env / .env.local を自動で読み込みます（OS 環境変数が優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で抑止可能。
  - 必須のキー（JQUANTS_REFRESH_TOKEN など）は Settings プロパティで取得時にチェックされます。
- プロセス優先度:
  - run_monitoring / run_execution の起動時に set_process_priority("high") を呼び出します（psutil を利用）。権限不足などで失敗する場合は警告を出しスキップします。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() はテーブルを冪等に作成し、既存 DB にカラムを追加する簡易マイグレーションを行います（例: latency_ms, peak_value の追加）。
- テスト / モック:
  - paper_trading モードや一部の関数はモック・テストを想定して設計されています。OpenAI 呼び出し等はテスト時に差し替え可能です。

---

## ディレクトリ構成（主要ファイル説明）

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / 設定管理（.env 自動ロード含む）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 切替対応）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py — ニュースの NLP（OpenAI）による銘柄スコア付与
    - regime_detector.py — 市場レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログ永続化層（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の生成・評価
    - alert_manager.py — LINE 通知送信
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ / run_once 対応
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — 注文管理の外向き API
    - reconciler.py — 再起動時の注文・ポジション照合
    - （その他：broker_factory, execution_engine, order_repository 等が存在）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・資金配分（ロット丸め等）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Vol/Value 等ファクター計算（DuckDB 利用）
    - feature_exploration.py — 将来リターン計算・IC 等
  - utils/
    - process_priority.py — psutil を使った優先度/CPU affinity ユーティリティ
  - data/  (リポジトリに含まれないことが多い。実行時に使用／作成される)
    - monitoring.db, paper_trading.db, kabusys.duckdb, *.flag, *.pid など

---

## よくある運用例

- 監視を常時稼働させつつ、必要に応じて Execution を起動／停止する
  - 監視は常に本番 monitoring.db を使い、Execution のプロセス状態やデータ鮮度をチェックしてアラート/kill 判定を行う
- Paper Trading の検証
  - KABUSYS_ENV=paper_trading を設定して run_execution を起動 → data/paper_trading.db にのみ記録
  - 実行結果を paper_verification_report で集計

---

必要であれば、README に以下の追加情報も追記できます（ご希望に応じて）:

- 依存関係の exact list（requirements.txt 作成）
- Docker / systemd ユニット例（デーモン化）
- CI / テスト実行方法（ユニットテスト、モック例）
- 実例の .env.example（必須キーのテンプレート）

追加で欲しい情報や、README のフォーマット変更（英語版、Badge、ライセンス表記など）があれば教えてください。