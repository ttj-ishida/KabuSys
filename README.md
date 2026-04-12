# KabuSys — README

日本株向け自動売買フレームワークの一部（簡易版ドキュメント）。  
この README は、提供されたコードベース（src/kabusys 配下）に基づいてプロジェクト概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

注意: 実行にはソースを Python パスに含める必要があります（開発時はプロジェクトルートから `PYTHONPATH=src` を指定するのが簡単です）。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するモジュール群です。主要な責務は以下です。

- 市場データ（DuckDB）からファクター/指標を計算する研究用モジュール（research）
- ポートフォリオ構築（候補選定・重み・ポジションサイジング・セクター制約）
- Execution 層（ブローカー抽象化・注文管理・リコンシリエーション・リスク管理）
- 監視（System / Trade / Risk モニタ、アラート、kill-switch、Streamlit ダッシュボード）
- AI 支援モジュール（ニュースの NLP によるセンチメント、レジーム判定）
- 開発/検証用ツール（Paper Trading の検証レポート生成 など）
- 環境/設定管理（.env 自動読み込み、Settings）

このコードは本番用の DB（DuckDB / SQLite）や外部 API（Kabu API / OpenAI など）との接続を前提としていますが、paper_trading 環境ではブローカーをモックして本番 DB と分離する仕組みがあります。

---

## 主な機能一覧

- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、実行プロセス PID、データ鮮度チェック
  - TradeMonitor: 滞留注文検出、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ
  - AlertManager: LINE Push による通知（クールダウン管理）
  - KillSwitch: 条件達成時に `data/kill.flag` を書き込んで ExecutionEngine 停止をトリガ
  - Streamlit ダッシュボード：監視データの可視化

- Execution（実行系）
  - OrderManager / OrderRepository / Reconciler: 発注・状態同期・再起動時の復旧
  - RiskManager: 発注前の制約チェック（最大ポジション比率、利用率等）
  - BrokerFactory によるブローカー選択（paper_trading では MockBroker を利用）

- Portfolio（ポートフォリオ構築）
  - 候補選定、等重・スコア加重、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム係数

- Research（研究用）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由で prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI 経由）
  - news_nlp: ニュースをまとめて LLM でセンチメントを計算し ai_scores テーブルへ書き込み
  - regime_detector: ma200 とマクロニュースセンチメントを合成して market_regime を判定

- ツール
  - paper_verification_report: Paper Trading DB を解析して検証レポートを出力

- ユーティリティ
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
  - config: .env 自動読み込みと Settings クラス

---

## セットアップ手順（開発環境）

1. 必要な Python バージョン
   - Python 3.10 以上（型注釈で `X | Y` の記法を使用）

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS)
   - .venv\Scripts\activate (Windows)

3. 必要パッケージのインストール（最低限）
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit
   例:
   ```
   pip install duckdb psutil openai requests streamlit
   ```
   ※ 実際のプロジェクトでは requirements.txt / Poetry 等で管理する想定です。

4. ソースを Python パスに含める（開発実行時）
   - プロジェクトルートから:
     ```
     PYTHONPATH=src python -m kabusys.run_monitoring
     ```
     Windows PowerShell:
     ```
     $env:PYTHONPATH="src"; python -m kabusys.run_monitoring
     ```

5. 環境変数設定
   - .env または OS 環境変数に必要な値を設定します。プロジェクトは自動的にプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を探して `.env` / `.env.local` を読み込みます（OS 環境変数が優先、.env.local が .env を上書き）。
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

6. 必須となる主要な環境変数（抜粋）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
   - KABU_API_PASSWORD — kabuステーション API 用（必須）
   - OPENAI_API_KEY — OpenAI を使う機能を使う場合（news_nlp / regime_detector）
   - KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live"), デフォルト "development"
   - その他オプション:
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE ("instant"|"partial"|"never"|"reject")
     - PID_FILE_PATH (default: data/execution.pid)
     - KILL_FLAG_PATH (default: data/kill.flag)
     - MONITOR_POLL_INTERVAL (監視ループ間隔 秒、デフォルト 60)

   .env.example があればこれを参考に作成してください（ソース配布の際に同梱想定）。

---

## 使い方（主要コマンド例）

前提: プロジェクトルートから実行し、src を Python パスに含める。例: `PYTHONPATH=src python -m kabusys.run_monitoring`

- 監視ループ起動（Monitoring）
  ```
  PYTHONPATH=src python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は Settings の sqlite_path（monitoring DB） を使ってログを保存します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

- Execution エンジン起動（注文実行）
  ```
  PYTHONPATH=src python -m kabusys.run_execution
  ```
  - 環境変数 `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録（本番 DB と分離）。
  - 実行前に PID ファイル、kill.flag の取り扱い（Settings.kill_flag_clear_on_start）に注意してください。

- Streamlit ダッシュボード（監視 UI）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - `--db` オプションで SQLite DB を指定できます。既存 DB を read-only で開くため URI が使われます。

- Paper Trading 検証レポート
  ```
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で DB を指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` が優先されます。

- AI スコアリング / レジーム判定はプログラム的に呼び出し
  - kabusys.ai.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)
  - どちらも OpenAI API キー（api_key 引数 または OPENAI_API_KEY 環境変数）が必要です。

---

## 重要な動作・挙動メモ

- .env の自動読み込み
  - プロジェクトルートを .git または pyproject.toml から検出して `.env` / `.env.local` を読みます。
  - OS 環境変数が優先され、.env.local は .env を上書きできます。
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- データベース
  - DuckDB: デフォルト `data/kabusys.duckdb`
  - Monitoring SQLite: デフォルト `data/monitoring.db`
  - Paper Trading SQLite: `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成・マイグレーション（カラム追加）を行います。

- PID / Kill Flag
  - ExecutionEngine は PID ファイル（デフォルト `data/execution.pid`）を使用して実行プロセスの存否を監視します。
  - KillSwitch は `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります（既存ファイルがあれば再書き込みせず冪等）。

- Paper Trading mode
  - `KABUSYS_ENV=paper_trading` とすると、Execution は本番ブローカーではなく MockBroker を使い、paper_trading 用の SQLite に記録します（本番 DB と完全に分離）。

- OpenAI 利用
  - news_nlp / regime_detector は OpenAI（gpt-4o-mini）を利用しており、API 呼び出しは冪等性やリトライ（指数バックオフ）を考慮して設計されています。
  - API キーが未設定の場合、いくつかの処理はフェイルセーフ（スコア=0.0、処理スキップなど）で継続するように実装されていますが、明示的にエラーを出す箇所もあります（値チェックにより ValueError）。

---

## ディレクトリ構成（概要）

以下は src/kabusys 配下の主要ファイルと役割の一覧（抜粋）です。

- src/kabusys/
  - __init__.py — パッケージメタ情報
  - config.py — 環境変数/.env の読み込みと Settings クラス
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading モード対応）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力ツール
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン/ポジション上限監視
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - alert_manager.py — LINE 通知ラッパ
    - kill_switch.py — kill.flag 管理
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
  - execution/
    - order_manager.py — 注文作成/送信の高レベル API
    - order_repository.py — SQLite ベースの注文ストレージ（コード断片中に存在）
    - reconciler.py — 再起動時の注文/ポジション突合
    - risk_manager.py — 発注時リスク制約
    - broker_factory.py / broker_api.py など（ブローカー抽象）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・スケーリング
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメント集計 & OpenAI 呼び出し
    - regime_detector.py — ma200 + マクロセンチメントでレジーム判定
  - data/ （Runtime に作成されることが多い）
    - kabusys.duckdb (DuckDB)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite for paper trading)

（上記はコードベースの抜粋に基づく一覧です。実際のフル実装ではファイルや補助モジュールが追加される可能性があります。）

---

## よくある質問 / 注意点

- Python バージョン
  - 型ヒントに `X | Y` を使っているため Python 3.10+ を推奨します。

- データベースファイルのバックアップ/排他
  - SQLite/ DuckDB ファイルは同時アクセスに注意してください。監視ダッシュボードは read-only モードで開くことが想定されています。

- .env の扱い
  - 自動読み込みは便利ですが、CI/本番環境では OS 環境変数で明示的に設定することを推奨します。自動読み込みを無効化するフラグがあります。

- テスト／モック
  - AI 呼び出し部分（news_nlp/_call_openai_api, regime_detector/_call_openai_api）はテスト時に patch して差し替えられるように設計されています。

---

必要であれば、README にサンプル .env、より詳細なコマンド例（systemd ユニットファイル、Dockerfile、CI 設定）や各モジュールの API 使用例（関数レベルの doc を抜粋）を追加で作成します。どの情報を優先して追加しますか？