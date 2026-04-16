KabuSys
======

日本株自動売買システムのモノリポジトリ（ライブラリ＋実行スクリプト群）。  
このリポジトリは戦略の研究用ユーティリティ、ポートフォリオ構築、発注実行エンジン、監視・アラート基盤、AI を用いたニュース解析などのコンポーネントで構成されています。

概要
---
KabuSys は以下のような目的で設計された自動売買基盤です。

- DuckDB / SQLite を用いた時系列データ・ログ永続化
- ポートフォリオ構築（候補選定・重み付け・単元丸め・リスク調整）
- ExecutionEngine によるブローカー接続・発注管理（本番／ペーパートレード切替）
- 起動時のリコンシリエーション（再起動後の整合性復旧）
- 監視基盤（System/Trade/Risk モニタ）とアラート（LINE 送信）
- AI（OpenAI）を利用したニュースセンチメント評価・市場レジーム判定
- Paper Trading 用検証レポート生成ツール
- Streamlit による監視ダッシュボード

主な機能一覧
---
- 環境設定管理（.env 自動読み込み、Settings クラス）
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し DB を分離
  - 停止フラグ / PID 管理（data/execution.pid, data/stop_requested.flag）
- 監視ループ起動スクリプト（run_monitoring.py）
  - モニタリング用 SQLite を用いた監視ログ永続化
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）
  - 監視は環境にかかわらず本番用 sqlite_path を参照
- Monitoring コンポーネント群
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常価格検出
  - RiskMonitor: ドローダウン・保有上限監視（KillSwitch 連携）
  - AlertManager: LINE Push による通知（クールダウン管理）
  - MonitoringDB: 監視ログ用テーブル/インデックス作成・読み書き
  - Streamlit ダッシュボード（監視データ表示）
- Execution コンポーネント群
  - OrderManager / OrderRepository / Reconciler / RiskManager 等
  - 発注状態管理と再整合化ロジック
- Portfolio モジュール（純粋関数）
  - 候補選定・等重 / スコア重み・リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元丸め・aggregate cap）
- Research モジュール
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns / IC / summary）
- AI モジュール
  - news_nlp: raw_news を OpenAI でスコアリングして ai_scores に書込
  - regime_detector: ma200 とマクロニュースの LLM スコアを合成して market_regime を判定
- ユーティリティ
  - process_priority: プラットフォーム差分を吸収してプロセス優先度 / CPU affinity を設定

セットアップ手順
---
前提
- Python 3.9+ を推奨（duckdb, psutil, requests, openai, streamlit 等との互換性を確認してください）
- OS: Linux / macOS / Windows（psutil の動作は OS に依存する処理あり）

依存パッケージ（例）
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを使う場合)
- その他（必要に応じて）: sqlite3 は標準モジュール

インストール（例: venv を利用）
1. 仮想環境作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # (Windows: .venv\Scripts\Activate)

2. 依存パッケージをインストール
   pip install duckdb psutil requests openai streamlit

環境変数 / .env
- プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（既存の OS 環境変数は保護）。
- 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）デフォルト "instant"
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視ログ用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 用（未設定なら送信スキップ）
- LOG_LEVEL: ログレベル（DEBUG|INFO|...）

初期データディレクトリ
- data/ 以下に DB や PID / フラグファイルが作成されます。デフォルトパスは Settings クラスで定義されています。

使い方（実行例）
---
監視ループを起動
- 環境変数を設定したうえで:
  python -m kabusys.run_monitoring
- ポーリング間隔を変更したい場合:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ※ 1 未満や 0 は無効でデフォルト（60 秒）にフォールバックします。

ExecutionEngine を起動
- 本番（KABUSYS_ENV=live）または開発（default development）:
  python -m kabusys.run_execution
- ペーパートレード（MockBroker / 分離DB）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH の DB に全発注ログが残ります（本番 DB と分離）。

停止 / フラグ
- run_monitoring.py / run_execution.py はプロジェクトルート data/stop_requested.flag を検知して安全に停止します。
- KillSwitch は data/kill.flag を書き込んで ExecutionEngine を停止するために使用します（監視ロジック内で評価されます）。
- PID ファイル: data/execution.pid

Paper Trading 検証レポート
- 単体ツールとして実行可能:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- データベース指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

Streamlit ダッシュボード
- 起動:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードは読み取り専用で監視 DB に接続します（存在しない場合はエラー表示）。

ライブラリ利用（研究 / バックテスト等）
- research パッケージからファクター計算関数を呼べます（DuckDB 接続を渡す設計）。
  例: from kabusys.research import calc_momentum, calc_volatility, calc_value

- portfolio パッケージは純粋関数群であり、単体テストが容易です。
  例: from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

注意事項 / 実装上のポイント
---
- Settings は .env / .env.local / OS 環境変数を読み込みます。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視用 SQLite を環境にかかわらず Settings.sqlite_path（本番パス）で開きます。run_execution は KABUSYS_ENV によって paper_trading 用 DB を使い分けます。
- process_priority ユーティリティで起動直後にプロセス優先度を "high" に変更しています。OS によっては権限不足で設定できない場合があります（警告ログのみ）。
- AI 周り（news_nlp, regime_detector）は OpenAI API 呼び出しを含むため、API キー・コスト管理に注意してください。エラー時は安全側のフォールバックを行う実装です（例: macro_sentiment=0.0）。
- MonitoringDB.init_monitoring_db は冪等であり、既存 DB に必要なカラムがない場合に簡単なマイグレーションを行います。

ディレクトリ構成
---
（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py                    — 環境設定管理（Settings）
- run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py             — ExecutionEngine 起動スクリプト

src/kabusys/ai/
- news_nlp.py                  — ニュース NLP（OpenAI）スコアリング
- regime_detector.py           — 市場レジーム判定（ma200 + LLM）

src/kabusys/monitoring/
- monitoring_db.py             — SQLite 永続化層（監視ログ）
- system_monitor.py            — システム・データ鮮度監視
- trade_monitor.py             — 注文滞留・約定異常検知
- risk_monitor.py              — ドローダウン・ポジション上限監視
- kill_switch.py               — kill.flag 書込みユーティリティ
- alert_manager.py             — LINE Push 通知
- monitoring_engine.py         — 各 Monitor を束ねるエンジン
- streamlit_dashboard.py       — Streamlit ダッシュボード

src/kabusys/execution/
- order_manager.py             — 発注管理（OrderManager）
- reconciler.py                — 再起動時のリコンシリエーション
- (その他)                     — broker_factory, execution_engine, order_repository 等

src/kabusys/portfolio/
- portfolio_builder.py         — 候補選定 / 重み計算
- risk_adjustment.py           — セクターキャップ / レジーム乗数
- position_sizing.py           — 株数決定・aggregate cap

src/kabusys/research/
- factor_research.py           — モメンタム/ボラティリティ/バリュー計算
- feature_exploration.py       — IC / forward returns / summary

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成ツール

src/kabusys/utils/
- process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ

data/
- monitoring.db (デフォルト)
- paper_trading.db (PAPER_TRADING_SQLITE_PATH デフォルト)
- kabusys.duckdb (DUCKDB_PATH デフォルト)
- execution.pid, stop_requested.flag, kill.flag

貢献 / 開発メモ
---
- pure 関数群（portfolio/*, research/*）はユニットテストを書きやすい設計です。まずそちらからカバレッジを増やすことを推奨します。
- 環境依存の処理（プロセス優先度、psutil、OpenAI 呼び出し）はモックしやすいように設計されています（テスト時はモック推奨）。
- .env.example を用意し、必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）について README に追記すると導入が容易になります。

以上。必要であれば README に .env.example のテンプレートや起動手順の具体的なサンプル（systemd ユニット / Docker Compose 例）を追記します。どの情報を追加しますか？