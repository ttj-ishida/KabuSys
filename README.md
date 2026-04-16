# KabuSys

日本株向け自動売買システムのモジュール群。本リポジトリは売買実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、LLM を使ったニュース評価など、実運用を意識したコンポーネント群を提供します。

---

## プロジェクト概要
KabuSys は以下の主要機能を持つモジュラー設計の自動売買基盤です。

- 実際のブローカー API / モック（paper trading）を切り替え可能な実行エンジン
- 実行・約定・ポジションの永続化（SQLite）と分析用 DuckDB
- システム・注文・リスク監視（監視ログの永続化・アラート送信）
- LINE によるアラート送信機能（AlertManager）
- LLM（OpenAI）を用いたニュースセンチメント評価と市場レジーム判定
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- Research ツール（ファクター計算、IC計算、特徴量探索）
- Streamlit ベースの監視ダッシュボードと検証レポートツール

---

## 主な機能一覧
- Execution
  - ExecutionEngine（ブローカー抽象化 + リスク管理 + 注文管理）
  - Reconciler（起動時の状態同期）
  - BrokerFactory（本番 / モック切替）
- Monitoring
  - SystemMonitor（プロセス・CPU/メモリ/Disk・データ鮮度）
  - TradeMonitor（滞留注文・約定異常）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（フラグファイルでエンジン停止）
  - AlertManager（LINE Push API）
  - MonitoringEngine（各モニタのポーリング）
  - Streamlit ダッシュボード（read-only）
- AI
  - news_nlp（記事を集約して OpenAI でセンチメントスコアを生成）
  - regime_detector（ETF MA とマクロセンチメントで市場レジーム判定）
- Portfolio
  - 選定・重み付け・リスク調整・株数計算（純粋関数群）
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン / IC / 統計サマリー
- Utilities
  - process_priority（プロセス優先度 / CPU affinity）
  - config（.env 自動ロード / Settings）

---

## セットアップ手順

前提:
- Python 3.10+ を想定
- SQLite は標準で利用可能
- DuckDB を使用（duckdb パッケージ）

依存（例）:
- duckdb
- psutil
- requests
- openai
- streamlit
- (必要に応じて) その他のランタイム依存ライブラリ

pip でのインストール例:
```
python -m pip install duckdb psutil requests openai streamlit
```

環境変数:
- 本アプリケーションは .env / .env.local をプロジェクトルートから自動読み込みします（既存 OS 環境変数は保護）。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須（実行する機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（Settings.jquants_refresh_token が要求）
- KABU_API_PASSWORD — kabuステーション（本番）用
- OPENAI_API_KEY — news_nlp / regime_detector を使う場合
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager を利用する場合

主な Settings 関連（デフォルト値あり）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定モード）
- SQLITE_PATH: デフォルト data/monitoring.db
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: paper_trading モード用 DB（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ループの秒数（デフォルト 60）
- PID / flag のパスは Settings で上書き可能（デフォルト data/*.flag / data/execution.pid）

データディレクトリ:
- data/ 以下に SQLite や pid/flag ファイルを作成します。実行前に適宜ディレクトリを作成してください:
```
mkdir -p data
```

---

## 使い方（主要コマンド例）

1) 実行エンジン（ExecutionEngine）を起動
- 本番（本番ブローカー）:
```
export KABUSYS_ENV=live
python src/kabusys/run_execution.py
```
- Paper Trading（モックブローカー、DB を分離して data/paper_trading.db に記録）:
```
export KABUSYS_ENV=paper_trading
python src/kabusys/run_execution.py
```
- エンジンは data/stop_requested.flag を見ることで安全停止できます（存在すれば起動せず、実行中は検知して停止します）。

2) 監視ループ（Monitoring）を起動
```
python src/kabusys/run_monitoring.py
```
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（例: 30秒）
```
export MONITOR_POLL_INTERVAL=30
```
- 監視は常に本番 sqlite_path を使って監視ログを記録します（環境に依らず）。

3) Streamlit ダッシュボード（監視ビュー）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- ダッシュボードは監視 DB を read-only で開きます。監視が未起動だと DB が存在しない旨を表示します。

4) Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report
# 期間指定:
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# 別 DB を指定:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

5) AI 系バッチ（ニューススコア / レジーム判定）
- news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date、OPENAI_API_KEY を渡して呼び出します。スクリプト化して cron/日次バッチ等で実行してください。

停止・強制停止関連:
- ExecutionEngine 停止シグナル: data/kill.flag を書き込むと ExecutionEngine に停止を要求できます（KillSwitch による判定で自動生成もあり）。
- run_execution.py / run_monitoring.py は data/stop_requested.flag を見て終了します。

ログレベル:
- Settings.log_level でログレベルを指定できます（DEBUG/INFO/...）。run_* スクリプト内では logging.basicConfig(level=logging.INFO) が呼ばれます。

---

## .env / 設定の読み込み
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` を自動的に読み込みます。
- `.env.local` があれば上書き読み込みします（OS 環境変数は保護される）。
- フォーマットは一般的な KEY=VALUE、export KEY=VALUE、クォート・コメントに対応します。
- 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）
（src 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - execution/
    - execution_engine.py   — 実行エンジン本体（EngineConfig 等）
    - order_manager.py      — Order 管理 API
    - order_repository.py   — DB 永続化（SQLite）
    - reconciler.py         — 起動時リコンシリエーション
    - broker_factory.py     — ブローカークライアント生成
    - ...（broker_api 等）
  - monitoring/
    - monitoring_db.py      — 監視 DB 層（SQLite テーブル定義 + helper）
    - system_monitor.py     — システム監視
    - trade_monitor.py      — 注文監視
    - risk_monitor.py       — リスク監視
    - kill_switch.py        — kill.flag 書込用
    - alert_manager.py      — LINE 通知
    - monitoring_engine.py  — 各 Monitor の統合ポーリング
    - streamlit_dashboard.py— Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py  — 候補選定 / 重み付け
    - position_sizing.py    — 株数計算・スケーリング
    - risk_adjustment.py    — セクター上限 / レジーム乗数
  - research/
    - factor_research.py    — Momentum / Volatility / Value 等
    - feature_exploration.py— forward returns / IC / summary
  - ai/
    - news_nlp.py           — ニュース集約 & OpenAI スコアリング
    - regime_detector.py    — 市場レジーム判定（MA + LLM）
  - data/ (実行時に生成)
    - monitoring.db (SQLite)
    - paper_trading.db (paper mode)
    - kabusys.duckdb (DuckDB)
    - execution.pid, stop_requested.flag, kill.flag, ... 

---

## 開発・運用上の注意
- Paper Trading と Live は DB を分離している（PAPER_TRADING_SQLITE_PATH を使用）。
- 監視（Monitoring）は環境にかかわらず本番用 sqlite_path を参照してログを残します（監視と実行は独立運用を想定）。
- process_priority.set_process_priority() で起動時に優先度を上げようとしますが、権限により失敗する場合は警告を出してスキップします。
- OpenAI API 呼び出しはリトライやフォールバック（失敗時は safe デフォルト）を組み込んでいますが、API キーと利用上限に注意してください。
- DuckDB を使う分析系は SQL を直接実行する設計です。テーブルスキーマ（prices_daily, raw_financials, raw_news 等）に従ってデータを投入してください。
- 監視の kill switch / flag ファイルは明示的な停止操作・自動停止ルール（ドローダウンなど）で使用されます。flag の取り扱いに注意してください。

---

## 参考コマンドまとめ
- 依存インストール:
  pip install duckdb psutil requests openai streamlit
- Execution 起動:
  KABUSYS_ENV=paper_trading python src/kabusys/run_execution.py
- Monitoring 起動:
  python src/kabusys/run_monitoring.py
- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

もし README に追加したい具体的な例（.env.example、systemd ユニット例、Docker 化手順、テーブルスキーマ仕様など）があれば教えてください。必要に応じて追記します。