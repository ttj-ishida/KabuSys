# KabuSys

KabuSys は日本株の自動売買・監視・リサーチを支援する軽量ライブラリ兼実行フレームワークです。本リポジトリには取引実行（ExecutionEngine）周りのコンポーネント、監視（Monitoring）ツール、ポートフォリオ構築・サイズ算出ロジック、ファクター計算やリサーチ用ユーティリティ、及び OpenAI を用いたニュース NLP / レジーム判定などが含まれます。

対象 Python バージョン: 3.10+

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 環境変数（主な設定）
- 使い方（コマンド例）
- 監視 DB スキーマ（概要）
- ディレクトリ構成
- 注意事項

---

## プロジェクト概要

KabuSys は次のような関心事を分離して実装しています。

- 注文の作成 / 送信 / 同期を担う Execution コンポーネント
- システム状態（CPU/メモリ/ディスク/プロセス）や注文状態を定期的に記録・アラートする Monitoring コンポーネント
- ポートフォリオ候補選定・重み付け・株数決定などの Portfolio 構築ロジック（純粋関数）
- DuckDB を用いたファクター計算・リサーチ（価格・財務データを参照）
- OpenAI を利用したニュースセンチメント評価（ai.news_nlp）や市場レジーム判定（ai.regime_detector）
- Paper Trading 用の分離された SQLite DB と検証レポート生成ツール

設計方針としては「副作用を最小化した純粋関数」「DB 書き込みは冪等化」「ルックアヘッドバイアス回避（date.today()直接参照を避ける）」などが採用されています。

---

## 機能一覧

主な機能:

- Execution
  - OrderManager / Reconciler による注文ライフサイクル管理と再同期
  - paper_trading モードでの MockBroker を利用した分離実行
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態・データ鮮度検査
  - TradeMonitor: 注文滞留・約定価格異常検出
  - RiskMonitor: ドローダウン / ポジション上限監視、kill.flag による停止シグナル発行
  - AlertManager: LINE Push による通知（クールダウン制御）
  - Streamlit ダッシュボード（監視ダッシュボード）
  - MonitoringEngine によるポーリング統合
- Portfolio
  - 候補選定（score / rank）
  - 等配分 / スコア重み / リスクベースの株数算出
  - セクターキャップ・レジーム乗数適用
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計測、統計サマリ
- AI
  - ニュースを LLM（OpenAI）でセンチメントスコア化し ai_scores に書き込み
  - レジーム判定（ETF の MA200 乖離 + マクロニュースセンチメント）
- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 前提条件

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- OS: Linux / macOS / Windows（プロセス優先度設定はプラットフォーム差に依存）

※ requirements.txt は同梱されていないため、上記パッケージを適宜インストールしてください。

例:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要ライブラリをインストール
   - pip install duckdb psutil requests openai streamlit

3. データディレクトリ準備
   - デフォルトの SQLite / DuckDB のパスは data/ 以下を想定しています:
     - data/monitoring.db（監視ログ）
     - data/kabusys.duckdb（時系列・財務データ等）
     - data/paper_trading.db（paper_trading モード用）
   - 必要ならディレクトリを作成:
     - mkdir -p data

4. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（config.py が自動で読み込みます）。
   - 自動読み込みを無効化するには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必要な環境変数を設定（下記「環境変数」を参照）

---

## 環境変数（主な設定）

Settings クラス (kabusys.config.Settings) で使用する主な環境変数:

- 基本・認証
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
  - OPENAI_API_KEY — OpenAI API キー（ai 機能で必須）
- 実行環境
  - KABUSYS_ENV — one of: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、Execution は paper DB を使用し MockBrokerClient を想定
- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — 実行エンジンの PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill flag（デフォルト: data/kill.flag）
- Paper Trading
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）
- ログ / アラート
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（未設定時は通知スキップ）
- Monitoring
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）
- その他
  - KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を消す場合に 1 に設定

推奨の .env（例）:
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

---

## 使い方（コマンド例）

ルートから実行することを想定しています（パッケージとしてモジュール実行）。

- 監視ループを開始（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）。
  - 実行時にプロセス優先度を "high" に設定しようとします（システム権限に依存）。

- ExecutionEngine を起動（注文実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper DB（PAPER_TRADING_SQLITE_PATH）を使用し MockBroker を使います。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine を先に起動してデータを記録してください。

- AI（プログラムから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらはライブラリ API です。必要な DuckDB 接続と OpenAI API キーを渡して利用します。

- テスト的に各コンポーネントを使う（ライブラリとして）
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns

---

## 監視 DB スキーマ（monitoring_db.init_monitoring_db による自動作成）

init_monitoring_db(conn) は以下のテーブルを冪等的に作成します:

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard
  - id=1 の単一行に集計（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

マイグレーション用の安全策（既存列チェック・ALTER TABLE の実行等）も組み込まれています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env 自動読み込みロジック
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースの LLM センチメント評価
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite 永続化レイヤ
  - system_monitor.py — システム監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 発行/管理
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各 Monitor を統合
  - streamlit_dashboard.py — ダッシュボード
- execution/
  - reconciler.py — 起動時リコンシリエーション
  - order_manager.py — 注文作成 / 送信管理
  - ...（ブローカー関連、注文リポジトリ等）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数算出ロジック
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value 計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート

（上記は主要ファイルの抜粋です。プロジェクト全体は src/kabusys 以下にまとまっています）

---

## 注意事項 / 運用メモ

- KABUSYS_ENV によって実行挙動が変わります。paper_trading は本番 DB と分離されます。live は本番運用想定です。development はローカル向け。
- Settings はプロジェクトルート（.git または pyproject.toml を探索）にある .env / .env.local を自動ロードします。OS 環境変数は保護されます。
- psutil を使ったプロセス優先度設定や CPU affinity の変更は権限に依存します。権限が不足する場合は警告を出してスキップします。
- OpenAI API を利用する機能は API 使用制限・コストが発生します。エラー時は安全側のフォールバック（スコア 0.0 等）を採りますが、運用上の考慮が必要です。
- kill.flag が書き込まれると ExecutionEngine に停止シグナルを送る設計です。必要に応じて KILL_FLAG_CLEAR_ON_START を使って起動時にフラグをクリアできます。
- monitoring のポーリングループは例外耐性を持ちますが、致命的なエラーが続く場合はログを確認してください。
- DuckDB / SQLite ファイルは運用上バックアップやローテーションを検討してください。

---

質問や追加してほしいドキュメント（例: API リファレンス、設計資料、運用手順書）があれば教えてください。README に追記して整備します。