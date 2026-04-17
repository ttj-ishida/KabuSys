# KabuSys

日本株自動売買システムの一部コードベース（ライブラリ / 実行スクリプト・監視・研究用ユーティリティ）。  
この README はリポジトリ内の主要機能、セットアップ、使い方、ディレクトリ構成を簡潔にまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したシステム群です。本リポジトリには以下の主要な責務が含まれます。

- Execution（発注エンジン）: ブローカークライアント経由で注文を発行・管理する ExecutionEngine 周りのコンポーネント
- Monitoring（監視）: システム稼働状況・注文の異常検知・リスク監視、監視ログの永続化・アラート送信（LINE）
- Portfolio（ポートフォリオ構築）: 銘柄候補選定、重み付け、ポジションサイズ計算、セクター制限などの純粋関数群
- Research（研究）: DuckDB を用いたファクター計算・将来リターン計算・IC 計算など
- AI 支援（news_nlp, regime_detector）: OpenAI を使ったニュースセンチメント評価や市場レジーム判定
- Tools: Paper Trading 検証レポート生成などのユーティリティスクリプト
- いくつかのユーティリティ（プロセス優先度設定、等）

設計上、DB（SQLite / DuckDB）はローカルファイルで保持され、paper_trading モードでは本番 DB と完全に分離されるよう配慮されています。

---

## 機能一覧（抜粋）

- Execution
  - 起動スクリプト: run_execution.py（KABUSYS_ENV に応じて本番 / paper_trading を切替）
  - Reconciler による再起動後の注文照合とポジション差分検出
  - OrderManager / OrderRepository による注文状態管理

- Monitoring
  - 監視用 DB スキーマの初期化（monitoring_db.init_monitoring_db）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス存在チェック / データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクイベント記録
  - KillSwitch: kill.flag による ExecutionEngine 停止シグナル生成
  - AlertManager: LINE Messaging API 経由での通知（クールダウン管理）
  - 監視ループ起動スクリプト: run_monitoring.py
  - Streamlit ダッシュボード: monitoring/streamlit_dashboard.py

- Portfolio
  - 銘柄選定・重み付け（等金額・スコア重み）
  - セクターキャップ適用
  - ポジションサイズ計算（単元・利用可能現金・リスク制約を考慮）

- Research / AI
  - DuckDB を使ったファクター計算（Momentum / Value / Volatility）
  - 将来リターン計算、IC 計算、統計サマリー
  - news_nlp: OpenAI によるニュースセンチメント取得（ai_scores への書き込み）
  - regime_detector: ma200 とマクロニュースの LLM 評価を合成して market_regime を更新

- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 要件（主な依存パッケージ）

- Python 3.10+ 推奨（型注釈に | を使用）
- duckdb
- psutil
- openai
- requests
- streamlit（ダッシュボードを使う場合）
- sqlite3（標準ライブラリ）

実行環境に合わせて適切にインストールしてください。簡易的には：

pip install duckdb psutil openai requests streamlit

また開発時は該当する pyproject / requirements を利用してインストールしてください（このリポジトリに requirements.txt が無い場合は上記パッケージ目安）。

---

## セットアップ手順

1. リポジトリルートで Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai requests streamlit

   （開発用に pip install -e . が使える場合はパッケージのインストールを検討してください）

3. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（既存の OS 環境変数は保護されます）。
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   主要な環境変数（抜粋）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な箇所あり）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知設定（任意）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。run_monitoring が参照、デフォルト 60）

4. データディレクトリの準備
   - data フォルダを作る（PID ファイル・フラグファイルの配置先）
   - 例: mkdir -p data

---

## 使い方（代表的なコマンド）

注意: スクリプトを実行する際は Python の import path が正しく設定されている必要があります。リポジトリルートで以下のいずれかを行ってください。

- 開発インストール:
  - pip install -e .

- または一時的に PYTHONPATH を通す:
  - PYTHONPATH=src python -m kabusys.run_monitoring

以下は代表的な実行例です。

- 監視ループ起動（SystemMonitor をポーリング）
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を上書きする例:
    - MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring

  run_monitoring の特徴:
  - 起動時にプロセス優先度を "high" に設定しようとします（失敗しても継続）。
  - 停止フラグ: data/stop_requested.flag を作成するとループを終了します。
  - 監視 DB は Settings.sqlite_path（環境にかかわらず本番 sqlite_path を使用）に接続します。

- ExecutionEngine 起動（発注エンジン）
  - PYTHONPATH=src python -m kabusys.run_execution
  - Paper Trading（擬似ブローカー）で起動:
    - KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution

  実行時の注意:
  - paper_trading モードでは MockBrokerClient を使い、別 DB（PAPER_TRADING_SQLITE_PATH）へ記録して本番 DB と分離されます。
  - 起動時に data/execution.pid に PID を書き、data/stop_requested.flag の存在で停止処理を行います。
  - kill.flag（Settings.kill_flag_path）により実行停止シグナルを送る仕組みもあります（KillSwitch）。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 起動時に監視 DB を read-only (URI with ?mode=ro) で開きます。MonitoringEngine が DB を更新していることが前提です。

- Paper Trading 検証レポート（コマンドライン）
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または指定 DB:
    - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 関連（プログラム内呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り、内部で OPENAI_API_KEY 環境変数または渡された api_key を使います。

---

## 設定/運用上のポイント

- 環境読み込み
  - config.py は .env/.env.local を自動的にプロジェクトルートから読み込みます（OS 環境変数が優先）。自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- 環境モード
  - KABUSYS_ENV は development / paper_trading / live のいずれか。paper_trading では本番 DB と分離した動作（PAPER_TRADING_SQLITE_PATH）になります。

- プロセス優先度
  - 実行スクリプトは起動時に set_process_priority("high") を呼びます。psutil による操作のため権限や OS によって設定できない場合は警告ログが出ます。

- 停止/キルフラグ
  - run_monitoring / run_execution はプロジェクト data ディレクトリ内の flag ファイル（stop_requested.flag, kill.flag, execution.pid 等）を用いて相互に停止・検知を行います。これらは手動で作成/削除できます。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等にテーブルを作成し、既存 DB に対して必要なカラム追加（簡易マイグレーション）も行います。

- Paper Trading の約定モード
  - PAPER_FILL_MODE = instant | partial | never | reject（設定ミスは例外）

---

## ディレクトリ構成（抜粋）

（リポジトリの src/kabusys 以下をベースにしています）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数と Settings 管理（.env 自動読み込み）
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - data/                        — データディレクトリ（実行時に作成するファイル: monitoring.db, paper_trading.db, execution.pid, stop_requested.flag, kill.flag など）

  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - execution_engine.py (想定) ...
    - broker_factory.py, broker_api.py ...

  - monitoring/
    - monitoring_db.py            — SQLite を使った永続層（テーブル定義・CRUD ラッパー）
    - system_monitor.py           — CPU/メモリ/ディスク/プロセス/データ鮮度チェック
    - trade_monitor.py            — 注文滞留・約定異常検出
    - risk_monitor.py             — ドローダウン/ポジション上限監視
    - kill_switch.py              — kill.flag 書き込みロジック
    - alert_manager.py            — LINE 通知
    - monitoring_engine.py        — 監視コンポーネントを束ねるループ
    - streamlit_dashboard.py      — Streamlit ダッシュボード

  - portfolio/
    - portfolio_builder.py        — 候補選定・重み付け
    - position_sizing.py          — 株数決定・スケール調整
    - risk_adjustment.py          — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py          — momentum/value/volatility 等のファクター計算（DuckDB）
    - feature_exploration.py      — 将来リターン・IC・統計サマリー
    - __init__.py

  - ai/
    - news_nlp.py                 — OpenAI を用いたニュースセンチメント（ai_scores挿入）
    - regime_detector.py          — ma200 + マクロニュース LLM 統合による市場レジーム判定

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力

  - utils/
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ

---

## 開発者向けメモ / トラブルシューティング

- モジュール実行時の import path
  - ルートで PYTHONPATH=src を設定するか、pip install -e . しておくと -m 実行や import が楽になります。

- DuckDB / SQLite の接続
  - DuckDB はファイルパスを渡して接続します。研究モジュールは prices_daily / raw_financials / raw_news 等のテーブルを前提とするため、事前にデータをロードしてください。

- OpenAI API のエラー
  - news_nlp と regime_detector は 429 / タイムアウト / 5xx をリトライしますが、API キー未設定は例外を投げます。テスト時は _call_openai_api をモックすると良いです。

- 監視ループを停止したい場合
  - data/stop_requested.flag を作成すると run_monitoring / run_execution はそれを検知して終了します。
  - KillSwitch により data/kill.flag が書き込まれると ExecutionEngine に停止シグナルとなります（evaluate 実行時）。

---

README は主要部分の概要を提供しています。各モジュールの詳細な使用法や API（関数シグネチャ、返却値、例外）はソースコードの docstring / type 注釈を参照してください。必要であれば各コンポーネントの個別ドキュメント（例: ExecutionEngine の起動オプション、OrderRepository スキーマ、DuckDB のテーブル仕様など）を追加で作成します。