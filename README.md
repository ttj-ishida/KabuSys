# KabuSys

KabuSys は日本株向けの自動売買システム（リサーチ・ポートフォリオ構築・発注・監視・AI ニュース解析を含む）を想定した Python コードベースです。本 README はコードベース（src/kabusys 以下）を前提に、概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の機能を備えた自動売買プラットフォームのコンポーネント群です。

- リサーチ（ファクター計算、特徴量解析、将来リターン計算）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限・レジーム調整）
- 発注実行（OrderManager / ExecutionEngine、ブローカーファクトリ）
- 起動時リコンシリエーション（Reconciler）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine、LINE 通知）
- AI ベースのニュース解析（OpenAI を用いたニュースセンチメント）とレジーム判定
- Paper Trading 用検証用ツール（検証レポート生成）
- 監視ダッシュボード（Streamlit）

設計方針の一部：
- DuckDB / SQLite をデータストアとして利用（DuckDB は時系列ファクター計算、SQLite は監視ログ／注文ログ等）
- 外部 API 呼び出し（ブローカー / OpenAI 等）は抽象化してフェイルセーフに動作
- 多くのモジュールは副作用を持たない純粋関数群で構成

---

## 主な機能一覧

- Research
  - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily/raw_financials を用いたファクター計算
  - calc_forward_returns, calc_ic, factor_summary: 特徴量探索・IC 計算等

- Portfolio
  - 銘柄選定（select_candidates）
  - 重み付け（等金額、スコア加重）
  - ポジションサイズ計算（リスクベース、重みベース）
  - セクター制限、レジーム乗数

- Execution
  - OrderManager（発注フロー、重複防止、DB 永続化）
  - Reconciler（起動時リコンシリエーション）

- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク/データ鮮度/プロセス生存チェック）
  - TradeMonitor（滞留注文・約定価格異常検出）
  - RiskMonitor（ドローダウン・ポジション数監視）
  - MonitoringDB（SQLite スキーマ初期化・ログ永続化）
  - KillSwitch（条件で ExecutionEngine 停止フラグを書き込み）
  - AlertManager（LINE Push 通知）
  - MonitoringEngine（上記を束ねるポーリング実行）

- AI
  - news_nlp.score_news: OpenAI を使ったニュースセンチメントを ai_scores に書込
  - regime_detector.score_regime: ETF の MA とマクロニュースで市場レジーム判定（market_regime テーブルへ書き込み）

- Tools
  - paper_verification_report: Paper Trading の検証レポート生成 CLI
  - streamlit_dashboard: Streamlit ベースの監視ダッシュボード

---

## 要件（推奨）

- Python 3.9+（コードは modern typing を使っているため 3.9 以上を推奨）
- 必要な Python パッケージ（以下参照）
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボードを使う場合)
  - openai (AI 機能を使う場合)
  - 他: sqlite3 は標準ライブラリ
- ネットワークアクセス（ブローカー API / OpenAI を利用する場合）

例（pip インストール）:
pip install duckdb psutil requests streamlit openai

※ 実際の requirements.txt があればそれを使用してください。

---

## セットアップ手順

1. リポジトリをクローン／取得
2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   pip install duckdb psutil requests streamlit openai

4. データディレクトリ作成（デフォルトパス）
   mkdir -p data

5. 環境変数設定
   プロジェクトルートに .env（および必要であれば .env.local）を置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主要な環境変数（Settings で参照されるもの）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能で必須)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知に使用)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — 監視用 DB
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading モード専用 DB
- PAPER_FILL_MODE (instant|partial|never|reject, デフォルト: instant)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (1 で起動時に kill.flag をクリア)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒、デフォルト 60)

例 .env（最低限の例）
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development

---

## 使い方

以下は代表的な実行方法例です。

- 監視ループの起動（モニタリング）
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト: 60）
  - run_monitoring は Monitoring 用 SQLite（Settings.sqlite_path）を常に使用します（KABUSYS_ENV に関係なく）

- ExecutionEngine（発注エンジン）の起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
  - 起動時にプロセス優先度を「high」に設定しようと試みます（権限がない場合は警告でスキップ）

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを上書きできます（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- Streamlit ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視用 SQLite を read-only で開き、Positions / Orders / System / Overview を表示します

- AI 機能（プログラム的に呼ぶ例）
  from kabusys.ai.news_nlp import score_news
  # DuckDB 接続を作成して score_news(conn, target_date, api_key=...)
  # または
  from kabusys.ai.regime_detector import score_regime
  # score_regime(conn, target_date, api_key=...)

- その他のユーティリティ
  - MonitoringDB.init_monitoring_db は DB スキーマ作成（冪等）を行います。run_monitoring / run_execution 内で自動的に呼ばれます。

注意点・挙動
- run_monitoring はモニタリング用 SQLite パス（Settings.sqlite_path）を使用します。paper_trading でも監視は本番 DB を参照する設計です。
- run_execution は KABUSYS_ENV によって paper_trading 用 DB（Settings.paper_sqlite_path）を使うか本番（Settings.sqlite_path）を使うかが切り替わります。
- KillSwitch は条件が満たされると KILL_FLAG_PATH（デフォルト data/kill.flag）に理由を書き込みます。ExecutionEngine はこのファイル存在を検知して安全停止する想定です。
- LINE 通知は AlertManager を通じて行われます。トークン／ユーザー ID が空の場合は送信は行われずログのみ出力されます。
- OpenAI 呼び出しにはレート制限やネットワーク障害に対するリトライ（指数バックオフ）が実装されていますが、API キーは必須です。

---

## 開発・テストに関するメモ

- .env ファイルの自動読み込みルール:
  - OS 環境変数 > .env.local > .env の順で読み込み
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化可能
  - プロジェクトルートは .git または pyproject.toml がある親ディレクトリで探索

- process priority / CPU affinity:
  - psutil を使って Windows/Linux/Mac の差分を吸収
  - 一部操作（低 nice 値の設定など）は権限が必要な場合があり失敗時は警告でスキップされます

- DB マイグレーション:
  - init_monitoring_db は必要なテーブルとインデックスを作成します
  - 既存 DB にないカラム（例: peak_value, latency_ms）を追加する簡易マイグレーションが含まれます

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py                        — 環境変数 / Settings 管理
- run_monitoring.py                — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                 — ExecutionEngine 起動スクリプト

src/kabusys/ai/
- news_nlp.py                      — ニュースの OpenAI によるセンチメント解析
- regime_detector.py               — マーケットレジーム判定（MA200 + マクロニュース）

src/kabusys/data/                   — （DuckDB 用テーブルアクセス等を想定）
- pipeline.py (参照されるモジュールが存在)

src/kabusys/research/
- factor_research.py               — モメンタム / ボラティリティ / バリュー等のファクター計算
- feature_exploration.py           — 将来リターン・IC・統計サマリー等

src/kabusys/portfolio/
- portfolio_builder.py             — 候補選定・重み付け
- position_sizing.py               — 株数計算・スケールダウンロジック
- risk_adjustment.py               — セクターキャップ・レジーム乗数

src/kabusys/execution/
- order_manager.py                 — 発注ワークフロー（OrderManager）
- reconciler.py                    — 起動時リコンシリエーション
- (他: broker_factory, execution_engine, order_repository, order_record 等が存在)

src/kabusys/monitoring/
- monitoring_db.py                 — SQLite スキーマ & MonitoringDB 操作
- system_monitor.py                — システム状態・データ鮮度監視
- trade_monitor.py                 — 注文滞留 / 約定異常監視
- risk_monitor.py                  — ドローダウン / 保有数監視
- kill_switch.py                   — kill.flag 管理
- alert_manager.py                 — LINE 通知
- monitoring_engine.py             — 各 Monitor を束ねるエンジン
- streamlit_dashboard.py           — Streamlit ダッシュボード

src/kabusys/tools/
- paper_verification_report.py     — Paper Trading 検証レポート生成 CLI

src/kabusys/utils/
- process_priority.py              — プロセス優先度 / CPU affinity ユーティリティ

---

## 参考コマンド集

- 監視を起動（デフォルト interval=60s）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution を起動（paper_trading モードで起動する例）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## ライセンス／注意事項

- このコードベースは学習用／サンプル用の設計を含むため、本番運用時は十分なテスト・法令遵守・リスク管理を行ってください。
- ブローカー API 呼び出しや実資金の運用は各自責任で行ってください。
- OpenAI API キーやブローカーの資格情報は安全に管理してください。

---

不明点や追加したい情報（例: 実際の ExecutionEngine の起動オプション、テストコマンド、CI 設定など）があれば教えてください。README に追記します。