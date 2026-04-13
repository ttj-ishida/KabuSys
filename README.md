# KabuSys

日本株向け自動売買システムのモジュール群。  
ポートフォリオ構築、注文実行、監視、リサーチ、AI（ニュースセンチメント/レジーム判定）などの機能を持つマイクロサービス風ライブラリです。

---

## プロジェクト概要

KabuSys は以下の責務を持つコンポーネント群で構成されています。

- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ算出）
- 注文管理・Execution Engine（ブローカーとのやり取り、リコンシリエーション）
- 監視（システム状態、注文滞留、リスクアラート、kill-flag）
- リサーチ（ファクター算出、特徴量解析）
- AI モジュール（ニュースのセンチメント分析、レジーム判定）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針として、
- DuckDB/SQLite によるローカルデータベース操作（テーブル設計・永続化）
- 外部 API 呼び出し（ブローカー、OpenAI 等）は抽象化して安全に扱う
- 本番環境と Paper Trading のデータは分離（paper_trading 用 DB）
- ルックアヘッドバイアスを避けるため日付参照を明示的に扱う
などが採用されています。

---

## 主な機能一覧

- portfolio:
  - 銘柄候補選定（select_candidates）
  - 等金額・スコア加重の重み算出（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター制限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- execution:
  - OrderManager（発注の状態遷移管理）
  - Reconciler（再起動時の注文・ポジション突合）
  - Broker クライアントファクトリ（paper/live を切替可能）
- monitoring:
  - SystemMonitor（CPU/メモリ/ディスク・プロセス・データ鮮度）
  - TradeMonitor（滞留注文・約定異常価格検出）
  - RiskMonitor（ドローダウン・ポジション数監視）
  - KillSwitch（フラグファイルによる停止シグナル）
  - AlertManager（LINE Push による通知、クールダウン管理）
  - MonitoringEngine（複数モニタの統合ポーリング）
  - Streamlit ダッシュボード
- research:
  - ファクター計算（momentum/volatility/value）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリ
- ai:
  - news_nlp: ニュース記事を OpenAI に投げて銘柄ごとにセンチメントを算出・保存
  - regime_detector: ETF MA とマクロニュースで市場レジーム判定
- tools:
  - Paper Trading 検証レポート生成ツール（paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.9+（ソースに合わせて適宜）
- システムに必要な外部バイナリは不要（ただし psutil 等のパッケージが利用される）

手順の例（仮にプロジェクトルートがある状態）:

1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil requests openai streamlit

   （パッケージリストはプロジェクト用 requirements.txt を用意している場合はそれを使用してください）

3. 環境変数 / .env の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（既存 OS 環境変数を保護）。
   - 自動ロードを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。

必須の主な環境変数（例）
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必要な場合）
- KABU_API_PASSWORD — kabu ステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
- KABUSYS_ENV — 環境: development / paper_trading / live
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）

注意:
- Monitoring は実行時に常に本番用の sqlite_path を使用します（KABUSYS_ENV に依らず）。
- Paper Trading（KABUSYS_ENV=paper_trading）では Broker クライアントがモックに切り替わり、専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。

---

## 実行方法（使い方）

基本的にはモジュールを直接実行します。

- 監視ポーリング（デフォルト 60 秒間隔）
  - 環境変数で間隔を上書き: MONITOR_POLL_INTERVAL（秒、1 以上）
  - 実行:
    - python -m kabusys.run_monitoring
  - 実行時の挙動:
    - プロセス優先度を "high" に設定（可能な場合）
    - monitoring DB 初期化（テーブル作成／マイグレーション）
    - DuckDB 接続を確立して SystemMonitor のポーリングループを開始

- Execution Engine（注文実行セッション）
  - 実行:
    - python -m kabusys.run_execution
  - ポイント:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用
    - リスク設定等はコード内のデフォルトから調整可能（RiskConfig / EngineConfig）

- Paper Trading 検証レポート
  - 使い方:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
    - DB 指定: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）
  - 出力: 標準出力に期間サマリと Pass/Fail 判定を表示

- Streamlit ダッシュボード（監視データ表示）
  - 実行例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only 接続で DB を開くため、MonitoringEngine を先に起動しておく必要があります

---

## 主要な設定 / 環境変数

- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行管理用ファイル設定
- PAPER_FILL_MODE: paper_trading における MockBroker の約定挙動（instant|partial|never|reject）

---

## 重要な実装ノート（運用上の注意）

- Monitoring の DB 初期化は冪等（init_monitoring_db）。既存 DB に対してマイグレーション（カラム追加）を行うロジックがあります。
- KillSwitch は data/kill.flag を書くことで ExecutionEngine に停止を指示します。既存フラグがある場合は再書き込みしません。
- SystemMonitor は pid ファイルの存在とプロセス生存を確認し、stale PID を検出した場合は削除してリスクログに記録します。
- AI モジュールは OpenAI API の呼び出しでリトライ・エラーハンドリングを行い、レスポンスは厳密にバリデーションしてから DB に書き込みます。API キーは環境変数または引数で渡します。
- Paper Trading と Live のデータはできるだけ分離されています（DB・設定の分離）。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主要ファイル・モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env ロードと Settings クラス
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証ツール
  - portfolio/
    - portfolio_builder.py — 候補選定、重み付け
    - risk_adjustment.py — セクター制約、レジーム乗数
    - position_sizing.py — 株数計算・スケーリング
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（init / MonitoringDB）
    - system_monitor.py — システム状態監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 制御
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 監視の統合
    - streamlit_dashboard.py — Streamlit ダッシュボード
    - __init__.py
  - research/
    - factor_research.py — momentum/volatility/value 計算
    - feature_exploration.py — forward returns、IC、統計
    - __init__.py
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロ）
    - __init__.py
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity
    - __init__.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - broker_api.py
    - execution_engine.py
    - order_record.py
    - その他（Execution に関する実装ファイル群）

（実際のファイル一覧はリポジトリ内の src/kabusys を参照してください）

---

## 例: よく使うコマンドまとめ

- 監視開始:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を指定: --db /path/to/paper_trading.db
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## サポート / 拡張ポイント

- Broker クライアントの実装（本番 API / モック）は BrokerClientFactory を通じて差し替えが可能です。
- position_sizing の lot_size は将来的に銘柄別対応に拡張することを想定しています。
- AI モジュールのモデル指定やバッチサイズ、トークン制限は定数で管理されており、運用に合わせて調整可能です。
- MonitoringDB は軽量な永続層として設計されていますが、必要に応じて別の DB に移すことができます（init/CRUD 層の置き換え）。

---

必要であれば、README に含めるサンプル .env.example、requirements.txt、または各モジュールのより詳細な API ドキュメント（関数引数・戻り値・例外）を追加で作成します。どの情報を優先して追加しますか？