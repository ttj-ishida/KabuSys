# KabuSys

KabuSys は日本株向けの自動売買 / 監視 / リサーチ用ライブラリ群です。  
本リポジトリには実運用を想定したコンポーネント（ExecutionEngine、Monitoring、AI 支援モジュール、ポートフォリオ構築ロジック、リサーチ用ユーティリティ等）が含まれます。

以下はコードベースから読み取れる主要な機能・使い方・設定方法のまとめです。

---

## プロジェクト概要

- 自動売買エンジン（ExecutionEngine）と監視サブシステム（Monitoring）の実装。
- Paper Trading と Live（本番）を環境変数 `KABUSYS_ENV` で切り替え可能（`development` / `paper_trading` / `live`）。
- DuckDB を使ったデータ解析（価格・財務データなど）と、SQLite による監視ログ / 注文レコード保存。
- LLM（OpenAI）の API を用いたニュースセンチメント評価と市場レジーム判定機能（AI モジュール）。
- ポートフォリオ構築・リスク調整・ポジションサイジングの純粋関数群（ユニットテストしやすい設計）。
- Streamlit ベースの簡易ダッシュボード、運用検証用レポート生成ツールなどのユーティリティを含む。

---

## 主な機能一覧

- Execution
  - 起動スクリプト: run_execution.py
  - Broker クライアント工場、OrderManager、RiskManager、Reconciler（再起動時の同期処理）を含む。
  - Paper Trading 時は Broker のモックを使い DB を分離可能。

- Monitoring
  - 起動スクリプト: run_monitoring.py（定期ポーリングで SystemMonitor を実行）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス PID チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch: 条件により ExecutionEngine 停止フラグ（data/kill.flag）を作成
  - AlertManager: LINE Messaging API 経由の通知（クールダウン管理）
  - Monitoring DB 操作ユーティリティ（init_monitoring_db, MonitoringDB）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

- Research / Signals
  - research.factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を利用）
  - research.feature_exploration: 将来リターン、IC（Information Coefficient）、統計サマリ

- AI
  - ai.news_nlp: raw_news を集約して OpenAI に送り、銘柄ごとのセンチメントスコアを ai_scores テーブルに保存
  - ai.regime_detector: ETF (1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime を更新

- Portfolio
  - portfolio.portfolio_builder: 候補選定、等配分/スコア加重
  - portfolio.position_sizing: 発注株数決定、リスク制約・単元丸め
  - portfolio.risk_adjustment: セクターキャップ・レジーム乗数

- Tools
  - tools.paper_verification_report.py: Paper Trading DB を解析して稼働率・注文成功率・レイテンシ等の検証レポートを出力

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントの union 型 `X | None` 等を使用）
- Git 等でプロジェクトをクローンして作業ディレクトリをプロジェクトルートにすることを推奨

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

2. 必要パッケージをインストール
   - 以下は主要な依存ライブラリです（requirements.txt がある場合はそれを使用してください）。
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

3. データディレクトリの作成（初回）
   - mkdir -p data
   - （必要に応じて権限設定）

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先される）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...     (AI 機能を使う場合必須)
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject

5. DB 初期化
   - Monitoring 側は run_monitoring/run_execution 内で `init_monitoring_db()` が呼ばれるため、通常は手動初期化不要です。
   - DuckDB / SQLite のデータファイルは最初は無くても自動作成されますが、prices_daily や raw_financials など解析用テーブルは別途取り込み処理が必要です（本リポジトリ内にデータ取り込みスクリプトは含まれていません）。

---

## 使い方

※コマンドはプロジェクトルートから実行してください。

1. Monitoring を起動する
   - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
   - 実行例:
     - python -m kabusys.run_monitoring
     - または python src/kabusys/run_monitoring.py
   - 動作:
     - `data/stop_requested.flag` を検知するとループを抜けて終了します（外部停止制御）。
     - Monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を使います（環境に関係なく）。

2. ExecutionEngine を起動する
   - Paper Trading（KABUSYS_ENV=paper_trading）の場合は MockBrokerClient を使用し、Paper 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
   - 実行例:
     - python -m kabusys.run_execution
     - または python src/kabusys/run_execution.py
   - 停止フラグ:
     - 起動時 / 実行中に `data/stop_requested.flag` が存在すると起動を停止・実行中は停止します。
   - PID ファイル:
     - Execution は data/execution.pid を利用します（Settings.pid_file_path）。SystemMonitor が PID 存在を監視します。

3. Streamlit ダッシュボード
   - 実行例（read-only DB 指定可能）:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視データやポジション情報を可視化します。

4. Paper Trading 検証レポート
   - 使用例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     - --db に直接 DB パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

5. AI 機能
   - news_nlp.score_news(conn, target_date, api_key=None)
     - raw_news / news_symbols テーブルを集約 → OpenAI に送信 → ai_scores テーブルへ書き込み
     - OPENAI_API_KEY が必要（api_key 引数で上書き可能）
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して market_regime に保存
   - どちらも環境変数 OPENAI_API_KEY が無ければ例外（明示的にキーを渡すことも可能）。API 失敗時はフェイルセーフ動作（部分的にゼロフォールバック等）があります。

6. 設定の自動読み込み
   - プロジェクトルートの `.env` / `.env.local` が自動で読み込まれます。既存 OS 環境変数は保護されます。
   - 無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 環境変数（主要なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J‑Quants API 用トークン（必須箇所あり）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング秒（デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（一部設定は Settings クラスを参照）

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・ディレクトリ（src/kabusys 以下を中心に抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動読み込み等）
  - run_monitoring.py            — Monitoring ポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py           — SQLite 監視テーブル初期化・操作用クラス
    - system_monitor.py          — システム状態 / データ鮮度監視
    - trade_monitor.py           — 注文滞留 / 約定異常監視
    - risk_monitor.py            — ドローダウン / ポジション上限監視
    - kill_switch.py             — 停止フラグ管理（kill.flag）
    - alert_manager.py           — LINE 通知（クールダウン管理）
    - monitoring_engine.py       — 各 Monitor を束ねるランナー
    - streamlit_dashboard.py     — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - execution_engine.py
    - broker_factory.py
    - （その他ブローカ API / レコード定義など）
  - research/
    - factor_research.py         — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py     — 将来リターン/IC/統計ユーティリティ
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py                — ニュースセンチメント（OpenAI）
    - regime_detector.py         — 市場レジーム判定（MA200 + LLM）
  - data/                         — 実行時に利用されるデフォルト DB / フラグ等（git 追跡外推奨）
    - monitoring.db (default)
    - kabusys.duckdb (default)
    - paper_trading.db (default)

---

## 運用上の注意 / 実装上の特徴

- Settings クラスは .env 自動読み込みを行い、必須キーは明示的に取得時に検査します（_require）。
- Monitoring の DB 初期化（init_monitoring_db）は冪等設計で、既存スキーマに対する軽微なマイグレーション（カラム追加）を内包しています。
- Execution 起動時は Paper Trading の場合 DB を分離（PAPER_TRADING_SQLITE_PATH）して、本番 DB と完全に分離するよう設計されています。
- AI 機能は OpenAI API に依存し、429/タイムアウト/5xx 等をリトライする処理やレスポンス検証を組み込んでいます。API キー管理には注意してください。
- Process priority / CPU affinity の設定は psutil を利用し、プラットフォーム差異を吸収するよう設計されています。権限不足で設定できない場合は警告を出してスキップします。
- KillSwitch により監視が検出した重大リスク（例: ドローダウン超過）で Execution 停止フラグを書き込み、Execution 側はこれを検知して安全に停止します。

---

## よく使うコマンドまとめ（例）

- 仮想環境の作成・依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil requests openai streamlit

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution 起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 追加情報 / 開発のヒント

- .env.example を作成しておくと初期セットアップが楽になります（必須の環境変数は Settings クラスを参照）。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news / news_symbols など）は外部データ取り込みが必要です。データ取り込み機能は本リポジトリから別途用意してください。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます。
- AI 呼び出し部分は外部 API のため単体テストではモック（unittest.mock.patch）することを推奨します（コード内でそのための差し替えを想定しています）。

---

README に書かれている内容はコードベースの仕様や設計意図を元にまとめています。より具体的な実行手順や追加のスクリプト（データ投入、ブローカー接続サンプル等）が必要であれば、目的に合わせて追記サポートします。