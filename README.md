# KabuSys

KabuSys は日本株向けの自動売買フレームワークです。マーケットデータの研究・ファクター計算、ポートフォリオ構築、発注エンジン、監視（Monitoring）、AI を用いたニュースセンチメント評価などを含むモジュール群で構成されています。プロダクション／ペーパートレードの切替や、監視用ダッシュボード、LINE 通知など運用に必要な機能を備えています。

## 主な特徴
- ExecutionEngine（発注エンジン）
  - ブローカー抽象化（本番／モック切替）
  - リスク管理・ポジション上限・発注レート制御
  - 再起動時のリコンシリエーション（Reconciler）
- Paper trading モード
  - KABUSYS_ENV=paper_trading で MockBroker を使用し、paper_trading 用 DB に完全分離
- Monitoring（監視）
  - System / Trade / Risk monitoring（ログは SQLite に永続化）
  - Kill switch（閾値超過で data/kill.flag を書き込み、ExecutionEngine を停止）
  - LINE によるアラート通知（AlertManager）
  - Streamlit ダッシュボード（監視データの可視化）
- Research / Portfolio ライブラリ
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - ポートフォリオ選別・重み計算・サイズ決定（等分／スコア加重／リスクベース）
  - セクター制限・レジーム乗数の適用
- AI モジュール
  - ニュースを OpenAI （gpt-4o-mini）でスコアリングして ai_scores に保存
  - マクロニュース + ETF MA200 を使った市場レジーム判定
- 運用ユーティリティ
  - process priority / CPU affinity 設定ユーティリティ
  - .env 自動読み込み・設定管理

---

## 準備・セットアップ

前提
- Python 3.10+（型注釈で | を使用）
- SQLite（標準ライブラリで利用）
- OS に応じた権限（プロセス優先度 / CPU affinity を設定する場合）

推奨手順（プロジェクトルートで実行）:

1. リポジトリをクローンして移動
   - git clone ... && cd <project_root>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がない場合は上記を参照してください。追加の依存があれば適宜インストールしてください。）

4. data ディレクトリを作成
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートの .env/.env.local を作成。自動読み込みはデフォルトで有効です（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 最低限設定が必要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — 必須（J-Quants 用）
     - KABU_API_PASSWORD — 必須（kabuステーション API 用）
     - OPENAI_API_KEY — AI 機能を使う場合に必須
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
     - その他は下記「重要な環境変数」を参照

注意:
- paper_trading モードでは発注はモックブローカーに行われ、DB は data/paper_trading.db に分離されます。
- Monitoring は説明どおり、本番 sqlite_path を常に参照する設計部分があります（run_monitoring 起動時の挙動に注意）。

---

## 使い方（主要な実行方法）

プロジェクトルートから実行する例を示します。`src/` 配下のスクリプトは直接実行できます。

- Monitoring を起動（監視ポーリングループ）
  - python src/kabusys/run_monitoring.py
  - オプション: 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60）
  - 実行中に data/stop_requested.flag が存在すると監視ループは終了します。

- ExecutionEngine（発注エンジン）を起動
  - python src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、data/paper_trading.db に書き込みます。
  - 実行中に data/stop_requested.flag が存在するとエンジンは停止します。

- Paper Trading 検証レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または: python src/kabusys/tools/paper_verification_report.py --from ... --to ...
  - オプションで --db に DB パスを指定可能（デフォルト: data/paper_trading.db）

- Streamlit ダッシュボード（監視画面）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視データに read-only で接続して表示します。MonitoringEngine を先に起動してデータを作成してください。

- AI スコア / レジーム判定
  - ai モジュールは関数として提供（kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）。OpenAI API キーが必要です。
  - 例（スクリプトや REPL から）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, date(2026, 4, 15), api_key="...")

停止・強制停止:
- ExecutionEngine に対する停止シグナルは data/kill.flag（KillSwitch）を用います。KillSwitch は特定のリスク状況を検出すると flag を書き込み、実行プロセス側で検出して停止します。
- run_* スクリプトは data/stop_requested.flag でループを終了します。

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API を使う機能で必要
- PAPER_FILL_MODE: paper trading の約定振る舞い（instant | partial | never | reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: Monitoring 用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch 用フラグパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

設定ファイル:
- プロジェクトルートの `.env` / `.env.local` があれば自動で読み込まれます（ただし OS 環境変数が優先）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 運用上の注意点
- process priority の設定（高優先度）はプラットフォームと権限に依存します。psutil を使って設定しますが、権限不足や非対応 OS の場合は警告が出てスキップされます。
- Monitoring の DB マイグレーションは init_monitoring_db() が冪等で行います。既存 DB にカラム追加が必要な場合もスクリプト内で対応しています。
- AI 呼び出しは外部 API（OpenAI）に依存するため、API エラーやレート制限に対してリトライやフォールバック（0.0）を行う設計です。請求やレートに注意してください。
- Paper trading は本番 DB から独立していますが、Monitoring は本番 sqlite_path を参照する実装箇所があるため、運用時はパス設定に注意してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- run_monitoring.py
- run_execution.py

サブパッケージ:
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py, broker_api.py, ...（ブローカー関連）
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
  - streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py
- data/ (実行時に利用／作成される。DB / PID / flag ファイルを配置)
  - kabusys.duckdb (デフォルト)
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 用)
  - execution.pid
  - kill.flag / stop_requested.flag

（上記はコードベースから抽出した主要ファイルです。プロジェクト全体の完全なツリーはローカルリポジトリでご確認ください。）

---

## 開発用・テスト用のヒント
- モジュールは可能な限り副作用を抑えているため、ユニットテストが書きやすい設計です（関数に接続を注入するスタイル等）。
- OpenAI や外部 API 呼び出し部分は _call_openai_api をパッチしてテスト可能です（unittest.mock.patch を推奨）。
- MonitoringEngine は run_once() を持つため、1回分のチェックをユニットテストで呼び出して振る舞いを確認できます。

---

この README はコードベースの公開ソースから主要機能・起動方法・設定を抜粋してまとめたものです。より詳細な API や内部設計（StrategyModel.md / PortfolioConstruction.md 等の設計ドキュメント）がプロジェクトに含まれていればそちらも参照してください。質問や補足があれば教えてください。