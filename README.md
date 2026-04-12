# KabuSys — README (日本語)

このリポジトリは日本株向けの自動売買・研究・監視ツール群です。  
本 README ではプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよび補助ツール群です。主な目的は以下です。

- 発注エンジン（ExecutionEngine）による注文作成・送信・リコンシリエーション
- 監視（Monitoring）によるシステム状態・注文状態・リスク監視、アラート送信
- 研究（Research）用のファクター計算・特徴量分析
- ポートフォリオ構築ロジック（候補選定・重み付け・ポジションサイズ算出）
- AI を用いたニュースセンチメント（OpenAI）や市場レジーム判定
- Paper Trading 用の分離された DB と検証ツール

設計方針の要点：
- DuckDB を分析用途に、SQLite を監視/取引ログ等の永続化に使用
- 環境毎（development / paper_trading / live）で挙動を切り替え可能
- OpenAI API 呼び出しはフェイルセーフ、リトライ、レスポンス検証を実装
- 多くの処理は純粋関数／副作用を最小限に保つ設計

---

## 主な機能一覧

- Execution
  - 注文作成・送信・状態管理（OrderManager）
  - 再起動時のリコンシリエーション（Reconciler）
  - Broker クライアントの抽象化（実ブローカー or Mock）
  - Paper Trading モード（本番 DB と完全分離、PAPER_FILL_MODE 制御）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、プロセス存在、データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン、ポジション上限）
  - KillSwitch（フラグファイルで ExecutionEngine に停止シグナル）
  - AlertManager（LINE Push による通知、クールダウン管理）
  - Streamlit ダッシュボード（監視 DB の可視化）
- Research / AI
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC 計算、特徴量統計
  - ニュース NLP（OpenAI を使った銘柄別センチメント）
  - 市場レジーム判定（ETF + マクロニュースを合成）
- Tools
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）
- Utilities
  - 環境設定読み込み（.env 自動読み込み機構）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Monitoring DB 初期化 / 永続化レイヤ

---

## セットアップ手順

前提：Python 3.9+ 想定（実際の互換性は環境に依存）。pip によるパッケージ管理を想定します。

1. レポジトリをクローンし、仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要な Python パッケージをインストール  
   主要な依存（代表例）:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - （その他プロジェクトの実際の requirements を使用してください）

   例:
   - pip install duckdb psutil requests openai streamlit

   ※ requirements.txt があればそちらを使用してください。

3. データディレクトリ
   - デフォルトでデータファイルは `data/` に保存されます（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）。
   - 必要なら事前に `mkdir -p data` を作成してください。

4. 環境変数 / .env
   - Settings モジュールはプロジェクトルートの `.env` と `.env.local` を自動ロードします（デフォルトで OS 環境変数より下位）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 重要な環境変数（例）：
     - KABUSYS_ENV = development | paper_trading | live
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - PAPER_FILL_MODE = instant | partial | never | reject
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB パス)
     - SQLITE_PATH (monitoring 用 DB パス, デフォルト: data/monitoring.db)
     - DUCKDB_PATH (分析用 DB, デフォルト: data/kabusys.duckdb)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート送信用)
     - PID_FILE_PATH, KILL_FLAG_PATH など

   簡易的な .env 例:
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   JQUANTS_REFRESH_TOKEN=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

---

## 使い方

主要スクリプトはモジュールとして実行できます（Python パッケージのルートが PYTHONPATH に入っていることを想定）。

- 監視ループの起動（SystemMonitor 単体起動スクリプト）
  - 動作: Settings の sqlite_path（常に本番設定）に接続して SystemMonitor のポーリングを実行
  - 実行:
    - python -m kabusys.run_monitoring
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60）
  - 補足:
    - 起動時にプロセス優先度を "high" に設定しようとします（psutil の権限に依存）

- ExecutionEngine の起動（注文実行）
  - 動作: KABUSYS_ENV によって実際の Broker か Mock を使い分け（paper_trading の場合は Mock、paper DB に記録）
  - 実行:
    - python -m kabusys.run_execution
  - 補足:
    - Paper Trading モードは settings.is_paper が True（KABUSYS_ENV=paper_trading）
    - Paper 用 DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
    - 起動時に PID ファイルを使用（Settings.pid_file_path）・kill flag のクリア挙動は設定で制御可能

- Paper Trading 検証レポート生成
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - --db デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- Streamlit ダッシュボード
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    - 監視 DB を read-only で開き、Overview / Positions / Orders / System のタブで可視化します

- AI 機能（ニュース NLP / レジーム判定）
  - 必要: OPENAI_API_KEY を設定
  - 呼び出しは API 的に `kabusys.ai.score_news` / `kabusys.ai.regime_detector.score_regime` を利用

---

## 主要モジュール説明（簡易）

- kabusys.config
  - .env 自動読み込みと Settings クラス（環境変数アクセスラッパ）
- kabusys.monitoring
  - monitoring_db: SQLite のテーブル初期化・操作ラッパ
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch
  - alert_manager: LINE Push 経由で通知
  - streamlit_dashboard: 可視化用 UI
- kabusys.execution
  - order_manager, reconciler, execution_engine（実際のエンジンは run_execution から利用）
- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment（等金額・スコア配分、単元丸め、セクターキャップ、レジーム乗数）
- kabusys.research
  - factor_research: momentum/volatility/value の算出（DuckDB 経由）
  - feature_exploration: forward returns / IC / summary
- kabusys.ai
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄別スコアを ai_scores テーブルへ書き込む
  - regime_detector: ETF MA とマクロニュースを合成して市場レジーム判定
- kabusys.utils
  - process_priority: cross-platform なプロセス優先度/CPU affinity 設定

---

## ディレクトリ構成

（主要ファイル・フォルダを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 broker / order_repository / execution_engine 等)
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
    - utils/
      - process_priority.py
      - __init__.py
    - data/ (期待されるランタイムの data 配置例)
      - kabusys.duckdb (DuckDB)
      - monitoring.db (SQLite monitoring DB)
      - paper_trading.db (Paper Trading 用 SQLite)

---

## 運用上の注意 / トラブルシューティング

- OpenAI
  - OPENAI_API_KEY が未設定だと ai 機能は動きません。エラーではなく ValueError を投げるか、関数が 0 を返す等のフェイルセーフ実装がありますが、API キーを用意すると正しく動作します。
  - レート制限や 5xx は再試行ロジックがありますが、長時間失敗することがあります。ログを確認してください。
- psutil による優先度設定
  - 非特権ユーザーではプロセス優先度/affinity の変更に失敗することがあります。その場合は警告ログが出て処理は継続します。
- kill.flag
  - KillSwitch が生成する `data/kill.flag` をチェックし、ExecutionEngine 停止の挙動があります。必要であれば起動前に削除（または Settings.kill_flag_clear_on_start を設定）してください。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB に対する簡単なカラム追加（マイグレーション）を行います。カラム追加に失敗すると例外になりますのでバックアップを推奨します。
- 権限・パス
  - PID ファイルやデータディレクトリの書き込み権限を事前に確認してください。

---

## 開発のヒント

- Settings は .env / .env.local をプロジェクトルートから自動で読み込みます（.git または pyproject.toml を探します）。テスト時に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
- DuckDB 接続は分析専用。research モジュールは prices_daily / raw_financials / raw_news 等のテーブルを前提にしています。
- 各種 API 呼び出し（OpenAI、LINE、Broker）は失敗時にログを出し継続するよう設計されています。運用時はログ監視を必須にしてください。

---

この README はコードベースの現状（主要ファイルとコメント）に基づいて作成しています。実際の依存関係や追加の CLI オプション、ドキュメントはプロジェクトの他ファイル（pyproject.toml / requirements.txt / docs）を参照してください。必要であれば README に環境変数の完全リストや起動例を追記します。