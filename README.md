# KabuSys README

このリポジトリは日本株自動売買システム「KabuSys」の実装の一部です。本書はコードベース（src/kabusys/）の主要コンポーネント、セットアップ、起動方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームの一部実装です。主な目的は以下：

- シグナルに基づく発注・注文管理（ExecutionEngine）
- システム稼働性・注文異常・リスク（ドローダウン・ポジション上限）の監視（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算（Portfolio モジュール）
- リサーチ用ファクター計算および特徴量解析（Research）
- ニュースの NLP によるセンチメント算出（AI モジュール）
- Paper Trading 用の検証ツール（tools）

設計方針として、DB（SQLite / DuckDB）を使った永続化、外部 API 呼び出し（ブローカー／OpenAI）は抽象化され、paper_trading モードで本番 DB と分離できるようになっています。

---

## 主な機能一覧

- Execution
  - 発注フロー（OrderManager、OrderRepository、Reconciler）
  - 再起動時の自動復旧（Reconciler）
  - Paper Trading モード（MockBroker を利用し data/paper_trading.db に記録）
- Monitoring
  - システム状態監視（CPU/メモリ/ディスク、プロセス生存、データ鮮度）
  - 注文監視（滞留注文、約定価格異常）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch による停止フラグ自動書き込み
  - LINE によるアラート通知（AlertManager）
  - Streamlit ダッシュボード
- Portfolio
  - 候補選定・重み計算（等分・スコア重み）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ決定（単元丸め、利用現金に合わせたスケール）
- Research
  - Momentum/Volatility/Value 等のファクター計算（DuckDB ベース）
  - 将来リターン、IC（Spearman）計算、統計サマリ
- AI
  - ニュースセンチメント算出（OpenAI API を使用）
  - 市場レジーム検出（ETF MA とマクロニュースの LLM 評価を統合）
- Tools
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）

---

## 要件（主な依存パッケージ）

推奨 Python バージョン: 3.9+

必須ライブラリ（抜粋）:
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード使用時)
- sqlite3（標準ライブラリ）
- その他の標準ライブラリ

（実運用では requirements.txt を用意して pip install -r でインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

3. .env ファイルの用意
   - プロジェクトルートに `.env`（必要な環境変数を記載）を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必須環境変数（一部）
   - JQUANTS_REFRESH_TOKEN — （J-Quants API 用）
   - KABU_API_PASSWORD — kabuステーション API 用
   - OPENAI_API_KEY — OpenAI を利用する機能で必要
   - KABUSYS_ENV — one of development, paper_trading, live（既定: development）
   - 省略時のデフォルト DB パス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

5. データディレクトリ作成
   - mkdir -p data

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live (既定: development)
  - paper_trading の場合、run_execution は専用の paper_trading DB を使用します
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必須）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、既定: 60）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject、既定: instant）
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: DB ファイルパス
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill.flag のパス
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE アラート用（未設定なら送信しない）

設定は .env/.env.local、または OS 環境変数で行います。.env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に行われます。

---

## 使い方

基本的にモジュールを直接実行することで各エンジンを起動できます。

1. 監視ループ (Monitoring)
   - 実行:
     - python -m kabusys.run_monitoring
   - 機能:
     - SystemMonitor を定期実行して system_status / risk_logs などを監視・記録します。
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト 60）。
     - 停止: プロジェクトルートの data/stop_requested.flag を作成すると監視ループを終了します。

2. 実行エンジン (ExecutionEngine)
   - 実行:
     - python -m kabusys.run_execution
   - 機能:
     - ブローカークライアントを生成して注文処理を行います。
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、DB は PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）に記録され、本番 DB と分離されます。
     - 起動時に data/stop_requested.flag が存在すると起動しません。
     - 実行中に data/stop_requested.flag を作成するとエンジン停止シグナルを送り安全に終了します。

3. Streamlit ダッシュボード
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 機能:
     - monitoring.db のダッシュボード、ポジション、注文、システム状態を可視化します。
     - DB は読み取り専用 URI で開かれます（存在しない場合はエラー）。

4. Paper Trading 検証レポート
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - オプション:
       - --from YYYY-MM-DD
       - --to YYYY-MM-DD
       - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）
   - 目的:
     - Paper Trading DB の期間別指標（稼働率、注文成功率、送信率、レイテンシ等）を標準出力に出力します。

5. AI 関連（プログラムから呼び出す）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
     - raw_news から銘柄別ニュースを集め OpenAI に投げて ai_scores に書き込みます。OPENAI_API_KEY が必要。
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - マクロニュースと ETF MA を組み合わせて market_regime テーブルへ書き込みます。OPENAI_API_KEY が必要。

注意点:
- run_monitoring は Monitoring 用の SQLite（settings.sqlite_path）を常に使用します（環境に依存せず監視 DB は本番パスを参照）。
- kill.flag（Settings.kill_flag_path）は KillSwitch による ExecutionEngine 停止要因の記録に使われます。ExecutionEngine 起動時にオプションでクリーンアップする挙動があります（設定による）。

---

## 停止・運用上のファイル

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py が監視している停止フラグファイル。存在するとループを終了します。
- data/kill.flag
  - KillSwitch が書き込む停止理由（ExecutionEngine 停止のトリガー）。
- data/execution.pid
  - 実行エンジンの PID を書き込むファイル。SystemMonitor はこの PID を確認してプロセス存否をチェックします。
- data/*.db
  - monitoring.db（SQLite / 監視ログ）
  - paper_trading.db（Paper Trading 用 SQLite）
  - kabusys.duckdb（DuckDB、時系列価格やファクターデータ等）

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス
- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 切替あり）

サブパッケージ:
- monitoring/
  - monitoring_db.py — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — 停止フラグ書き込みロジック
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各 Monitor の統合ループ
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py など（発注と再同期ロジック）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算・集計キャップ対応
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム/ボラ/バリュー等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector.py — MA と LLM を使った市場レジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- data/（リポジトリルートに配置、実行時に使用）
  - monitoring.db, paper_trading.db, kabusys.duckdb, stop_requested.flag, kill.flag, execution.pid など

---

## よくある運用上の注意

- Paper Trading と本番 DB は分離してください。KABUSYS_ENV=paper_trading により run_execution は paper_trading DB に記録しますが、Monitoring は常に monitoring.sqlite_path（本番の監視 DB）を使用しますので設定に注意してください。
- OpenAI を利用する機能は API キー必須です。API 呼び出しはリトライ処理やフェイルセーフ（失敗時は 0.0 のフォールバック等）を含む設計ですが、サンプルキーの誤使用や料金発生に注意してください。
- process_priority/set_cpu_affinity は OS 権限により失敗することがあります。失敗時はログに警告が出て処理は継続します。
- monitoring_db.init_monitoring_db() は冪等でテーブルと必要なマイグレーションを保証します。最初に DB を開くコードで呼ばれます。
- ログレベルは環境変数 LOG_LEVEL で制御できます（Settings.log_level）。ただし各スクリプトは起動時に basicConfig(level=logging.INFO) 等を使用しています。

---

## 開発者向けメモ

- .env のパース挙動: export プレフィックスやクォート、コメントを柔軟に扱います。不正な値は警告されます。
- DuckDB 接続を受け取る設計のため、Research/AI モジュールは SQL を直接投げて高速に集計できます。
- テスト時は外部 API 呼び出し部分（_call_openai_api 等）をモックすることで副作用を回避できます。

---

必要に応じて README をプロジェクト要件や運用フローに合わせて拡張してください。質問や追加で記載したい内容があれば教えてください。