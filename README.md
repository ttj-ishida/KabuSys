# KabuSys

日本株向け自動売買システムのライブラリ / 実行スクリプト群

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのコンポーネント群です。  
主な目的は以下の通りです：

- 取引エンジン（ExecutionEngine）による発注・注文管理・リスク管理
- 監視（MonitoringEngine）によるシステム安定性・注文滞留・ドローダウン監視
- ポートフォリオ構築・ポジションサイジングの純粋関数群
- 研究用／解析用モジュール（ファクター計算・特徴量探索）
- AI を使ったニュースセンチメント（OpenAI）を用いたスコアリングとレジーム判定
- Paper Trading（モックブローカー）用の分離された DB と検証ツール

設計方針としては、テスト可能・フェイルセーフ・ルックアヘッドバイアスの回避を重視しています。

---

## 主な機能一覧

- Monitoring
  - システムリソース（CPU / メモリ / ディスク）監視
  - Execution プロセス生存監視（PID ファイルチェック）
  - データ鮮度チェック（DuckDB の prices_daily を参照）
  - 注文滞留・約定異常の検出
  - ドローダウン・ポジション上限の検出と kill flag 発行
  - LINE によるアラート送信（AlertManager）

- Execution
  - ブローカー抽象化（実ブローカー / MockBroker）
  - OrderManager による注文状態管理
  - Reconciler による起動時の自動復旧（ブローカーとの突合）
  - RiskManager による発注制限（例: max_position_pct, utilization）

- Portfolio（純粋関数）
  - 候補選定、等金額・スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め・aggregate cap）

- Research
  - momentum / volatility / value ファクター計算（DuckDB 経由）
  - 将来リターン計算、IC 計算、統計サマリー

- AI
  - ニュース NLP（OpenAI）で銘柄別センチメントを ai_scores に書き込み
  - 市場レジーム判定（ETF MA200 とマクロニュースを合成）

- Tools
  - Paper Trading 検証レポート生成（tools.paper_verification_report）
  - Streamlit ベースの監視ダッシュボード（monitoring/streamlit_dashboard.py）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに | 演算子を使用）
- SQLite（標準ライブラリ）、DuckDB、外部パッケージが必要

推奨パッケージ（例）:
pip install duckdb psutil requests openai streamlit

（実際の要件一覧が別ファイルにある場合はそちらを参照してください）

1. リポジトリをクローン／取得
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate
3. 依存ライブラリをインストール
   - pip install duckdb psutil requests openai streamlit
4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（代表例）:
- KABUSYS_ENV: 起動環境（"development" | "paper_trading" | "live"。デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: "instant" | "partial" | "never" | "reject"（paper_trading の約定挙動）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）

注意:
- .env の読み込みは config モジュールがプロジェクトルートを自動検出して行います（.git または pyproject.toml が基準）。
- OS 環境変数は .env の上位優先で保護されます。

---

## 使い方

以下は主要なコマンド例です。プロジェクトルートで実行してください。

1) 監視ループ起動（Monitoring）
- デフォルトは本番用 SQLite（monitoring はどの KABUSYS_ENV でも本番 sqlite_path を使用します）
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）

実行例:
- python -m kabusys.run_monitoring

停止方法:
- プロジェクト内の data/stop_requested.flag を作成するとポーリングループが次回チェック時に終了します。

2) Execution エンジン起動（ExecutionEngine）
- KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 専用 DB に書き込みます（data/paper_trading.db）

実行例:
- python -m kabusys.run_execution

停止方法:
- data/stop_requested.flag を作成するとエンジンは安全に停止します。
- KillSwitch（監視側）により data/kill.flag が書き込まれると ExecutionEngine 側で停止処理が走ります（kill.flag は Settings.kill_flag_path で指定可能、デフォルト data/kill.flag）。

3) Paper Trading 検証レポート生成（ツール）
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション `--db PATH` で SQLite DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

4) 監視ダッシュボード（Streamlit）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ブラウザでダッシュボードを開き、ダッシュボード／ポジション／注文／システム状態を確認できます。
- DB を読み取り専用で開くため、MonitoringEngine が起動している必要があります。

5) AI 機能
- kabusys.ai.score_news(target_date) や kabusys.ai.regime_detector.score_regime(conn, date) を呼ぶと OpenAI を使った処理が実行されます。OPENAI_API_KEY が必要です。

---

## 注意事項 / 運用メモ

- Paper Trading:
  - KABUSYS_ENV=paper_trading にすると paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。本番 DB と完全に分離されます。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼びます（psutil を使用）。権限がない場合は警告ログが出ますが続行します。
- DB スキーマ:
  - monitoring.monitoring_db.init_monitoring_db() により必要なテーブルは起動時に冪等で作成されます。古い DB に対しては軽微なマイグレーション（カラム追加）を行います。
- Kill / Stop フラグ:
  - data/stop_requested.flag: run_monitoring / run_execution が監視している「停止」フラグ（手動で作成/削除して操作）
  - data/kill.flag: KillSwitch が自動で作成する停止シグナル（ExecutionEngine の外部強制停止トリガ）
- ログ:
  - 起動スクリプトは logging.basicConfig(level=logging.INFO) を使います。LOG_LEVEL 環境変数でレベルを変更可（Settings.log_level）。
- テスト方法:
  - MonitoringEngine.run_once() を使えば単体テストで各 Monitor を一度だけ実行できます（ユニットテスト向け）。

---

## ディレクトリ構成（要約）

（repo の src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み）
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポートツール
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py       — 市場レジーム判定（MA200 + マクロ NLP）
  - monitoring/
    - __init__.py
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - alert_manager.py        — LINE Push 通知
    - monitoring_engine.py    — 各 Monitor を束ねる
    - streamlit_dashboard.py  — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他ブローカー/エンジン関連ファイルが存在）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - monitoring/ (上記)

- data/  — 実行時に生成・参照するファイル群（監視 DB / duckdb / pid / flag 等）
  - monitoring.db (デフォルト)
  - kabusys.duckdb (デフォルト)
  - execution.pid
  - stop_requested.flag
  - kill.flag
  - paper_trading.db

（上記は主要ファイルのみ抜粋。実際のリポジトリで詳細を確認してください。）

---

## よくある操作例

- 環境変数を .env に設定して監視起動
  - .env:
    - KABUSYS_ENV=live
    - JQUANTS_REFRESH_TOKEN=...
    - KABU_API_PASSWORD=...
    - OPENAI_API_KEY=...
  - 起動:
    - python -m kabusys.run_monitoring

- Paper Trading で Execution を起動（モックブローカーを使う）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- 強制停止（監視からの停止要求でエンジンを止めたい場合）
  - 監視から KillSwitch が data/kill.flag を書く
  - 手動で停止したい場合は data/stop_requested.flag を作成

---

README に記載のない詳細（実装上の仕様や追加のコマンド等）はソースコード内の docstring／コメントを参照してください。必要であれば導入スクリプト（requirements.txt / setup.py）や実運用手順のテンプレートも作成できます。要望があれば教えてください。