# KabuSys

KabuSys は日本株自動売買システムのモジュール群です。バックテスト／リサーチ用のファクター計算、ポートフォリオ構築、注文実行／リコンシリエーション、監視（モニタリング）や AI を使ったニュースセンチメント評価などの機能を提供します。

バージョン: 0.1.0

---

## 概要

このリポジトリは以下の主要な責務を持つモジュールで構成されています。

- execution: ブローカーとのやり取り、注文管理、再同期（Reconciler）などの取引実行ロジック
- monitoring: システム稼働状態・注文状態・リスク監視、LINE 通知、監視ダッシュボード
- portfolio: 候補選定、重み付け、単元株丸め、リスク調整（セクター上限・レジーム適用）
- research: DuckDB を用いたファクター計算・特徴量探索ユーティリティ
- ai: OpenAI API を用いたニュースセンチメント評価、レジーム判定
- tools: 運用用スクリプト（Paper Trading 検証レポート等）
- utils: プロセス優先度や CPU affinity のユーティリティ
- config: 環境変数 / .env の読み込みと Settings 管理

注: モジュールは duckdb や OpenAI SDK、psutil、requests、streamlit 等の外部ライブラリに依存します（詳細はセットアップ参照）。

---

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution.py）
  - 実ブローカー／Paper Trading 切替（KABUSYS_ENV）
  - 注文管理、リスク管理、リコンシリエーション、PID 管理、停止フラグ対応
- 監視ループ起動スクリプト（run_monitoring.py）
  - CPU / メモリ / ディスク / プロセス状態 / データ鮮度のポーリング
  - ポーリング間隔は環境変数で上書き可能（MONITOR_POLL_INTERVAL）
  - 監視ログを SQLite に永続化
- MonitoringEngine（複数監視コンポーネントの束ね）
  - SystemMonitor / TradeMonitor / RiskMonitor の定期実行
  - KillSwitch（閾値トリガーで ExecutionEngine 停止用フラグを作成）
  - AlertManager（LINE への一方向通知、クールダウン管理）
- Streamlit ダッシュボード（監視データ閲覧）
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
- AI 関連
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとの ai_score を ai_scores テーブルへ書き込み
  - regime_detector: ETF MA とマクロ記事の LLM スコアを合成して日次レジーム判定
- ポートフォリオ構築ユーティリティ
  - 候補選定（select_candidates）
  - 等重／スコア重み付け
  - ポジションサイズ計算（risk_based / equal / score）
  - セクター上限フィルタ、レジーム乗数

---

## セットアップ手順（ローカル開発 / 運用）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 推奨（個別インストール）:
     pip install duckdb psutil openai requests streamlit
   - これ以外に sqlite3 は標準ライブラリに含まれます。

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を実行してください）

3. Python の import パス（開発時）
   - パッケージは `src/` 配下にある想定です。開発時は環境変数 PYTHONPATH を設定してください：
     export PYTHONPATH=$(pwd)/src
     （Windows PowerShell の場合: $env:PYTHONPATH = (Resolve-Path src).Path）

4. data ディレクトリを作成
   - mkdir -p data

5. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（必要な環境変数を記載）を置くと自動読み込みされます。
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: 必須（J-Quants API トークン）
     - KABU_API_PASSWORD: 必須（kabu API パスワード）
     - OPENAI_API_KEY: AI 機能利用時に必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
     - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定モード）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

6. DB 初期化
   - run_monitoring.py や run_execution.py 実行時に必要なテーブルは自動で作成（init_monitoring_db が冪等で作成します）。
   - DuckDB 用のテーブル（prices_daily 等）は別途 ETL などで投入してください（research / ai は prices_daily/raw_news 等を前提とします）。

---

## 使い方（主なコマンド例）

注: 開発中はリポジトリルートで PYTHONPATH を通すか、パッケージをインストールして利用してください。

- 監視ループを起動（Monitoring）
  - 簡易実行:
    PYTHONPATH=src python src/kabusys/run_monitoring.py
  - モジュール実行:
    PYTHONPATH=src python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で変更:
    MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python src/kabusys/run_monitoring.py
  - 停止:
    - 監視プロセスはプロジェクトルートの data/stop_requested.flag を検知するとループを抜けます。
      touch data/stop_requested.flag

- 実行エンジンを起動（ExecutionEngine）
  - 本番モード（KABUSYS_ENV=live）:
    KABUSYS_ENV=live PYTHONPATH=src python src/kabusys/run_execution.py
  - Paper Trading（分離された DB に記録）:
    KABUSYS_ENV=paper_trading PYTHONPATH=src python src/kabusys/run_execution.py
  - 停止:
    - stop フラグ: data/stop_requested.flag を置くと起動中スレッドが検知して engine.stop() を呼び出します。
    - kill.flag: KillSwitch による停止指示は data/kill.flag を書き込みます（ExecutionEngine は kill.flag を検知して停止する設計）。

- Streamlit ダッシュボード（監視データ閲覧）
  - 起動例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - アクセス後はブラウザでダッシュボードを閲覧できます（read-only URI で SQLite を開いています）。

- Paper Trading 検証レポート
  - 実行例:
    PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

- AI 機能（ニューススコア, レジーム判定）
  - OPENAI_API_KEY が必要です。プログラムからは kabusys.ai.score_news / regime_detector.score_regime を呼び出せます。
  - 直接 CLI で呼ぶユーティリティは含まれていませんが、スクリプトやジョブから呼び出して ai_scores / market_regime テーブルに書き込みます。

---

## 運用上のフラグ / PID

- data/execution.pid
  - ExecutionEngine が起動時に PID を書き込む想定（SystemMonitor はこの PID ファイルを監視してプロセス生存を確認）。
- data/stop_requested.flag
  - 実行ループ（monitoring / execution）を穏やかに終了させるためのフラグ。プロセスは存在を検出して終了します。
- data/kill.flag
  - KillSwitch により書き込まれる停止フラグ。ExecutionEngine に対する停止信号として利用。

---

## 主要モジュール説明（抜粋）

- kabusys.config.Settings
  - .env ファイルと OS 環境変数を読み込み、アプリケーション設定を提供します。
- kabusys.monitoring.monitoring_db
  - SQLite に対する永続化層（system_status, trade_logs, positions, risk_logs, dashboard テーブル）。
- kabusys.monitoring.SystemMonitor / TradeMonitor / RiskMonitor
  - それぞれシステム状態、注文滞留／約定異常、ドローダウン・ポジション上限を監視。
- kabusys.monitoring.MonitoringEngine
  - 上記モニタを束ね、KillSwitch と AlertManager を組み合わせて監視ループを行う。
- kabusys.execution.OrderManager / Reconciler / ExecutionEngine（実装の一部）
  - 注文生成、ブローカー同期、自動復旧ロジックを含む。
- kabusys.portfolio.*
  - 銘柄候補選定、重み付け、リスク調整、株数決定（単元丸め）等の純粋関数群。
- kabusys.research.*
  - DuckDB を使ったファクター計算（momentum/value/volatility）や特徴量解析ユーティリティ。
- kabusys.ai.news_nlp, kabusys.ai.regime_detector
  - OpenAI を使ったニュースのセンチメント評価および市場レジーム判定の実装。
- kabusys.utils.process_priority
  - プラットフォーム依存差を吸収したプロセス優先度 / CPU affinity 設定ユーティリティ。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル/ディレクトリ構成（src 配下）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - utils/
      - __init__.py
      - process_priority.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 execution 関連ファイル)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - data/  (実行時に生成される想定)
      - monitoring.db (SQLite)
      - paper_trading.db (Paper Trading 用 SQLite)
      - kabusys.duckdb (DuckDB)
      - execution.pid / stop_requested.flag / kill.flag

---

## 運用に関する注意点

- Monitoring データベース（monitoring.db）は run_monitoring や run_execution の起動時に init_monitoring_db() で必要テーブルを作成します。既存スキーマに対する軽微なマイグレーション（カラム追加など）も組み込まれています。
- run_execution は KABUSYS_ENV=paper_trading の場合、Paper Trading 用に別 DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離します。Monitoring は常に settings.sqlite_path（監視用 DB）を使用します。
- AI 機能（news_nlp / regime_detector）は OPENAI_API_KEY が必須です。API 呼び出し時の失敗はフェイルセーフ（スコア 0 等）で処理される設計ですが、API キー未設定だと ValueError を投げます。
- プロセス優先度設定は set_process_priority("high") が用意されていますが、権限不足で設定できない場合は警告に留まり処理を継続します。
- LINE 通知は channel token と user id が設定されていない場合ログ出力のみで実際の送信は行いません。

---

必要に応じて README を拡張します（例えば、詳細な環境変数一覧、CI/CD 設定、サンプル .env.example、API キーの安全な管理方法、Docker 化手順など）。どの情報を追加希望か教えてください。