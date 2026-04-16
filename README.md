# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ／運用スクリプト群）のREADME。

以下はこのリポジトリに含まれる主要機能、セットアップと起動方法、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な実行エンジン、監視（Monitoring）、ポートフォリオ構築・リスク調整、リサーチ用ファクター計算、LLM を使ったニュース NLP／レジーム検出などを提供するモジュール群です。  
このリポジトリは純粋関数／データアクセス層／運用スクリプトを分離した設計になっており、実運用（live）・模擬（paper_trading）・開発（development）環境を切り替えて利用できます。

主な特徴：
- ExecutionEngine 起動スクリプト（run_execution） — live / paper_trading を分離
- Monitoring（System / Trade / Risk）と Alert（LINE）通知
- Portfolio 構築（候補選定・重み付け・株数決定・セクター制限）
- Research（ファクター計算、IC 計算、特徴量探索）
- AI モジュール（ニュースセンチメント、レジーム判定） — OpenAI API を利用
- Streamlit ベースの監視ダッシュボード

---

## 機能一覧

- 実行（Execution）
  - 発注フローの管理（OrderManager、OrderRepository、Reconciler）
  - ブローカー抽象化（本番クライアント / MockBroker for paper_trading）
  - リスク管理（RiskManager）

- 監視（Monitoring）
  - SystemMonitor：CPU/Memory/Disk、プロセス生存、データ鮮度を監視
  - TradeMonitor：滞留注文・約定異常を検知
  - RiskMonitor：ドローダウン、ポジション上限を監視
  - KillSwitch：条件により停止フラグを発行（data/kill.flag）
  - AlertManager：LINE によるアラート送信
  - MonitoringEngine：各 Monitor を束ねてポーリング
  - Streamlit ダッシュボード（読み取り専用で監視情報を表示）

- ポートフォリオ（Portfolio）
  - シグナル選定、等配分／スコア加重、ポジションサイズ計算
  - セクター上限適用、レジーム乗数

- リサーチ（Research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン、IC、統計サマリー、ランク計算

- AI（LLM）
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に保存
  - regime_detector: ETF（1321）の MA とマクロニュースセンチメントを合成してレジーム判定

- ユーティリティ
  - 設定管理（kabusys.config: .env/.env.local 自動読み込み、環境変数アクセス）
  - プロセス優先度／CPU affinity 設定ユーティリティ（psutil 利用）

---

## セットアップ手順

1. Python 環境（3.9+ 推奨）を用意する。

2. 依存パッケージをインストール（例）:
   pip install psutil duckdb openai requests streamlit

   （プロジェクトに requirements.txt がある場合はそれを使ってください。ここでは主な依存を列挙しています）

3. ソース配置:
   - 開発中はリポジトリルートに `src/` がある前提で動作します。パッケージを実行する際は PYTHONPATH を設定するか、プロジェクトルートで `pip install -e src` 等してください。
   - 例（簡易）:
     export PYTHONPATH=./src

4. 環境変数 / .env:
   - 自動読み込み順序: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 重要な環境変数（代表例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定時は通知スキップ）
     - PAPER_FILL_MODE: instant | partial | never | reject （paper_trading の約定動作）
     - SQLITE_PATH: monitoring DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper 用 DB（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH: prices 等を保管する DuckDB（デフォルト: data/kabusys.duckdb）
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト: 60）

5. データディレクトリ:
   - デフォルトの SQLite / DuckDB パスは `data/` 以下にあります。必要に応じて `data/` を作成してください。起動時処理がテーブル作成（init_monitoring_db）を行います。

---

## 使い方（起動例）

前提: カレントディレクトリがリポジトリルートで、PYTHONPATH に src を含めるか editable install 済みであること。

1. Monitoring の起動（常駐ポーリング）
   - 環境変数 MONITOR_POLL_INTERVAL で秒間隔を指定可能（例: 30秒）
   - デフォルトでは監視は本番の sqlite_path を使用（KABUSYS_ENV に依らない）
   実行例:
   PYTHONPATH=./src python -m kabusys.run_monitoring
   もしくは
   export MONITOR_POLL_INTERVAL=30
   PYTHONPATH=./src python -m kabusys.run_monitoring

   stop:
   - プロジェクトの data/stop_requested.flag を作成するとループが検知して停止します。

2. ExecutionEngine の起動（実行エンジン）
   - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB (PAPER_TRADING_SQLITE_PATH) に書き込みます（本番 DB と完全分離）。
   実行例:
   PYTHONPATH=./src python -m kabusys.run_execution
   例（paper）:
   KABUSYS_ENV=paper_trading PYTHONPATH=./src python -m kabusys.run_execution

   stop:
   - data/stop_requested.flag を作成すると起動中のエンジンに停止シグナルが送られます。
   - KillSwitch により data/kill.flag が書き込まれると、運用側で停止などの対応が可能です。

3. Streamlit ダッシュボード（監視 UI）
   スタート例（デフォルト DB: data/monitoring.db）:
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4. Paper Trading 検証レポート生成
   コマンドライン:
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   DB 指定:
   python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5. AI モジュール（ニューススコア / レジーム判定）
   - OPENAI_API_KEY が必要です。関数は Python API として利用できます（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）。
   - DuckDB 接続を渡して実行し、内部で raw_news 等のテーブルを参照して書き込みを行います。

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（必須ではないが検証・挙動に影響）
  - paper_trading: MockBroker を使い paper_trading 用 DB に書き込む
  - live: 本番モード
- MONITOR_POLL_INTERVAL: 監視ループの秒（デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 外部 API 認証に必要
- SQLITE_PATH: 監視 DB（data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading DB（data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信用

---

## 運用上のファイル（フラグ / PID）

- data/stop_requested.flag: run_monitoring / run_execution がこのファイルの存在を検知して安全に停止します（外部から停止を要求する際に作成）。
- data/kill.flag: KillSwitch がリスクトリガー時に書き込むフラグ（Execution 停止要請の意図表示）。
- data/execution.pid: ExecutionEngine の PID ファイル（SystemMonitor がプロセス監視に使用）。

---

## ディレクトリ構成

以下はソース（src/kabusys）内の主要ファイル／パッケージと役割の概観です（抜粋）:

- kabusys/
  - __init__.py — パッケージ定義とバージョン
  - config.py — 環境変数 / .env の読み込みと Settings クラス
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py — ニュースセンチメント取得（OpenAI）
    - regime_detector.py — マクロ + MA ベースのレジーム判定

  - execution/
    - order_manager.py — 発注ステートマシン外向き API
    - reconciler.py — 起動時の同期・リコンシリエーション
    - (ブローカー関連、engine, repository 等を含む想定)

  - monitoring/
    - monitoring_db.py — SQLite DB スキーマと永続化 API（MonitoringDB）
    - system_monitor.py — システム監視（CPU/メモリ/ディスク、PID、データ鮮度）
    - trade_monitor.py — 注文滞留・約定異常検知
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 各 Monitor を束ねるランナー
    - streamlit_dashboard.py — 監視ダッシュボード（Streamlit）

  - portfolio/
    - portfolio_builder.py — 候補選定と重み計算
    - position_sizing.py — 株数決定・スケーリング処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリューの計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー

  - tools/
    - paper_verification_report.py — Paper Trading 用検証レポート CLI

  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ

  - monitoring/（上に同じ）および他の supporting modules

注: 上はこの README に含まれるファイル群の抜粋です。実際のリポジトリにはさらに細かいモジュール（broker, engine, data pipeline, order_repository 等）が存在します。

---

## 開発・デバッグのヒント

- Settings は .env/.env.local の自動読み込みを行います（プロジェクトルートの検出は .git または pyproject.toml を基準）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを止めてください。
- Monitoring の DB 初期化（テーブル作成・簡易マイグレーション）は init_monitoring_db により冪等に行われます。
- AI 呼び出し周りはリトライ・フェイルセーフ実装がありますが、API キー・ネットワークエラー時の挙動を事前に確認してください（ログを参照）。
- local 開発では KABUSYS_ENV=paper_trading を使うと本番 DB を汚さずに検証できます。

---

## よく使うコマンドまとめ

- Monitoring 起動:
  PYTHONPATH=./src python -m kabusys.run_monitoring

- Execution 起動（paper）:
  KABUSYS_ENV=paper_trading PYTHONPATH=./src python -m kabusys.run_execution

- Paper レポート:
  PYTHONPATH=./src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要であれば、README に追加すべき具体的な運用手順（例: systemd / supervisor 用の unit ファイル、ログローテーション、バックアップ手順）や、より詳細な環境変数一覧・.env.example を作成します。どの情報をさらに展開しましょうか？