# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）。

このリポジトリは注文実行エンジン、監視（モニタリング）、ポートフォリオ構築、ファクター研究、ニュースNLP（OpenAI）連携などのコンポーネントを含む統合システムです。設計方針として「本番 DB と Paper Trading を明確に分離」「ルックアヘッドバイアスを避ける」「外部 API 失敗時はフェイルセーフで継続」を採用しています。

---

## 主な機能一覧

- ExecutionEngine（発注エンジン）
  - Broker クライアント抽象化（実口座 / Mock を切替可能）
  - OrderManager / Reconciler による注文状態管理・再同期
  - リスク管理（RiskManager）による最大ポジション比率・利用率などの制約

- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - TradeMonitor：滞留注文検出・約定異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch / AlertManager：閾値超過時の停止フラグ書き込み / LINE 通知
  - Monitoring DB（SQLite）への永続化（テーブル作成は冪等）

- Portfolio construction（銘柄選定・配分・サイズ計算）
  - 候補選定、等重/スコア重み、リスクベースのポジションサイズ計算
  - セクター上限適用、レジーム乗数（bull/neutral/bear）

- Research（研究用）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（ニュースNLP / レジーム判定）
  - raw_news を OpenAI（gpt-4o-mini 等）でセンチメント評価 → ai_scores に保存
  - ETF（1321）MA とマクロセンチメントを合成して market_regime 判定

- Tools
  - Paper Trading 検証レポート生成スクリプト（過去期間の稼働率や注文成功率、レイテンシなどを評価）
  - Streamlit ダッシュボード（監視データの可視化）

---

## 前提・依存ライブラリ（例）

必須（主にソースで明示されている）：
- Python 3.9+（型ヒント等を使用）
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)

インストール例：
- 仮想環境を作ってから：
  - pip install duckdb psutil requests openai streamlit

（実際の requirements.txt があればそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン／取得
   - git clone ...

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
     - KABU_API_PASSWORD — kabuステーション 接続パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
     - KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE — paper_trading 時の約定動作: instant | partial | never | reject
     - PAPER_TRADING_SQLITE_PATH — paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB データベース（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用
     - LOG_LEVEL — ログレベル（DEBUG, INFO...）

   - 例 .env（プロジェクトルート）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=paper_trading

5. データディレクトリの準備
   - data/ 以下に DB ファイルやフラグファイルが作られます。必要に応じて空ディレクトリを作成してください。
   - 実行時に自動作成されるファイル：
     - data/monitoring.db（監視ログ）
     - data/paper_trading.db（Paper Trading 用、KABUSYS_ENV=paper_trading 時に使用）
     - data/kabusys.duckdb（DuckDB）
     - data/execution.pid（ExecutionEngine の PID）
     - data/kill.flag / data/stop_requested.flag（停止制御用）

注意: 本番（live）で起動する前に、必ず設定とブローカー接続の確認を行ってください。

---

## 使い方（主要スクリプト / コマンド）

- 実行エンジンを起動（ExecutionEngine）
  - Python モジュールとして起動可能:
    - python -m kabusys.run_execution
  - 実行内容:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録して本番 DB と分離します。
    - 起動前に data/kill.flag が存在する場合は起動をスキップします。
    - 停止は data/stop_requested.flag を作成することで行えます（run_execution は定期的にこのフラグを監視し停止します）。

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き（デフォルト 60 秒）。0以下は無効。
  - Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用して監視ログを記録します。
  - 監視は system/trade/risk をチェックし、必要に応じて kill.flag を書き込み、LINE 通知を行います。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、ダッシュボード（Overview / Positions / Orders / System）を表示します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニュースセンチメント / レジーム判定）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、指定日分のニュースを OpenAI でスコア化して ai_scores テーブルへ書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 1321（ETF）の MA200 乖離とマクロセンチメントを合成して market_regime に書き込む
  - いずれも OPENAI_API_KEY を引数または環境変数で設定する必要があります。

停止／強制停止の仕組み:
- data/stop_requested.flag: run_monitoring / run_execution がポーリングで検知して安全停止します。
- data/kill.flag: KillSwitch が書き込み、ExecutionEngine 側で検出された場合に停止トリガーとして用いられます（Settings.kill_flag_path）。

---

## 監視 DB スキーマ（概要）

init_monitoring_db によって作成される主要テーブル：
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code PRIMARY KEY, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 で単一行保持: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

マイグレーション: init_monitoring_db は既存 DB に対してもカラム追加（例: peak_value, latency_ms）を行います（冪等）。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み、Settings クラス）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor を定期実行する起動スクリプト

  - execution/ — 発注関連
    - order_manager.py — 注文作成 / キャンセル等の外向 API
    - reconciler.py — 起動時リコンシリエーション（OrderSent 照合、ポジション差分）
    - order_repository.py — DB 層（OrdersDB として想定）
    - order_record.py — 注文レコード・状態遷移ロジック
    - broker_factory.py / broker_api.py — ブローカー/Mock 抽象化インタフェース
    - execution_engine.py — 実行エンジン本体
    - risk_manager.py — リスク管理ロジック

  - monitoring/ — 監視関連
    - monitoring_db.py — SQLite の永続化層（テーブル作成 / CRUD ユーティリティ）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — 停止フラグの書き込み・管理
    - alert_manager.py — LINE への通知（クールダウン機能付き）
    - monitoring_engine.py — 各 Monitor を束ねるポーリング実行
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

  - portfolio/ — ポートフォリオ構築
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 発注数量決定（単元丸め・aggregate cap 等）
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/ — 研究用ファクター
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

  - ai/ — OpenAI を用いる機能
    - news_nlp.py — ニュースを銘柄毎に集約して LLM でセンチメント評価、ai_scores へ書き込み
    - regime_detector.py — ETF MA とマクロセンチメントの合成によるレジーム判定

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 運用上の注意点

- 本番環境で運用する前に、必ず Paper Trading（KABUSYS_ENV=paper_trading）で十分な検証を行ってください。
- KABUSYS_ENV による DB 分離や Mock の有無に注意。paper_trading では paper_sqlite_path（既定: data/paper_trading.db）を使い本番 DB と分離します。
- OpenAI API を利用する機能は API キーと利用コストに注意してください（リトライ・バックオフ実装あり）。
- PID ファイル / フラグファイル（data/execution.pid / data/kill.flag / data/stop_requested.flag）を用いてプロセス管理・停止を行います。手動で削除する場合は安全性に配慮してください。
- monitoring は本番の sqlite_path を参照します。monitoring を別環境で動かす場合は SQLite のパス指定などに注意してください。

---

この README はコードベースの主要な目的と利用方法、構成をまとめたものです。詳細は各モジュールの docstring を参照してください。必要であればインストール用の requirements.txt、デプロイ手順、運用 runbook（サービス化 / systemd / supervisor 等）も追加できます。