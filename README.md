# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム（プロトタイプ）です。バックテスト／リサーチ用の DuckDB ベースのデータ処理、銘柄選定・配分・株数計算などのポートフォリオ構築ロジック、発注エンジン（本番 / ペーパー切替）、監視 / アラート基盤、LLM を用いたニュースセンチメント / レジーム判定などを含んでいます。

---

## 概要

このリポジトリは以下の責務を持つモジュールで構成されています（主要機能）:

- execution: 発注エンジン、ブローカー抽象化（本番と Mock を切替可能）、オーダー管理、リコンシリエーション
- monitoring: システム稼働監視、注文監視、リスク監視、kill-switch、LINE による通知、Streamlit ダッシュボード
- portfolio: 候補選定、重み計算、ポジションサイジング、セクター制約、レジーム乗数
- research: ファクター計算、特徴量探索、IC 計算などのリサーチ機能（DuckDB 経由）
- ai: ニュース NLP（OpenAI）による銘柄センチメント、レジーム判定
- tools: Paper Trading の検証レポート生成スクリプト等
- utils: プロセス優先度や CPU affinity のユーティリティ
- config: 環境変数 / .env 読み込み・設定管理

設計上のポイント:
- DuckDB や SQLite をローカル DB として利用（データ処理と監視ログを分離）
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離して専用 SQLite を使用
- OpenAI を使った NLP 機能はキーが必須で、API 失敗はフォールバックで安全に扱う設計
- .env 自動読込機能あり（プロジェクトルートの .env / .env.local）だが無効化可能

---

## 主な機能一覧

- Execution / Broker
  - 本番／ペーパー切替（MockBroker）
  - 発注・状態遷移管理、再起動時のリコンシリエーション
  - リスク管理（Rate limit、ポジション上限、ドローダウンなど）
- Monitoring
  - システム資源（CPU/MEM/DISK）と Execution プロセスの監視
  - 注文滞留・約定異常の検出
  - Kill Switch（条件により data/kill.flag を書き込み、Engine を停止）
  - LINE への通知（AlertManager）
  - Streamlit ダッシュボード（read-only）
- Portfolio Construction
  - 候補選定（スコア順、上位 N）
  - 等重・スコア加重・リスクベース配分
  - セクター上限適用、レジーム乗数
  - 株数決定（単元丸め、aggregate cap）
- Research / Data
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン、IC、統計サマリ、Z-score 正規化
- AI（OpenAI）
  - ニュース記事群を LLM でセンチメント化して ai_scores に書き込み
  - マクロタイトルを LLM で評価して市場レジーム判定を行い market_regime に書き込み
- Tools
  - Paper Trading 向け検証レポート生成スクリプト（成否判定・レイテンシ指標等）

---

## セットアップ手順（開発向け）

前提:
- Python 3.10 以上（型アノテーションに `X | Y` 形式を使用）
- Git リポジトリがプロジェクトルートに存在すること（.env 自動読み込みに利用）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係インストール
   - requirements.txt が無ければ下記を個別インストールしてください（最低限）:
     - pip install duckdb psutil requests openai streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合はそれを使ってください）
   - pip install -r requirements.txt

3. ディレクトリ作成
   - data ディレクトリを作成（DB を置くため）
     - mkdir -p data

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（OS 環境変数優先）。
   - 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 主要な環境変数（参考）
   - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
   - OPENAI_API_KEY=sk-...
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PAPER_FILL_MODE=instant|partial|never|reject
   - MONITOR_POLL_INTERVAL（秒）: 監視ポーリング間隔（run_monitoring 用、デフォルト 60）
   - KILL_FLAG_PATH=data/kill.flag
   - PID_FILE_PATH=data/execution.pid

   例 .env:
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   ```

---

## 使い方（主要スクリプト）

注意: 監視・実行ループは停止フラグファイル data/stop_requested.flag や data/kill.flag を用います。手動で停止する場合はこれらファイルを作成・削除してください。

- 実行エンジン（ExecutionEngine）起動
  - 本番モード:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレーディング（MockBroker を自動利用）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper 用 DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存され、本番 DB と分離されます。
  - Execution は data/execution.pid を作成します。停止フラグ（data/stop_requested.flag）を検知すると安全停止します。

- 監視ループ起動（SystemMonitor を定期実行）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書きできます:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は monitoring DB（Settings.sqlite_path）を使います。Monitoring は KABUSYS_ENV にかかわらず sqlite_path を参照します。

- Streamlit ダッシュボード（監視用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開きます。MonitoringEngine がデータを書き込んでいることが前提です。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  - コマンドライン引数で期間・DB を指定可能。デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

- AI 機能（ニュースセンチメント / レジーム判定）
  - プログラム内から呼び出します。例:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - OpenAI API キーが必要（引数または環境変数 OPENAI_API_KEY）。

---

## 実行時のファイル / フラグ

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py が監視しているフラグ。存在するとループを終了します（外部プロセスによる停止指示用）。
- data/kill.flag
  - KillSwitch がリスクトリガー発生時に書き込むファイル。ExecutionEngine 側は起動時にこれを検出して起動を抑止できます。
- data/execution.pid（デフォルト）
  - ExecutionEngine の PID を書き込むファイル。system monitor は PID の存在・生存確認を行います。

---

## 設定管理 (.env の取り扱い)

- config.py はプロジェクトルート（.git または pyproject.toml を基準）を探索して .env, .env.local を自動読み込みします（OS 環境変数が優先）。
- .env.local は .env の上書きに使えます（ローカル上の秘密情報など）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settingsクラスにより各種設定値へアクセスできます。KABUSYS_ENV は "development", "paper_trading", "live" のいずれかでなければ例外になります。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 管理
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - broker_api.py, broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...（発注 / ブローカー関連）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ / 永続化
    - system_monitor.py — CPU/MEM/DISK / データ鮮度 / PID チェック
    - trade_monitor.py — 注文滞留 / 約定異常検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 複数モニタ束ねるエンジン
    - streamlit_dashboard.py — 監視ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・制限適用
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — マクロセンチメント + MA200 によるレジーム判定
  - data/ (ランタイムで生成される）
    - monitoring.db（デフォルト） — 監視ログ SQLite
    - paper_trading.db（ペーパー用）
    - kabusys.duckdb（DuckDB データ）
    - execution.pid / stop_requested.flag / kill.flag

---

## 運用上の注意点

- Monitoring の DB 初期化はスクリプト実行時に自動で行われます（init_monitoring_db を利用）。
- Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path を使用します（監視は本番 DB/別 DB の混同を避ける必要あり）。
- Paper Trading と本番 DB は分離されています（settings.is_paper により paper_sqlite_path を利用）。
- OpenAI 呼び出しはレート制限やネットワーク障害を考慮してリトライ・フェイルセーフ設計になっていますが、API キーの管理とコスト管理に注意してください。
- process priority / cpu affinity の設定は OS に依存し、アクセス権限が無い場合は警告を出してスキップします（psutil を使用）。

---

## よく使うコマンドまとめ

- 仮想環境作成・有効化:
  - python -m venv .venv
  - source .venv/bin/activate
- 依存関係インストール:
  - pip install duckdb psutil requests openai streamlit
- ExecutionEngine 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Streamlit ダッシュボード起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

---

この README はコードベースに基づいて作成しています。導入や運用で不明点があれば、該当モジュール（monitoring/*.py, execution/*.py, ai/*.py, portfolio/*.py, research/*.py）内の docstring コメントを参照してください。