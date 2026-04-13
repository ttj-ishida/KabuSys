# KabuSys — README

このリポジトリは日本株向けの自動売買 / 研究 / 監視ユーティリティ群（KabuSys）のコードベースです。  
本ドキュメントはプロジェクト概要、主な機能、セットアップ手順・使い方、ディレクトリ構成を日本語でまとめた README.md です。

注意: 実行スクリプトはパッケージとして読み込めることを想定しています（例: python -m kabusys.run_monitoring）。環境変数は .env/.env.local または OS 環境変数から設定します（自動読み込み機能あり）。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主要なもの）
- ディレクトリ構成（主要ファイルと説明）
- 運用上の注意

---

プロジェクト概要
- KabuSys は日本株自動売買システムのためのライブラリ群で、以下を含みます:
  - 実行エンジン（ExecutionEngine）起動スクリプト
  - 監視 / アラート / Kill-switch 機構
  - ポートフォリオ構築・銘柄選定・ポジションサイズ計算の純粋関数群
  - 研究用ファクター計算・特徴量解析ツール
  - AI（OpenAI）を用いたニュースセンチメント評価・市場レジーム判定
  - 運用向けツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

機能一覧（抜粋）
- 実行エンジン起動（run_execution.py）
  - 本番 / Paper Trading 切替（KABUSYS_ENV）
  - Risk Manager、OrderManager、Reconciler を組み合わせて発注を管理
- 監視（run_monitoring.py / MonitoringEngine）
  - SystemMonitor: CPU・メモリ・ディスク・プロセス生存・データ鮮度監視
  - TradeMonitor: 滞留注文、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視・ダッシュボード更新
  - AlertManager: LINE Push による通知（クールダウンあり）
  - KillSwitch: 条件に応じて flag ファイルを書き、ExecutionEngine を停止させる仕組み
  - Streamlit ダッシュボード（監視結果の可視化）
- ポートフォリオ構築（portfolio パッケージ）
  - 銘柄選定、スコア重み付け、等金額配分、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ算出（単元株丸め、aggregate cap）
- 研究（research パッケージ）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI モジュール（ai）
  - news_nlp: ニュース記事を集約して OpenAI に投げ、銘柄単位のセンチメントスコアを ai_scores テーブルに書き込む
  - regime_detector: ma200 とマクロニュースセンチメントを合成して市場レジーム判定し、market_regime テーブルへ保存
- 運用ツール
  - tools/paper_verification_report.py: Paper Trading DB から検証レポート出力
  - monitoring/streamlit_dashboard.py: Streamlit による監視ダッシュボード

---

セットアップ手順（ローカル開発用）
1. Python 環境
   - 推奨: Python 3.9+（duckdb, psutil, openai 等を必要とします）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 主要依存例:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - 例:
     - pip install duckdb psutil requests openai streamlit
   - （requirements.txt がある場合はそれを使用してください）
4. データディレクトリ作成
   - mkdir -p data
   - 初回起動時に SQLite / DuckDB ファイルが自動作成されます（初期化は init_monitoring_db により実行）。
5. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を置くと自動読み込みされます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要環境変数は下記参照。

---

使い方（主要コマンド例）
- 監視ループ開始（デフォルト 60 秒ポーリング。MONITOR_POLL_INTERVAL で上書き可能）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動
  - 本番環境:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（ブローカーはモック、data/paper_trading.db に記録）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード（監視 DB を読み取り専用で開く）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも可）
- AI スコアリング / レジーム判定（ライブラリ関数として呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

---

主要な環境変数（要点）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。run_monitoring のデフォルトは 60。
- PAPER_FILL_MODE: Paper Trading のモック約定モード（instant|partial|never|reject）。デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）  
  - 注意: run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path を使用します（監視は本番 DB を想定）。
  - run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用して分離します。
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（ai ニュース・レジーム機能で必要）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必要に応じて）
- KABU_API_PASSWORD: kabuステーション API パスワード（本番ブローカー利用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE Push）に使用
- PID_FILE_PATH: 実行エンジンが書き込む pid ファイルパス（例: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書く flag ファイルパス（例: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を消すか (1 = clear)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視しきい値（%）

.env ファイル自動読み込み
- プロジェクトルート（.git または pyproject.toml を基準）で .env と .env.local を読み込みます。
- 読み込み順: OS 環境 > .env.local (override) > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能
- .env パーサは export 形式・クォート・インラインコメントなどに対応しています。

---

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数の取得・検証・デフォルト定義、.env 自動ロードロジック
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で制御）
  - run_execution.py
    - ExecutionEngine 起動スクリプト。paper_trading モードは MockBroker を使用して DB を分離
  - ai/
    - news_nlp.py: ニュースセンチメント評価（OpenAI）・ai_scores 書き込みロジック
    - regime_detector.py: ma200 + マクロセンチメントで市場レジーム判定
  - monitoring/
    - monitoring_db.py: SQLite スキーマ作成・永続化ユーティリティ（init_monitoring_db, MonitoringDB）
    - system_monitor.py: CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py: 滞留注文／約定異常検出
    - risk_monitor.py: ドローダウン監視・ポジション上限監視
    - kill_switch.py: flag ファイルによる ExecutionEngine 停止機構
    - alert_manager.py: LINE Push 通知（クールダウン付き）
    - monitoring_engine.py: 上記 Monitor をまとめてポーリングするエンジン
    - streamlit_dashboard.py: Streamlit ベースの簡易ダッシュボード
  - execution/
    - reconciler.py: 起動時の注文・ポジション照合（再同期）
    - order_manager.py: 発注ワークフロー（状態遷移管理）
    - （その他: broker_factory, execution_engine, order_repository 等を含む想定）
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算（等重/スコア重み）
    - risk_adjustment.py: セクターキャップ、レジーム乗数
    - position_sizing.py: 株数計算・単元丸め・aggregate cap
  - research/
    - factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py: 将来リターン、IC、統計サマリ
  - tools/
    - paper_verification_report.py: Paper Trading DB から検証レポートを生成
  - utils/
    - process_priority.py: psutil を利用したプロセス優先度 & CPU affinity 設定ユーティリティ
  - data/（実行時に利用するデータファイルを格納する想定）
    - kabusys.duckdb （デフォルト）
    - monitoring.db （SQLite、init される）
    - paper_trading.db （Paper Trading 用 SQLite）

（注）一部ファイルはここで列挙した主要部分のみを抜粋しています。細かい実装は各モジュール内の docstring を参照してください。

---

運用上の注意
- 監視（run_monitoring）は monitoring DB（settings.sqlite_path）を使用します。実稼働では監視DBを本番運用環境に合わせて適切に配置してください。
- run_execution は paper_trading モード時に paper_trading.db を使用し、本番 DB と分離されます。Paper 用 DB のパスは PAPER_TRADING_SQLITE_PATH で上書き可能。
- process priority / cpu affinity の設定は psutil を使っています。権限不足で設定に失敗することがあります（ログに警告が出ます）。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）が必須です。API 呼び出し時のレート制限や失敗に対してはリトライ・フォールバックの仕組みが入っていますが、キー・コスト管理は運用者の責任です。
- KillSwitch はファイルシステム上の flag ファイルにより ExecutionEngine を停止させます。flag の存在・削除は運用上の重要な操作となるため注意してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存テーブルにカラムを追加する簡易マイグレーションを行いますが、大規模変更については別途マイグレーション手順を用意してください。
- テスト: .env 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

補足
- 各モジュールの docstring に設計方針・入力/出力仕様が丁寧に書かれています。実装・拡張を行う際はまず各ファイルの docstring を確認してください。
- 追加のセットアップ（ブローカー認証、J-Quants トークン、LINE トークンなど）は各環境変数を .env に設定してください。

---

以上。必要であれば README に含めるサンプル .env.example、requirements.txt、起動 / デプロイ手順（systemd / supervisor / docker-compose）についても作成できます。どの形式を優先しますか？