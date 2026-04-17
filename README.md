# KabuSys

KabuSys は日本株の自動売買システムの一部を構成する Python モジュール群です。本リポジトリには、実行エンジン / 監視（Monitoring） / ポートフォリオ構築 / リサーチ / AI ニュース処理などのコンポーネントが含まれます。

以下はこのコードベースの概要・セットアップ・使い方・ディレクトリ構成の説明です。

---

## プロジェクト概要

- 目的: 日本株の自動売買ワークフロー（シグナル生成 → 発注 → モニタリング → リスク制御）をサポートするライブラリ／実行スクリプト群。
- 主要コンポーネント:
  - ExecutionEngine: ブローカーとのインタラクション（発注・状態管理・リコンシリエーション）
  - Monitoring: システム稼働・データ鮮度・注文異常・ドローダウン等の継続監視、LINE 通知、kill switch（停止フラグ）
  - Portfolio: 候補選択、重み付け、ポジションサイズ計算、セクター制限
  - Research: ファクター計算（モメンタム/バリュー/ボラティリティ）や特徴量解析（IC 等）
  - AI: ニュースの NLP スコアリング（OpenAI）と市場レジーム判定
  - Tools: 検証レポート生成、Streamlit ベースの監視ダッシュボード

---

## 主な機能一覧

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / Execution プロセス生存チェック / データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常の検出とリスクログ記録
  - RiskMonitor: ドローダウン・保有上限の監視、dashboard テーブル更新、リスクイベントの記録
  - MonitoringEngine: 上記監視をまとめてポーリング実行、アラート発行、kill switch 評価
  - AlertManager: LINE Messaging API で通知（クールダウン制御あり）
  - kill_switch: `data/kill.flag` を作成して ExecutionEngine に停止指示を出す
  - Streamlit ダッシュボード（read-only）: monitoring.db を参照して現状表示

- 実行（Execution）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager / OrderRepository / Reconciler による注文管理と起動時リコンシリエーション
  - Paper Trading モード: 環境変数 `KABUSYS_ENV=paper_trading` で MockBroker を使用し、paper_trading 用 DB に完全分離して記録

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等比率 / スコア加重 / リスクベース配分（weights, calc_position_sizes）
  - セクターキャップ適用、レジーム乗数

- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Spearman rank）計算、統計サマリー

- AI / NLP
  - news_nlp.score_news: raw_news を OpenAI で評価し ai_scores に書き込み
  - regime_detector.score_regime: ETF MA200 と LLM マクロセンチメントを合成して市場レジームを判定

- ツール
  - paper_verification_report: Paper Trading DB を解析して検証レポートを出力

---

## セットアップ手順

1. Python 仮想環境作成（推奨）
   - python 3.9+ を想定（利用するライブラリに依存）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージインストール
   - 必要な主なパッケージ:
     - duckdb, psutil, openai, requests, streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt があればそちらを利用してください）

3. リポジトリルートに data ディレクトリを準備
   - 例:
     - mkdir -p data

4. 環境変数設定 (.env)
   - プロジェクトは自動で `.env` / `.env.local` をロードします（OS 環境変数が優先）。
   - 自動ロードを無効にするには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須（使用コンポーネントに依存）例:
     - JQUANTS_REFRESH_TOKEN=<...>
     - KABU_API_PASSWORD=<...>
   - よく使うオプション（例）:
     - OPENAI_API_KEY=<your_openai_api_key>
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - LOG_LEVEL=INFO
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
   - .env のパースは `kabusys.config` の実装に従います。`.env.local` は `.env` の上書きとして扱われます。

5. DB 初期化
   - Monitoring 用 SQLite (デフォルト: data/monitoring.db) と DuckDB (data/kabusys.duckdb) は各スクリプトが起動時に必要なテーブルを作成します。
   - 例: 監視プロセス起動で自動作成されます。

---

## 使い方

- 監視ループ（SystemMonitor 単体起動）
  - パッケージ経由で起動:
    - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - export MONITOR_POLL_INTERVAL=30
  - 停止: プロジェクトルートの `data/stop_requested.flag` を作成すると監視ループが検知して停止します。

- 実行エンジン起動
  - python -m kabusys.run_execution
  - `KABUSYS_ENV=paper_trading` の場合、MockBroker を使用し DB は `data/paper_trading.db`（または PAPER_TRADING_SQLITE_PATH）に保存され、本番 DB とは分離されます。
  - 停止:
    - `data/stop_requested.flag` を作成すると、エンジンはフラグを検知して安全に停止します。
    - kill switch により `data/kill.flag` が生成されるとエンジンへ停止シグナルを送る運用が可能です。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - `--db` オプションで DB パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH でも可）。

- Streamlit ダッシュボード（監視用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System を表示します。

- AI 関連
  - ニュース NLP スコアリング:
    - モジュール呼び出し例: from kabusys.ai.news_nlp import score_news
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY に設定してください。
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime

- ログレベル
  - 環境変数 `LOG_LEVEL` でログレベルを制御できます（DEBUG/INFO/...）。

- プロセス優先度
  - 起動スクリプトは最初にプロセス優先度を "high" に設定しようとします（psutil を利用）。権限不足の場合は警告が出ます。

---

## 重要なファイル / フラグ

- data/execution.pid — ExecutionEngine が書き込む PID ファイル（SystemMonitor はこの PID を使ってプロセス生存をチェック）
- data/stop_requested.flag — 手動で作成すると run_execution/run_monitoring のループを停止させるために使用
- data/kill.flag — KillSwitch によって書き込まれる（条件を満たすと ExecutionEngine の停止トリガーとして使われる）
- DB:
  - data/monitoring.db — 監視ログ（SQLite）
  - data/paper_trading.db — Paper Trading 用 SQLite（KABUSYS_ENV=paper_trading）
  - data/kabusys.duckdb — DuckDB データ倉庫（価格・財務データ等）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                     — 環境変数 / .env ロード・Settings
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
- run_execution.py              — ExecutionEngine 起動スクリプト
- utils/
  - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/
  - __init__.py
  - monitoring_db.py            — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - (その他: broker_factory, execution_engine, order_repository, ...)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py
- tools/
  - paper_verification_report.py
  - __init__.py

（上記は主要ファイルの抜粋です。実際のファイルはさらに多くのサブモジュールを含みます。）

---

## 運用上の注意点

- 環境（KABUSYS_ENV）
  - development / paper_trading / live のいずれかを指定します。値が不正だと例外になります。
  - paper_trading モードではブローカーアクセスはモックされ、本番 DB に影響しない別 DB を使います。

- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` / `.env.local` を自動ロードします。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI API
  - news_nlp / regime_detector は OpenAI を使用します。API 呼び出しに失敗した場合はフェイルセーフ（スコア 0 など）で継続する実装になっていますが、利用には OPENAI_API_KEY が必要です。
  - API 呼び出しはリトライ制御やレスポンス検証を行っていますが、実行前にキーと課金状態を確認してください。

- データ鮮度チェック
  - SystemMonitor は DuckDB の prices_daily テーブルに基づいてデータ鮮度を判定します。テーブルが存在しない／データが不足しているとデータ鮮度判定は失敗します。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は既存 DB にカラム追加（例: peak_value、latency_ms）を行います。互換性のため冪等に実行されます。

---

## よく使うコマンド集（例）

- 監視を起動（デフォルト 60 秒ポーリング）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行エンジンを起動（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

README の内容はコード内の docstring / コメントに基づいてまとめています。運用や開発を始める際は、各モジュールの docstring（特に config.py, run_*.py, monitoring/*, ai/*, portfolio/*）を参照してください。必要であればサンプル .env.example の作成や、requirements.txt / Dockerfile、起動・監視の運用手順書（Runbook）などの追加ドキュメントも作成できます。必要があれば教えてください。