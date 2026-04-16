# KabuSys

日本株自動売買システムの軽量実装（ライブラリ + 実行/監視スクリプト群）。

この README はソースツリー内の主要モジュールから機能・使い方を抜粋してまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群と実行・監視ツールを提供します。主な機能は次の通りです。

- 実行エンジン（ExecutionEngine）による注文発行・リスク管理・再同期（Reconciler）
- 監視（MonitoringEngine）によるプロセス・データ鮮度・注文件数・約定異常・ドローダウン監視
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI 補助機能（ニュースセンチメントによる銘柄スコアリング、レジーム判定）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）
- 設定管理（.env の読み込み、Settings クラス）
- プロセス優先度や CPU affinity のユーティリティ

設計上の特徴：
- DuckDB / SQLite をデータストアに使用（DuckDB は時系列・ファクタ計算、SQLite は監視・注文ログ等）
- Paper Trading と本番 DB を明確に分離
- OpenAI を利用した NLP 処理は外部 API キーで有効化（フェイルセーフ実装あり）
- .env/.env.local の読み込みは自動（必要に応じて無効化可能）

---

## 機能一覧（抜粋）

- 実行（run_execution.py）
  - Broker クライアント生成（本番 / Paper Trading 切り替え）
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine の起動
  - 停止フラグ（data/stop_requested.flag）による安全停止

- 監視（run_monitoring.py / MonitoringEngine）
  - SystemMonitor: CPU・メモリ・ディスク・プロセス生存・データ鮮度を監視
  - TradeMonitor: 滞留注文・約定価格異常を検出
  - RiskMonitor: ドローダウン・ポジション上限を監視、リスクイベントの記録
  - KillSwitch / AlertManager による自動停止判定と LINE 通知（設定があれば）

- 研究（kabusys.research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- AI（kabusys.ai）
  - news_nlp: ニュース記事を OpenAI でセンチメント評価して ai_scores に書き込む
  - regime_detector: MA200 とマクロニュースを組み合わせて市場レジーム判定

- ポートフォリオ（kabusys.portfolio）
  - 候補選定、等重・スコア重み計算、リスク調整（セクター制限・レジーム乗数）、ポジションサイズ算出（単元株丸め等）

- ユーティリティ
  - 設定管理（kabusys.config）: .env/.env.local 読み込み、Settings クラス
  - process_priority: プロセス優先度・CPU affinity 設定
  - monitoring_db: 監視用 SQLite スキーマ作成・CRUD

- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成
  - streamlit_dashboard: 監視 DB を可視化するダッシュボード

---

## セットアップ手順

以下はローカル開発 / 実行用の最小手順例です。

前提
- Python 3.9/3.10 以降（ソースは型ヒントに 3.9+ を想定）
- DuckDB/psutil/requests/openai/streamlit 等の外部ライブラリ

1. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb psutil requests openai streamlit
   ```
   ※プロジェクト専用の requirements.txt がある場合はそれを使用してください。

3. リポジトリルートに data ディレクトリを作成（スクリプトがこの配下へファイルを書きます）
   ```bash
   mkdir -p data
   ```

4. 環境変数 / .env の設定
   - プロジェクトは自動的にルートの `.env` と `.env.local` を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を利用する場合:
     - OPENAI_API_KEY
   - 主要な設定（デフォルト値）:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag
     - MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト 60）

   例（.env）:
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   ```

5. DB 初期化
   - 監視 DB スキーマは run_monitoring / run_execution の起動時に init_monitoring_db() が呼ばれて自動作成されます。
   - DuckDB のテーブル（prices_daily, raw_financials 等）は外部データ投入が必要です（研究・ファクター計算で参照）。

---

## 使い方（実行例）

重要: パッケージが import 可能な状態（`src` を PYTHONPATH に含めるか、パッケージ化してインストール）で実行してください。リポジトリルートで以下を実行する方法が一般的です。

1. ExecutionEngine（取引エンジン）の起動
   - Paper Trading で起動（MockBrokerを使用、DB を分離）
     ```bash
     export KABUSYS_ENV=paper_trading
     python -m kabusys.run_execution
     ```
   - 本番モード（注意して使用）
     ```bash
     export KABUSYS_ENV=live
     python -m kabusys.run_execution
     ```

   - 停止は `data/stop_requested.flag` を作成するとエンジンが検知して安全に停止します。

2. 監視ループの起動
   ```bash
   python -m kabusys.run_monitoring
   ```
   - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（例: 30）
     ```bash
     export MONITOR_POLL_INTERVAL=30
     ```

3. Streamlit ダッシュボード（監視 DB の可視化）
   ```bash
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   - ダッシュボードは監視 DB を読み取り専用モードで開きます。監視プロセスを先に起動しておくとデータが見えます。

4. Paper Trading 検証レポート生成
   ```bash
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   - `--db` オプションや環境変数 `PAPER_TRADING_SQLITE_PATH` で DB を指定できます。

5. AI 機能
   - OpenAI API を使う機能（news_nlp.score_news, regime_detector.score_regime）は `OPENAI_API_KEY` が必要です。キーがなければ ValueError が発生します（呼び出し前にチェックされます）。
   - これらは DuckDB の raw_news / news_symbols / ai_scores / prices_daily などを参照します。

---

## 主要な環境変数一覧（抜粋）

- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE通知）用（未設定ならログ出力のみ）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject、デフォルト instant）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH: 実行制御用パス
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

詳細は kabusys.config.Settings のプロパティ説明を参照してください。

---

## ディレクトリ構成（抜粋）

以下はソース内の主なパス・ファイルです（完全な一覧ではありません）。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数/.env 読み込みと Settings
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py       — Monitoring ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - execution_engine.py      (ほか実装ファイル)
      - broker_factory.py
      - broker_api.py
      - order_record.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - utils/
      - process_priority.py
    - data/                     — 実行時に使用する DB や PID/flag を置く（git 管理外推奨）

---

## 運用上の注意

- Paper Trading は本番 DB と完全分離されます。KABUSYS_ENV=paper_trading のときは PAPER_TRADING_SQLITE_PATH を使用します。
- 監視は常に「本番の monitoring.sqlite（設定された SQLITE_PATH）」へ書き込みます（run_monitoring は環境に関わらず本番の sqlite_path を使用します）。
- stop / kill フラグ:
  - data/stop_requested.flag: run_execution/run_monitoring が監視している停止フラグ
  - data/kill.flag: KillSwitch が作成する実運用停止フラグ（ExecutionEngine 停止のシグナル）
  - data/execution.pid: 実行エンジンの PID ファイル（SystemMonitor が存在確認）
- OpenAI 呼び出しは外部 API に依存するため、失敗時はフェイルセーフ（スコアを 0 にフォールバック、または処理をスキップ）する設計になっていますが、API 制限やコストに注意してください。

---

## 開発・拡張ポイント（参考）

- DuckDB 上の prices_daily / raw_financials データが整備されると研究・ファクター計算が有効になります。
- position_sizing の lot_size 対応や銘柄別 fee/slippage モデルの導入が想定されています（TODO コメントあり）。
- AI モジュールは JSON 検証やリトライを実装済みですが、モデル・プロンプトのチューニングは要検討です。
- AlertManager は LINE を使った簡易通知。メールや Slack 等へ拡張可能。

---

もし README に追加してほしい項目（例: requirements.txt の提案、より詳細な .env.example、データ投入手順、API モックの使い方、テストの実行法など）があれば教えてください。必要に応じてサンプル .env.example も作成します。